from datetime import UTC, datetime
import logging
import random
import re
import time
import traceback
from django.conf import settings
from langchain_community.document_loaders import YoutubeLoader, PyPDFLoader
from abc import ABC, abstractmethod

from markitdown import MarkItDown
from core.guru_types import get_guru_type_object_by_maintainer
from core.proxy import format_proxies, get_random_proxies
from core.exceptions import ExcelContentExtractionError, JiraContentExtractionError, NotFoundError, PDFContentExtractionError, ThrottleError, WebsiteContentExtractionError, WebsiteContentExtractionThrottleError, YouTubeContentExtractionError, ZendeskContentExtractionError, ConfluenceContentExtractionError
from core.models import DataSource, DataSourceExists, CrawlState
from core.gcp import replace_media_root_with_nginx_base_url
import unicodedata
from core.github.data_source_handler import process_github_repository, extract_repo_name
from core.requester import ConfluenceRequester, JiraRequester, ZendeskRequester, get_web_scraper, YouTubeRequester
import scrapy
from scrapy.crawler import CrawlerProcess
from multiprocessing import Process
from urllib.parse import urljoin
from typing import List, Set, Tuple
from django.utils import timezone
from core.utils import get_default_settings
from youtube_transcript_api import NoTranscriptFound

logger = logging.getLogger(__name__)
md = MarkItDown(enable_plugins=False)  # Set to True to enable plugins


def youtube_content_extraction(youtube_url, language_code='en'):
    transctipt_langs = ["en", 'hi', 'es', 'zh-Hans', 'zh-Hant', 'ar'] # The top 5 most spoken languages
    if language_code not in transctipt_langs:
        transctipt_langs.append(language_code)
    try:
        loader = YoutubeLoader.from_youtube_url(
            youtube_url, 
            add_video_info=True,
            language=transctipt_langs,
            translation=language_code,
            chunk_size_seconds=30,
        )
    except Exception as e:
        logger.error(f"Error extracting content from YouTube URL {youtube_url}: {traceback.format_exc()}")
        raise YouTubeContentExtractionError(f"Error extracting content from the YouTube URL")
        
    try:
        loading = loader.load()
        if len(loading) == 0:
            logger.error(f"No transcript found for YouTube URL {youtube_url}")
            raise YouTubeContentExtractionError(f"No transcript found for the YouTube URL")
    except NoTranscriptFound as e:
        logger.error(f"No transcript found for YouTube URL {youtube_url}")
        raise YouTubeContentExtractionError(f"No transcript found for the YouTube URL")
    except YouTubeContentExtractionError as e:
        raise e
    except Exception as e:
        logger.error(f"Error extracting content from YouTube URL {youtube_url}: {traceback.format_exc()}")
        raise YouTubeContentExtractionError(f"Error extracting content from the YouTube URL")

    document = loading[0]
    document_dict = {
        "metadata": document.metadata,
        "content": document.page_content,
    }

    # Remove anything enclosed in square brackets
    document_dict['content'] = re.sub(r'\[[^\]]*\]', '', document_dict['content'])

    # Remove the trailing newlines
    document_dict['content'] = document_dict['content'].strip()

    return document_dict


def jira_content_extraction(integration, jira_issue_link):
    try:
        jira_requester = JiraRequester(integration)
        jira_issue_key = jira_issue_link.split('/')[-1]
        issue = jira_requester.get_issue(jira_issue_key)
        return issue['title'], issue['content']
    except ThrottleError as e:
        raise e
    except Exception as e:
        logger.error(f"Error extracting content from Jira issue {jira_issue_key}: {traceback.format_exc()}")
        raise JiraContentExtractionError(traceback.format_exc()) from e

def zendesk_content_extraction(integration, url):
    if 'articles' in url:
        return zendesk_article_content_extraction(integration, url)
    else:
        return zendesk_ticket_content_extraction(integration, url)

def zendesk_article_content_extraction(integration, article_url):
    try:
        zendesk_requester = ZendeskRequester(integration)
        article_id = article_url.split('/')[-1].split('-')[0]
        article = zendesk_requester.get_article(article_id)
        return article['title'], article['content']
    except ThrottleError as e:
        raise e
    except Exception as e:
        logger.error(f"Error extracting content from Zendesk article {article_url}: {traceback.format_exc()}")
        raise ZendeskContentExtractionError(traceback.format_exc()) from e


def zendesk_ticket_content_extraction(integration, ticket_url):
    try:
        zendesk_requester = ZendeskRequester(integration)
        ticket_id = ticket_url.split('/')[-1]
        ticket = zendesk_requester.get_ticket(ticket_id)
        return ticket['title'], ticket['content']
    except ThrottleError as e:
        raise e
    except Exception as e:
        logger.error(f"Error extracting content from Zendesk ticket {ticket_url}: {traceback.format_exc()}")
        raise ZendeskContentExtractionError(traceback.format_exc()) from e

