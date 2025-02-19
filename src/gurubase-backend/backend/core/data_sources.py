import logging
import random
import re
import time
import traceback
from langchain_community.document_loaders import YoutubeLoader, PyPDFLoader
from abc import ABC, abstractmethod
from core.exceptions import PDFContentExtractionError, WebsiteContentExtractionError, WebsiteContentExtractionThrottleError, YouTubeContentExtractionError
from core.models import DataSource, DataSourceExists, CrawlState
from core.gcp import replace_media_root_with_nginx_base_url
import unicodedata
from core.github_handler import process_github_repository, extract_repo_name
from core.requester import get_web_scraper
import scrapy
from scrapy.crawler import CrawlerRunner
from crochet import setup, wait_for
from urllib.parse import urljoin
from typing import List, Set
from django.utils import timezone


logger = logging.getLogger(__name__)


def youtube_content_extraction(youtube_url):
    try:
        loader = YoutubeLoader.from_youtube_url(
            youtube_url, 
            add_video_info=True,
            language=["en", 'hi', 'es', 'zh-Hans', 'zh-Hant', 'ar'], # The top 5 most spoken languages
            translation="en",
            chunk_size_seconds=30,
        )
    except Exception as e:
        logger.error(f"Error extracting content from YouTube URL {youtube_url}: {traceback.format_exc()}")
        raise YouTubeContentExtractionError(f"Error extracting content from the YouTube URL")
        
    loading = loader.load()
    if len(loading) == 0:
        logger.error(f"No content found for YouTube URL {youtube_url}")
        raise YouTubeContentExtractionError(f"No content found for the YouTube URL")

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


def fetch_data_source_content(data_source):
    from core.models import DataSource

    if data_source.type == DataSource.Type.PDF:
        data_source.content = pdf_content_extraction(data_source.url)
        data_source.scrape_tool = 'pdf'
    elif data_source.type == DataSource.Type.WEBSITE:
        title, content, scrape_tool = website_content_extraction(data_source.url)
        data_source.title = title
        data_source.content = content
        data_source.scrape_tool = scrape_tool
    elif data_source.type == DataSource.Type.YOUTUBE:
        content = youtube_content_extraction(data_source.url)
        data_source.title = content['metadata']['title']
        data_source.content = content['content']
        data_source.scrape_tool = 'youtube'
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


class GitHubRepoStrategy(DataSourceStrategy):
    def create(self, guru_type_object, repo_url):
        try:
            # Create the data source
            data_source = DataSource.objects.create(
                type=DataSource.Type.GITHUB_REPO,
                guru_type=guru_type_object,
                url=repo_url
            )

            data_source.save()

            return {
                'type': 'GITHUB_REPO',
                'url': repo_url,
                'status': 'success',
                'id': data_source.id,
                'title': data_source.title
            }
        except DataSourceExists as e:
            return {
                'type': 'GITHUB_REPO',
                'url': repo_url,
                'status': 'exists',
                'id': e.args[0]['id'],
                'title': e.args[0]['title']
            }
        except Exception as e:
            logger.error(f'Error processing GitHub repository {repo_url}: {traceback.format_exc()}')
            return {
                'type': 'GITHUB_REPO',
                'url': repo_url,
                'status': 'error',
                'message': str(e)
            }


setup()

def get_random_proxy():

    return "http://dxttebbz:zw0wt5ys5g0c@" + random.choice(proxy_list)

class InternalLinkSpider(scrapy.Spider):
    name = 'internal_links'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_url = self.start_urls[0]
        self.original_url = kwargs.get('original_url')
        self.internal_links: Set[str] = set()
        self.crawl_state_id = kwargs.get('crawl_state_id')
        self.link_limit = kwargs.get('link_limit', 1500)
        self.should_close = False

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
        logger.info(f"Parsing URL: {response.url}")
        time.sleep(0.2)
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

            is_english = (
                not html_lang and not content_lang or
                (html_lang and html_lang.lower().startswith('en')) or
                (content_lang and content_lang.lower().startswith('en'))
            )
            
            if response.status == 200 and is_english:
                if response.url.startswith(self.start_url) or response.url.startswith(self.original_url):
                    self.internal_links.add(response.url)
                    if self.crawl_state_id:
                        crawl_state = CrawlState.objects.get(id=self.crawl_state_id)
                        if crawl_state.status == CrawlState.Status.RUNNING:
                            crawl_state.discovered_urls = list(self.internal_links)
                            crawl_state.save(update_fields=['discovered_urls'])

                if len(self.internal_links) % 100 == 0:
                    logger.info(f"Found {len(self.internal_links)} internal links")
                    if len(self.internal_links) >= self.link_limit:
                        if self.crawl_state_id:
                            crawl_state = CrawlState.objects.get(id=self.crawl_state_id)
                            crawl_state.status = CrawlState.Status.COMPLETED
                            crawl_state.end_time = timezone.now()
                            crawl_state.save()
                        return

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
                    
                    normalized_url = clean_url.rstrip('/')
                    if not any(link.rstrip('/') == normalized_url for link in self.internal_links):
                        logger.info(f"Crawling URL: {normalized_url}")
                        yield scrapy.Request(
                            full_url, 
                            callback=self.parse,
                            errback=self.handle_error,
                            meta={'download_timeout': 10, 'proxy': get_random_proxy()}
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

def get_internal_links(url: str, crawl_state_id: int = None, link_limit: int = 1500) -> List[str]:
    """
    Crawls a website starting from the given URL and returns a list of all internal links found.
    The crawler only follows links that start with the same domain as the initial URL.
    
    Args:
        url (str): The starting URL to crawl from
        crawl_state_id (int): ID of the CrawlState object to update during crawling
        link_limit (int): Maximum number of links to collect (default: 1500)
    
    Returns:
        List[str]: A list of all internal links found
    """
    links = set()

    class BulkInternalLinkSpider(InternalLinkSpider):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.internal_links: Set[str] = links

    @wait_for(timeout=3600)  # Wait for up to 1 hour
    def run_crawler():
        runner = CrawlerRunner(settings={
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
        })
        
        deferred = runner.crawl(BulkInternalLinkSpider, start_urls=[url], original_url=url, crawl_state_id=crawl_state_id, link_limit=link_limit)
        
        # Update crawl state when spider closes
        def on_spider_closed(spider):
            if crawl_state_id:
                try:
                    crawl_state = CrawlState.objects.get(id=crawl_state_id)
                    # Only update if not already FAILED (from error handling)
                    if crawl_state.status != CrawlState.Status.FAILED:
                        crawl_state.status = CrawlState.Status.STOPPED if spider.should_close else CrawlState.Status.COMPLETED
                        crawl_state.end_time = timezone.now()
                        crawl_state.save()
                except Exception as e:
                    logger.error(f"Error updating crawl state on spider close: {str(e)}")
        
        deferred.addCallback(lambda spider: on_spider_closed(spider))
        return deferred

    try:
        run_crawler()
        return list(links)
    except Exception as e:
        logger.error(f"Error in get_internal_links: {str(e)}")
        if crawl_state_id:
            try:
                crawl_state = CrawlState.objects.get(id=crawl_state_id)
                crawl_state.status = CrawlState.Status.FAILED
                crawl_state.error_message = str(e)
                crawl_state.end_time = timezone.now()
                crawl_state.save()
            except Exception as e:
                logger.error(f"Error updating crawl state: {str(e)}")
        raise

