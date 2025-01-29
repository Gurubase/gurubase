import logging
import re
import traceback
from django.conf import settings
from langchain_community.document_loaders import YoutubeLoader, PyPDFLoader
from firecrawl import FirecrawlApp
from abc import ABC, abstractmethod
from core.exceptions import GitHubRepoContentExtractionError, PDFContentExtractionError, WebsiteContentExtractionError, WebsiteContentExtractionThrottleError, YouTubeContentExtractionError
from core.models import DataSource, DataSourceExists, GithubFile
from core.gcp import replace_media_root_with_nginx_base_url
import unicodedata
import json
from core.github_handler import process_github_repository, extract_repo_name
import os
import random


logger = logging.getLogger(__name__)
app = FirecrawlApp(api_key=settings.FIRECRAWL_API_KEY)


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
    Example firecrawl response:
    {
        "markdown": "# 404\n\n## This page could not be found.",
        "metadata": {
            "title": "404: This page could not be found.Next.js by Vercel - The React Framework | Next.js by Vercel - The React Framework",
            "description": "Next.js by Vercel is the full-stack React framework for the web.",
            "language": "en",
            "robots": "noindex",
            "ogTitle": "Next.js by Vercel - The React Framework | Next.js by Vercel - The React Framework",
            "ogDescription": "Next.js by Vercel is the full-stack React framework for the web.",
            "ogImage": "https://assets.vercel.com/image/upload/front/nextjs/twitter-card.png",
            "ogLocaleAlternate": [],
            "sourceURL": "https://nextjs.org/docs/app/building-your-application/routing/error-handling3",
            "error": "Not Found",
            "statusCode": 404
        }
    }
    """
    try:
        scrape_status = app.scrape_url(
            url, 
            params={'formats': ['markdown'], "onlyMainContent": True}
        )
    except Exception as e:
        try:
            status_code = e.response.status_code
            reason = e.response.reason
            response = e.response.content
        except Exception as e:
            status_code = 'Unknown'
            reason = 'Unknown error'
            response = 'Unknown'

        if status_code == 429:
            logger.warning(f"Throttled for Website URL {url}. status: {status_code}, reason: {reason}, response: {response}")
            raise WebsiteContentExtractionThrottleError(f"Status code: {status_code}\nReason: {reason}")
        else:
            logger.error(f"Error extracting content from Website URL {url}. status: {status_code}, reason: {reason}, response: {response}")
            raise WebsiteContentExtractionError(f"Status code: {status_code}\nReason: {reason}")

    # check if the statusCode key exists in the metadata
    if 'statusCode' in scrape_status['metadata']:
        if scrape_status['metadata']['statusCode'] != 200:
            if scrape_status['metadata']['statusCode'] == 429:
                logger.warning(f"Throttled for Website URL {url}. Scrape status: {scrape_status}.")
                raise WebsiteContentExtractionThrottleError(f"Status code: {scrape_status['metadata']['statusCode']}. Description: {scrape_status['metadata']['description']}")
            else:
                logger.warning(f"No content found for Website URL {url}. Scrape status: {scrape_status}.")
                raise WebsiteContentExtractionError(f"Status code: {scrape_status['metadata']['statusCode']}")

    # check if the title key exists in the metadata
    if 'title' not in scrape_status['metadata']:
        logger.warning(f"No title found for Website URL {url}. Scrape status: {scrape_status}")
        title = url
    else:
        title = scrape_status['metadata']['title']
        title = clean_title(title)

    # check if the markdown key exists in the scrape_status
    if 'markdown' not in scrape_status:
        logger.error(f"No markdown found for Website URL {url}. Scrape status: {scrape_status}")
        raise WebsiteContentExtractionError(f"No content found")
    else:
        content = scrape_status['markdown']
        content = clean_content(content)

    return title, content


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
    elif data_source.type == DataSource.Type.WEBSITE:
        title, content = website_content_extraction(data_source.url)
        data_source.title = title
        data_source.content = content
    elif data_source.type == DataSource.Type.YOUTUBE:
        content = youtube_content_extraction(data_source.url)
        data_source.title = content['metadata']['title']
        data_source.content = content['content']
    elif data_source.type == DataSource.Type.GITHUB_REPO:
        default_branch = process_github_repository(data_source)
        # Use the repository name as the title
        owner, repo = extract_repo_name(data_source.url)
        data_source.default_branch = default_branch
        data_source.title = f"{owner}/{repo}"

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