def pdf_content_extraction(pdf_path):
    try:
        pdf_path = replace_media_root_with_nginx_base_url(pdf_path)
        loader = PyPDFLoader(pdf_path)
        pages = loader.load()
    except Exception as e:
        logger.error(f"Error extracting content from PDF {pdf_path}: {traceback.format_exc()}")
        try:
            error_message = e.args[0]
            if pdf_path in error_message:
                # Replace the actual path with a placeholder
                error_message = error_message.replace(pdf_path, 'pdf_path')
        except Exception as e:
            error_message = 'Unknown error'
        raise PDFContentExtractionError(error_message)
    
    content = '\n'.join([page.page_content for page in pages])
    sanitized_content = content.replace('\x00', '')
    return sanitized_content

def excel_content_extraction(excel_path):
    try:
        excel_path = replace_media_root_with_nginx_base_url(excel_path)
        result = md.convert(excel_path)
        content = result.text_content
    except Exception as e:
        logger.error(f"Error extracting content from Excel {excel_path}: {traceback.format_exc()}")
        try:
            error_message = e.args[0]
            if excel_path in error_message:
                # Replace the actual path with a placeholder
                error_message = error_message.replace(excel_path, 'excel_path')
        except Exception as e:
            error_message = 'Unknown error'
        raise ExcelContentExtractionError(error_message)
    
    sanitized_content = content.replace('\x00', '')
    return sanitized_content


def website_content_extraction(url):
    """
    Extract content from a website URL using either Firecrawl or Crawl4AI based on settings.
    Returns: Tuple[title: str, content: str, scrape_tool: str]
    """
    try:
        scraper, scrape_tool = get_web_scraper()
        title, content = scraper.scrape_url(url)
        
        # Clean the extracted content
        title = clean_title(title)
        content = clean_content(content)
        
        return title, content, scrape_tool
        
    except Exception as e:
        try:
            status_code = e.response.status_code
            reason = e.response.reason
            response = e.response.content
        except Exception as e:
            status_code = 'Unknown'
            reason = str(e)
            response = 'Unknown'

        if status_code == 429:
            logger.warning(f"Throttled for Website URL {url}. status: {status_code}, reason: {reason}, response: {response}")
            raise WebsiteContentExtractionThrottleError(f"Status code: {status_code}\nReason: {reason}")
        else:
            logger.error(f"Error extracting content from Website URL {url}. status: {status_code}, reason: {reason}, response: {response}")
            raise WebsiteContentExtractionError(f"Status code: {status_code}\nReason: {reason}")

def _update_data_source_success(data_source, title, content, scrape_tool):
    """Update data source with successful scrape results"""
    data_source.title = title
    data_source.content = content
    data_source.scrape_tool = scrape_tool
    data_source.error = ""
    data_source.user_error = ""
    data_source.status = DataSource.Status.SUCCESS

def _update_data_source_failure(data_source, error, scrape_tool, is_unsupported=False):
    """Update data source with failure information"""
    data_source.scrape_tool = scrape_tool
    if is_unsupported:
        data_source.error = error
        data_source.user_error = "Firecrawl API error"
    else:
        data_source.error = "URL was not processed in batch request"
        data_source.user_error = "Failed to process URL"

    data_source.status = DataSource.Status.FAIL

def _update_data_source_throttled(data_source, error):
    """Update data source when throttling occurs"""
    data_source.status = DataSource.Status.NOT_PROCESSED
    data_source.error = str(error)
    data_source.user_error = str(error)

def process_website_data_sources_batch(data_sources):
    """
    Process multiple website data sources in batch.
    Returns: List of processed data sources
    """
    urls = [ds.url for ds in data_sources]
    scraper, scrape_tool = get_web_scraper()
    url_to_data_source = {ds.url: ds for ds in data_sources}
    
    def process_urls(urls_to_process):
        """Process a batch of URLs and return remaining URLs to retry"""
        try:
            successful_results, failed_urls = scraper.scrape_urls_batch(urls_to_process)
        except WebsiteContentExtractionThrottleError as e:
            # Mark all data sources as NOT_PROCESSED when throttled
            for url in urls_to_process:
                _update_data_source_throttled(url_to_data_source[url], e)
            raise  # Re-raise to stop processing
        
        # Handle successful results
        for url, title, content in successful_results:
            if url in url_to_data_source:
                _update_data_source_success(
                    url_to_data_source[url], 
                    title, 
                    content, 
                    scrape_tool
                )
        
        # Handle failed URLs and collect URLs to retry
        failed_url_set = {url for url, _ in failed_urls}
        successful_url_set = {result[0] for result in successful_results}
        remaining_urls = []
        
        for url in urls_to_process:
            if url in failed_url_set:
                error = next((error for failed_url, error in failed_urls if failed_url == url), "")
                _update_data_source_failure(
                    url_to_data_source[url],
                    error,
                    scrape_tool,
                    is_unsupported="no longer supported" in error
                )
                if "no longer supported" not in error:
                    remaining_urls.append(url)
            elif url not in successful_url_set:
                _update_data_source_failure(
                    url_to_data_source[url],
                    "URL was not processed",
                    scrape_tool
                )
                remaining_urls.append(url)
                
        return remaining_urls
    
    try:
        # First attempt
        remaining_urls = process_urls(urls)
        
        # Retry if needed
        if remaining_urls:
            logger.info(f"Retrying batch with {len(remaining_urls)} remaining URLs")
            remaining_urls = process_urls(remaining_urls)
            
            # Mark any remaining URLs as failed
            for url in remaining_urls:
                _update_data_source_failure(
                    url_to_data_source[url],
                    "Failed after retry",
                    scrape_tool
                )
    except WebsiteContentExtractionThrottleError:
        # Return data sources without further processing when throttled
        return list(url_to_data_source.values())
            
    return list(url_to_data_source.values())


def clean_title(title):
    title = title.replace('Copy to clipboard', '').strip()
    title = title.split('ContentsMenuExpandLight')[0].strip()
    title = title.split(' - This feature is available in the latest Canary')[0].strip()
    title = title.split('TwitterFacebookInstagramLinkedInYouTube')[0].strip()   # https://www.ycombinator.com/people
    # Remove repeated sequences of two or more characters
    title = re.sub(r'(.{2,})\1+', r'\1', title)
    return title.strip()


def clean_content(content):
    # Remove image references with any URL (data:, http:, https:, etc)
    content = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', content)
    
    # Remove non-ascii characters
    # content = re.sub(r'[^\x00-\x7F]+', '', content)

    # Remove the line starting with: Copy to clipboard
    content = re.sub(r'\nCopy to clipboard\n', '', content)

    # Remove repeated phrases like lines of equal signs or dashes
    content = re.sub(r'={10,}|-{10,}', '', content)

    # Remove the line starting with: You signed in with another tab or window.
    content = re.sub(r'^You signed in with another tab or window.*$\n?', '', content, flags=re.MULTILINE)

    # Remove the line starting with: {{ message }}
    content = re.sub(r'^{{ message }}.*$\n?', '', content, flags=re.MULTILINE)

    # Remove the line starting with: You cant perform that action at this time.
    content = re.sub(r'^You cant perform that action at this time.*$\n?', '', content, flags=re.MULTILINE)
    return content.strip()


def sanitize_filename(filename):
    normalized = unicodedata.normalize('NFKD', filename)
    ascii_filename = normalized.encode('ASCII', 'ignore').decode('ASCII')
    clean_filename = re.sub(r'[^\w\-\.]', '_', ascii_filename)
    return clean_filename


def fetch_data_source_content(integration, data_source, language_code):
    from core.models import DataSource

    if data_source.type == DataSource.Type.PDF:
        data_source.content = pdf_content_extraction(data_source.url)
        data_source.scrape_tool = 'pdf'
    elif data_source.type == DataSource.Type.EXCEL:
        data_source.content = excel_content_extraction(data_source.url)
        data_source.scrape_tool = 'excel'
    elif data_source.type == DataSource.Type.WEBSITE:
        title, content, scrape_tool = website_content_extraction(data_source.url)
        data_source.title = title
        data_source.content = content
        data_source.scrape_tool = scrape_tool
    elif data_source.type == DataSource.Type.YOUTUBE:
        content = youtube_content_extraction(data_source.url, language_code)
        data_source.title = content['metadata']['title']
        data_source.content = content['content']
        data_source.scrape_tool = 'youtube'
    elif data_source.type == DataSource.Type.JIRA:
        title, content = jira_content_extraction(integration, data_source.url)
        data_source.title = title
        data_source.content = content
        data_source.scrape_tool = 'jira'
    elif data_source.type == DataSource.Type.ZENDESK:
        title, content = zendesk_content_extraction(integration, data_source.url)
        data_source.title = title
        data_source.content = content
        data_source.scrape_tool = 'zendesk'
    elif data_source.type == DataSource.Type.CONFLUENCE:
        title, content = confluence_content_extraction(integration, data_source.url)
        data_source.title = title
        data_source.content = content
        data_source.scrape_tool = 'confluence'
    elif data_source.type == DataSource.Type.GITHUB_REPO:
        default_branch = process_github_repository(data_source)
        # Use the repository name as the title
        owner, repo = extract_repo_name(data_source.url)
        data_source.default_branch = default_branch
        data_source.title = f"{owner}/{repo}"
        data_source.scrape_tool = 'github'

    data_source.error = ""
    return data_source


class DataSourceStrategy(ABC):
    @abstractmethod
    def create(self, guru_type_object, data):
        pass


class PDFStrategy(DataSourceStrategy):
    def create(self, guru_type_object, pdf_file, private=False):
        try:
            pdf_file.name = sanitize_filename(pdf_file.name)
            
            data_source = DataSource.objects.create(
                type=DataSource.Type.PDF,
                guru_type=guru_type_object,
                file=pdf_file,
                private=private
            )
            return {
                'type': 'PDF',
                'file': pdf_file.name,
                'status': 'success',
                'id': data_source.id,
                'title': data_source.title
            }
        except DataSourceExists as e:
            return {
                'type': 'PDF',
                'file': pdf_file.name,
                'status': 'exists',
                'id': e.args[0]['id'],
                'title': e.args[0]['title']
            }
        except Exception as e:
            logger.error(f'Error processing PDF {pdf_file.name}: {traceback.format_exc()}')
            return {
                'type': 'PDF',
                'file': pdf_file.name,
                'status': 'error',
                'message': str(e)
            }

class ExcelStrategy(DataSourceStrategy):
    def create(self, guru_type_object, excel_file, private=False):
        try:
            excel_file.name = sanitize_filename(excel_file.name)
            
            data_source = DataSource.objects.create(
                type=DataSource.Type.EXCEL,
                guru_type=guru_type_object,
                file=excel_file,
                private=private
            )
            return {
                'type': 'Excel',
                'file': excel_file.name,
                'status': 'success',
                'id': data_source.id,
                'title': data_source.title
            }
        except DataSourceExists as e:
            return {
                'type': 'Excel',
                'file': excel_file.name,
                'status': 'exists',
                'id': e.args[0]['id'],
                'title': e.args[0]['title']
            }
        except Exception as e:
            logger.error(f'Error processing Excel {excel_file.name}: {traceback.format_exc()}')
            return {
                'type': 'Excel',
                'file': excel_file.name,
                'status': 'error',
                'message': str(e)
            }

class YouTubeStrategy(DataSourceStrategy):
    def create(self, guru_type_object, youtube_url):
        try:
            data_source = DataSource.objects.create(
                type=DataSource.Type.YOUTUBE,
                guru_type=guru_type_object,
                url=youtube_url
            )
            return {
                'type': 'YouTube',
                'url': youtube_url,
                'status': 'success',
                'id': data_source.id,
                'title': data_source.title
            }
        except DataSourceExists as e:
            return {
                'type': 'YouTube',
                'url': youtube_url,
                'status': 'exists',
                'id': e.args[0]['id'],
                'title': e.args[0]['title']
            }
        except Exception as e:
            logger.error(f'Error processing YouTube URL {youtube_url}: {traceback.format_exc()}')
            return {
                'type': 'YouTube',
                'url': youtube_url,
                'status': 'error',
                'message': str(e)
            }


class WebsiteStrategy(DataSourceStrategy):
    def create(self, guru_type_object, website_url):
        try:
            data_source = DataSource.objects.create(
                type=DataSource.Type.WEBSITE,
                guru_type=guru_type_object,
                url=website_url,
            )
            return {
                'type': 'Website',
                'url': website_url,
                'status': 'success',
                'id': data_source.id,
                'title': data_source.title
            }
        except DataSourceExists as e:
            return {
                'type': 'Website',
                'url': website_url,
                'status': 'exists',
                'id': e.args[0]['id'],
                'title': e.args[0]['title']
            }
        except Exception as e:
            logger.error(f'Error processing Website URL {website_url}: {traceback.format_exc()}')
            return {
                'type': 'Website',
                'url': website_url,
                'status': 'error',
                'message': str(e)
            }


class JiraStrategy(DataSourceStrategy):
    def create(self, guru_type_object, jira_url):
        try:
            data_source = DataSource.objects.create(
                type=DataSource.Type.JIRA,
                guru_type=guru_type_object,
                url=jira_url,
            )
            return {
                'type': 'Jira',
                'url': jira_url,
                'status': 'success',
                'id': data_source.id,
                'title': data_source.title
            }
        except DataSourceExists as e:
            return {
                'type': 'Jira',
                'url': jira_url,
                'status': 'exists',
                'id': e.args[0]['id'],
                'title': e.args[0]['title']
            }
        except Exception as e:
            logger.error(f'Error processing Jira URL {jira_url}: {traceback.format_exc()}')
            return {
                'type': 'Jira',
                'url': jira_url,
                'status': 'error',
                'message': str(e)
            }


class ZendeskStrategy(DataSourceStrategy):
    def create(self, guru_type_object, ticket_url):
        try:
            data_source = DataSource.objects.create(
                type=DataSource.Type.ZENDESK,
                guru_type=guru_type_object,
                url=ticket_url,
            )
            return {
                'type': 'Zendesk',
                'url': ticket_url,
                'status': 'success',
                'id': data_source.id,
                'title': data_source.title
            }
        except DataSourceExists as e:
            return {
                'type': 'Zendesk',
                'url': ticket_url,
                'status': 'exists',
                'id': e.args[0]['id'],
                'title': e.args[0]['title']
            }
        except Exception as e:
            logger.error(f'Error processing Zendesk URL {ticket_url}: {traceback.format_exc()}')
            return {
                'type': 'Zendesk',
                'url': ticket_url,
                'status': 'error',
                'message': str(e)
            }

class GitHubStrategy(DataSourceStrategy):
    def create(self, guru_type_object, repo):
        url = repo['url']
        glob_pattern = repo['glob_pattern']
        glob_include = repo['include_glob']
        try:
            data_source = DataSource.objects.create(
                type=DataSource.Type.GITHUB_REPO,
                guru_type=guru_type_object,
                url=url,
                github_glob_pattern=glob_pattern,
                github_glob_include=glob_include
            )
            return {
                'type': 'GitHub',
                'url': url,
                'status': 'success',
                'id': data_source.id,
                'title': data_source.title,
                'github_glob_pattern': glob_pattern,
                'github_glob_include': glob_include
            }
        except DataSourceExists as e:
            return {
                'type': 'GitHub',
                'url': url,
                'status': 'exists',
                'id': e.args[0]['id'],
                'title': e.args[0]['title'],
                'github_glob_pattern': e.args[0]['github_glob_pattern'],
                'github_glob_include': e.args[0]['github_glob_include']
            }
        except Exception as e:
            logger.error(f'Error processing GitHub repository {url}: {traceback.format_exc()}')
            return {
                'type': 'GitHub',
                'url': url,
                'status': 'error',
                'message': str(e)
            }


def run_spider_process(url, crawl_state_id, link_limit, language_code):
    """Run spider in a separate process"""
    try:
        settings = {
            'LOG_ENABLED': False,
            'ROBOTSTXT_OBEY': False,
            'DOWNLOAD_TIMEOUT': 10,
            'USER_AGENT': 'Mozilla/5.0',
            'CONCURRENT_REQUESTS': 50,
            'CONCURRENT_REQUESTS_PER_DOMAIN': 50,
            'CONCURRENT_REQUESTS_PER_IP': 50,
            'AUTOTHROTTLE_ENABLED': True,
            'AUTOTHROTTLE_START_DELAY': 0,
            'AUTOTHROTTLE_MAX_DELAY': 1,
            'AUTOTHROTTLE_TARGET_CONCURRENCY': 50,
        }
        
        process = CrawlerProcess(settings)
        process.crawl(
            InternalLinkSpider,
            start_urls=[url],
            original_url=url,
            crawl_state_id=crawl_state_id,
            link_limit=link_limit,
            language_code=language_code
        )
        process.start()
    except Exception as e:
        logger.error(f"Error in spider process: {str(e)}")
        logger.error(traceback.format_exc())


def get_internal_links(url: str, crawl_state_id: int, link_limit: int, language_code: str) -> List[str]:
    """
    Crawls a website starting from the given URL and returns a list of all internal links found.
    The crawler only follows links that start with the same domain as the initial URL.
    """
    try:
        # Start the spider in a separate process
        crawler_process = Process(target=run_spider_process, args=(url, crawl_state_id, link_limit, language_code))
        crawler_process.start()
        
    except Exception as e:
        logger.error(f"Error in get_internal_links: {str(e)}")
        logger.error(traceback.format_exc())
        if crawl_state_id:
            try:
                crawl_state = CrawlState.objects.get(id=crawl_state_id)
                crawl_state.status = CrawlState.Status.FAILED
                crawl_state.error_message = str(e)
                crawl_state.end_time = timezone.now()
                crawl_state.save()
            except Exception as save_error:
                logger.error(f"Error updating crawl state: {str(save_error)}")
                logger.error(traceback.format_exc())
        raise


class InternalLinkSpider(scrapy.Spider):
    name = 'internal_links'

    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
            self.start_url = self.start_urls[0]
            self.original_url = kwargs.get('original_url')
            self.language_code = kwargs.get('language_code')
            self.internal_links: Set[str] = set()
            self.crawl_state_id = kwargs.get('crawl_state_id')
            self.link_limit = kwargs.get('link_limit', 1500)
            self.should_close = False
            if settings.ENV != 'selfhosted':
                proxies = format_proxies(get_random_proxies())
            else:
                proxies = None
            self.proxies = proxies
        except Exception as e:
            logger.error(f"Error initializing InternalLinkSpider: {str(e)}", traceback.format_exc())
            CrawlState.objects.get(id=self.crawl_state_id).status = CrawlState.Status.FAILED
            CrawlState.objects.get(id=self.crawl_state_id).error_message = str(e)
            CrawlState.objects.get(id=self.crawl_state_id).end_time = timezone.now()
            CrawlState.objects.get(id=self.crawl_state_id).save()

    def check_crawl_state(self):
        """Check if the crawl should be stopped"""
        if self.crawl_state_id:
            crawl_state = CrawlState.objects.get(id=self.crawl_state_id)
            if crawl_state.status == CrawlState.Status.STOPPED:
                self.should_close = True
                # Tell scrapy to stop the spider
                self.crawler.engine.close_spider(self, 'Crawl stopped by user')
                return True
        return False

    def parse(self, response):
        try:
            # First check if crawl has been stopped
            if self.check_crawl_state():
                return

            content_type = response.headers.get('Content-Type', b'').decode('utf-8').lower()
            if 'text/html' not in content_type:
                return

            html_lang = response.xpath('//html/@lang').get()
            html_lang = html_lang.strip() if html_lang else None
            content_lang = response.headers.get('Content-Language', b'')
            content_lang = content_lang.decode('utf-8').strip() if content_lang else None

            language_valid = (
                not html_lang and not content_lang or
                (html_lang and html_lang.lower().startswith(self.language_code)) or
                (content_lang and content_lang.lower().startswith(self.language_code))
            )
            
            if response.status == 200 and language_valid:
                if response.url.startswith(self.start_url) or response.url.startswith(self.original_url):
                    self.internal_links.add(response.url)
                    if self.crawl_state_id:
                        crawl_state = CrawlState.objects.get(id=self.crawl_state_id)
                        if crawl_state.status == CrawlState.Status.RUNNING:
                            crawl_state.discovered_urls = list(self.internal_links)
                            crawl_state.save(update_fields=['discovered_urls'])

                if settings.ENV != 'selfhosted' and len(self.internal_links) >= self.link_limit:
                    if self.crawl_state_id:
                        crawl_state = CrawlState.objects.get(id=self.crawl_state_id)
                        if not crawl_state.user.is_admin:
                            crawl_state.status = CrawlState.Status.FAILED
                            crawl_state.error_message = f"Link limit of {self.link_limit} exceeded"
                            crawl_state.end_time = timezone.now()
                            crawl_state.save()
                    return

                if len(self.internal_links) % 100 == 0:
                    logger.info(f"Found {len(self.internal_links)} internal links")

                # Check again if crawl has been stopped before scheduling new requests
                if self.check_crawl_state():
                    return

                for href in response.css('a::attr(href)').getall():
                    full_url = urljoin(response.url, href)
                    clean_url = full_url.split('#')[0].split('?')[0]

                    if not clean_url.startswith(self.start_url) and not clean_url.startswith(self.original_url):
                        continue
                    
                    if any(clean_url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.css', '.js']):
                        continue

                    if re.search(r"/v\d+.*(?:/|$)", clean_url):
                        continue

                    not_follow_words = ["/release-notes/", "/releases/","/generated", "/cdn-cgi/", "/_modules/", 
                                      "/_static/", "/_sources/", "/_generated/", "/_downloads/", "/_sources/", 
                                      "/_autosummary/", "/tags/", "/tag/"]
                    if any(word in clean_url for word in not_follow_words):
                        continue
                    
                    normalized_url = full_url.rstrip('/')
                    if not any(link.rstrip('/') == normalized_url for link in self.internal_links):
                        if settings.ENV == 'selfhosted':
                            meta = {'download_timeout': 10}
                            time.sleep(0.1)
                        else:
                            meta = {'download_timeout': 10, 'proxy': random.choice(self.proxies)}
                        yield scrapy.Request(
                            full_url, 
                            callback=self.parse,
                            errback=self.handle_error,
                            meta=meta
                        )
        except Exception as e:
            logger.error(f"Exception {e} for url {response.url}")
            logger.error(f"Exception traceback: {traceback.format_exc()}")
            if self.crawl_state_id:
                crawl_state = CrawlState.objects.get(id=self.crawl_state_id)
                crawl_state.status = CrawlState.Status.FAILED
                crawl_state.error_message = str(e)
                crawl_state.end_time = timezone.now()
                crawl_state.save()
    
    def handle_error(self, failure):
        failed_url = failure.request.url.split('#')[0].split('?')[0]
        self.internal_links.discard(failed_url)
        logger.warning(f"Failed to crawl URL: {failed_url}, Reason: {failure.value}")

    def closed(self, reason):
        """Handle spider closure"""
        if self.crawl_state_id:
            try:
                crawl_state = CrawlState.objects.get(id=self.crawl_state_id)
                # Only update if not already FAILED (from error handling)
                if crawl_state.status != CrawlState.Status.FAILED:
                    crawl_state.status = CrawlState.Status.STOPPED if self.should_close else CrawlState.Status.COMPLETED
                    crawl_state.end_time = timezone.now()
                    crawl_state.discovered_urls = list(self.internal_links)
                    crawl_state.save()
            except Exception as e:
                logger.error(f"Error updating crawl state on spider close: {str(e)}")
                logger.error(traceback.format_exc())

class CrawlService:
    @staticmethod
    def validate_and_get_guru_type(guru_slug, user):
        """Shared validation logic"""
        guru_type = get_guru_type_object_by_maintainer(guru_slug, user)
        if not guru_type:
            raise NotFoundError(f'Guru type {guru_slug} not found')
        return guru_type

    @staticmethod
    def get_user(user):
        if settings.ENV == 'selfhosted':
            return None
        return user

    @staticmethod
    def start_crawl(guru_slug, user, url, source=CrawlState.Source.API):
        from core.serializers import CrawlStateSerializer
        from core.tasks import crawl_website
        import re

        # Validate URL format
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        if not url_pattern.match(url):
            return {'msg': 'Invalid URL format'}, 400

        user = CrawlService.get_user(user)
        try:
            guru_type = CrawlService.validate_and_get_guru_type(guru_slug, user)
            language_code = guru_type.get_language_code()
            link_limit = guru_type.website_count_limit
        except NotFoundError as e:
            if source == CrawlState.Source.UI:
                # Defaults
                guru_type = None
                link_limit = 1500
                language_code = 'en'
            else:
                raise e
        
        if guru_type:
            existing_crawl = CrawlState.objects.filter(
                guru_type=guru_type, 
                status=CrawlState.Status.RUNNING
            ).first()
            if existing_crawl:
                return {'msg': 'A crawl is already running for this guru type. Please wait for it to complete or stop it.'}, 400
        
        crawl_state = CrawlState.objects.create(
            url=url,
            status=CrawlState.Status.RUNNING,
            link_limit=link_limit,
            guru_type=guru_type,
            user=user,
            source=source
        )
        crawl_website.delay(url, crawl_state.id, link_limit, language_code)
        return CrawlStateSerializer(crawl_state).data, 200

    @staticmethod
    def stop_crawl(user, crawl_id):
        from core.serializers import CrawlStateSerializer
        user = CrawlService.get_user(user)
        
        # Existing stop logic
        try:
            crawl_state = CrawlState.objects.get(id=crawl_id)
            if crawl_state.status == CrawlState.Status.RUNNING:
                crawl_state.status = CrawlState.Status.STOPPED
                crawl_state.end_time = datetime.now(UTC)
                crawl_state.save()
            return CrawlStateSerializer(crawl_state).data, 200
        except CrawlState.DoesNotExist:
            return {'msg': 'Crawl not found'}, 404

    @staticmethod
    def get_crawl_status(user, crawl_id):
        from core.serializers import CrawlStateSerializer
        user = CrawlService.get_user(user)
        
        # Existing status logic
        try:
            crawl_state = CrawlState.objects.get(id=crawl_id)
            # Update last_polled_at
            crawl_state.last_polled_at = datetime.now(UTC)
            crawl_state.save(update_fields=['last_polled_at'])
            
            response_data = CrawlStateSerializer(crawl_state).data
            if crawl_state.error_message:
                response_data['error_message'] = crawl_state.error_message
            return response_data, 200
        except CrawlState.DoesNotExist:
            return {'msg': 'Crawl not found'}, 404


class YouTubeService:
    @staticmethod
    def verify_api_key():
        if settings.ENV == 'selfhosted':
            default_settings = get_default_settings()
            if not default_settings.youtube_api_key:
                return {'msg': 'A YouTube API key is required for this functionality. You can add the API key on the Settings page.'}, 400
            else:
                if not default_settings.is_youtube_key_valid:
                    return {'msg': 'YouTube API key is invalid. Please check the API key on the Settings page.'}, 400
                else:
                    return {'msg': 'YouTube API key is valid'}, 200
        else:
            return {'msg': 'Youtube API key is not checked on cloud.'}, 200

    @staticmethod
    def fetch_playlist(url):
        """
        Fetch videos from a YouTube playlist URL
        Expected url: https://www.youtube.com/watch?v=...&list=...
        """
        verify_api_key_response = YouTubeService.verify_api_key()
        if verify_api_key_response[1] != 200:
            return verify_api_key_response

        if not url:
            return {'msg': 'URL is required'}, 400

        # Extract playlist ID using regex
        import re
        playlist_match = re.search(r'[?&]list=([^&]+)', url)
        if not playlist_match:
            return {
                'msg': 'Invalid YouTube playlist URL. Valid format: https://www.youtube.com/watch?v={video_id}&list={playlist_id}'
            }, 400
            
        playlist_id = playlist_match.group(1)
        
        try:
            # Fetch videos using YouTubeRequester
            youtube = YouTubeRequester()
            videos = youtube.fetch_all_playlist_videos(playlist_id)
            
            # Format response
            response_data = {
                'playlist_id': playlist_id,
                'video_count': len(videos),
                'videos': [f"https://www.youtube.com/watch?v={video['contentDetails']['videoId']}" for video in videos]
                # 'videos': [{
                    # 'title': video['snippet']['title'],
                    # 'description': video['snippet']['description'],
                    # 'video_id': video['contentDetails']['videoId'],
                    # 'published_at': video['snippet']['publishedAt'],
                    # 'thumbnail_url': video.get('snippet', {}).get('thumbnails', {}).get('high', {}).get('url'),
                    # 'link': f"https://www.youtube.com/watch?v={video['contentDetails']['videoId']}"
                # } for video in videos]
            }
            
            return response_data, 200
            
        except ValueError as e:
            return {'msg': str(e)}, 400
        except Exception as e:
            logger.error(f'Error fetching YouTube playlist: {e}', exc_info=True)
            return {
                'msg': 'An error occurred while fetching the playlist'
            }, 500

    @staticmethod
    def fetch_channel(url):
        """
        Fetch videos from a YouTube channel URL
        Expected url: https://www.youtube.com/@username or https://www.youtube.com/channel/CHANNEL_ID
        """
        verify_api_key_response = YouTubeService.verify_api_key()
        if verify_api_key_response[1] != 200:
            return verify_api_key_response

        if not url:
            return {'msg': 'URL is required'}, 400

        # Extract username or channel ID using regex
        import re
        username_match = re.search(r'youtube\.com/@([^/]+)', url)
        channel_id_match = re.search(r'youtube\.com/channel/([^/?]+)', url)
        
        if username_match:
            username = username_match.group(1)
            channel_id = None
        elif channel_id_match:
            channel_id = channel_id_match.group(1)
            username = None
        else:
            return {
                'msg': 'Invalid YouTube channel URL. Valid formats: https://www.youtube.com/@{user_handler} or https://www.youtube.com/channel/{channel_id}'
            }, 400
        
        try:
            # Fetch videos using YouTubeRequester
            youtube = YouTubeRequester()
            videos = youtube.fetch_all_channel_videos(username=username, channel_id=channel_id)
            
            # Format response
            response_data = {
                'channel_identifier': username or channel_id,
                'identifier_type': 'username' if username else 'channel_id',
                'video_count': len(videos),
                'videos': [f"https://www.youtube.com/watch?v={video['contentDetails']['videoId']}" for video in videos]
                # 'videos': [{
                    # 'title': video['snippet']['title'],
                    # 'description': video['snippet']['description'],
                    # 'video_id': video['contentDetails']['videoId'],
                    # 'published_at': video['snippet']['publishedAt'],
                    # 'thumbnail_url': video.get('snippet', {}).get('thumbnails', {}).get('high', {}).get('url'),
                    # 'link': f"https://www.youtube.com/watch?v={video['contentDetails']['videoId']}"
                # } for video in videos]

            }
            
            return response_data, 200
            
        except ValueError as e:
            return {'msg': str(e)}, 400
        except Exception as e:
            logger.error(f'Error fetching YouTube channel: {e}', exc_info=True)
            return {
                'msg': 'An error occurred while fetching the channel'
            }, 500



def confluence_content_extraction(integration, confluence_page_url):
    try:
        confluence_requester = ConfluenceRequester(integration)
        
        # Check if this is a space overview URL
        if confluence_page_url.endswith('/overview'):
            # Extract the space key from the URL
            url_parts = confluence_page_url.split('/')
            space_key = url_parts[-2]  # Get the space key from URL
            
            try:
                # Get space with homepage information
                space_data = confluence_requester.get_space_with_homepage(space_key)
                
                # If homepage exists, use it
                if space_data.get('homepage') and space_data['homepage'].get('id'):
                    homepage_id = space_data['homepage']['id']
                    page = confluence_requester.get_page_content(homepage_id)
                    return page['title'], page['content']
                else:
                    raise ValueError(f"No homepage found for space {space_key}")
            except Exception as space_err:
                logger.warning(f"Could not get space data for {space_key}: {str(space_err)}")
                # Create a basic title/content as fallback
                space_title = f"Space: {space_key}"
                space_content = f"This is a Confluence space with key: {space_key}"
                return space_title, space_content
        else:
            # Regular page URL - extract the page ID as before
            page_id = confluence_page_url.split('/')[-2]
            page = confluence_requester.get_page_content(page_id)
            return page['title'], page['content']
    except ThrottleError as e:
        raise e
    except Exception as e:
        logger.error(f"Error extracting content from Confluence page {confluence_page_url}: {traceback.format_exc()}")
        raise ConfluenceContentExtractionError(traceback.format_exc()) from e


class ConfluenceStrategy(DataSourceStrategy):
    def create(self, guru_type_object, confluence_url):
        try:
            data_source = DataSource.objects.create(
                type=DataSource.Type.CONFLUENCE,
                guru_type=guru_type_object,
                url=confluence_url,
            )
            return {
                'type': 'Confluence',
                'url': confluence_url,
                'status': 'success',
                'id': data_source.id,
                'title': data_source.title
            }
        except DataSourceExists as e:
            return {
                'type': 'Confluence',
                'url': confluence_url,
                'status': 'exists',
                'id': e.args[0]['id'],
                'title': e.args[0]['title']
            }
        except Exception as e:
            logger.error(f'Error processing Confluence URL {confluence_url}: {traceback.format_exc()}')
            return {
                'type': 'Confluence',
                'url': confluence_url,
                'status': 'error',
                'message': str(e)
            }

