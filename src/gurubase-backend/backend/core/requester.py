from datetime import datetime, timezone
import json
import time
import logging
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from typing import List, Tuple
from django.conf import settings
from openai import OpenAI
import requests
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from abc import ABC, abstractmethod
from firecrawl import FirecrawlApp
from core.exceptions import ThrottleError, WebsiteContentExtractionError, WebsiteContentExtractionThrottleError
import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
import html2text
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
from core.exceptions import ThrottlingException

logger = logging.getLogger(__name__)

from core.guru_types import get_guru_type_prompt_map
genai.configure(api_key=settings.GEMINI_API_KEY)


def get_openai_api_key():
    from core.utils import get_default_settings
    if settings.ENV == 'selfhosted':
        try:
            default_settings = get_default_settings()
            return default_settings.openai_api_key
        except Exception:
            # Handle cases where the table/column doesn't exist yet (during migrations)
            return settings.OPENAI_API_KEY
    else:
        return settings.OPENAI_API_KEY

def get_firecrawl_api_key():
    from core.utils import get_default_settings
    if settings.ENV == 'selfhosted':
        try:
            default_settings = get_default_settings()
            return default_settings.firecrawl_api_key
        except Exception:
            # Handle cases where the table/column doesn't exist yet (during migrations)
            return settings.FIRECRAWL_API_KEY
    else:
        return settings.FIRECRAWL_API_KEY

def get_youtube_api_key():
    from core.utils import get_default_settings
    if settings.ENV == 'selfhosted':
        try:
            default_settings = get_default_settings()
            return default_settings.youtube_api_key
        except Exception:
            # Handle cases where the table/column doesn't exist yet (during migrations)
            return settings.YOUTUBE_API_KEY
    else:
        return settings.YOUTUBE_API_KEY


GURU_ENDPOINTS = {
    'processed_raw_questions': 'processed_raw_questions'
}

class GptSummary(BaseModel):
    question: str
    user_question: str
    question_slug: str
    description: str
    valid_question: bool
    user_intent: str
    answer_length: int
    enhanced_question: str

class FollowUpQuestions(BaseModel):
    questions: List[str] = Field(..., description="List of follow up questions")

class ContextDetails(BaseModel):
    context_num: int = Field(..., description="Context number")
    score: float = Field(..., description="Relevance score of the context")
    explanation: str = Field(..., description="Explanation of the context relevance")

class ContextRelevance(BaseModel):
    overall_explanation: str = Field(..., description="Overall explanation of context relevance")
    contexts: List[ContextDetails] = Field(..., description="List of context relevance details")

class ContextDetailsWithoutExplanation(BaseModel):
    context_num: int = Field(..., description="Context number")
    score: float = Field(..., description="Relevance score of the context")

class ContextRelevanceWithoutExplanation(BaseModel):
    contexts: List[ContextDetailsWithoutExplanation] = Field(..., description="List of context relevance details")

class ClaimDetails(BaseModel):
    claim: str = Field(..., description="Claim")
    score: float = Field(..., description="Groundedness score")
    explanation: str = Field(..., description="Explanation of the groundedness")

class Groundedness(BaseModel):
    overall_explanation: str = Field(..., description="Overall explanation of groundedness")
    claims: List[ClaimDetails] = Field(..., description="List of claim details")

class AnswerRelevance(BaseModel):
    overall_explanation: str = Field(..., description="Overall explanation of answer relevance")
    score: float = Field(..., description="Answer relevance score")
    
class MainContent(BaseModel):
    main_content: str = Field(..., description="Main content of the website")

class QuestionGenerationResponse(BaseModel):
    summary_sufficient: bool = Field(..., description="Whether the summary is sufficient to answer the questions")
    questions: List[str] = Field(..., description="List of questions")

class OrderGitHubFilesByImportance(BaseModel):
    files: List[str] = Field(..., description="List of files ordered by their importance")

class WebScraper(ABC):
    """Abstract base class for web scrapers"""
    @abstractmethod
    def scrape_url(self, url: str) -> Tuple[str, str]:
        """
        Scrape content from a URL
        Returns: Tuple[title: str, content: str]
        """
        pass

class FirecrawlScraper(WebScraper):
    """Firecrawl implementation of WebScraper"""
    def __init__(self):
        self.app = FirecrawlApp(api_key=get_firecrawl_api_key())

    def scrape_url(self, url: str) -> Tuple[str, str]:
        scrape_status = self.app.scrape_url(
            url, 
            params={'formats': ['markdown'], "onlyMainContent": True}
        )

        if 'statusCode' in scrape_status['metadata']:
            if scrape_status['metadata']['statusCode'] != 200:
                if scrape_status['metadata']['statusCode'] == 429:
                    raise WebsiteContentExtractionThrottleError(
                        f"Status code: {scrape_status['metadata']['statusCode']}. "
                        f"Description: {scrape_status['metadata'].get('description', '')}"
                    )
                else:
                    raise WebsiteContentExtractionError(
                        f"Status code: {scrape_status['metadata']['statusCode']}"
                    )

        title = scrape_status['metadata'].get('title', url)
        if not title:
            title = url

        if 'markdown' not in scrape_status:
            raise WebsiteContentExtractionError("No content found")

        return title, scrape_status['markdown']

    def _check_throttling(self, response):
        """Check if response indicates throttling and raise appropriate exception"""
        if 'metadata' in response and 'statusCode' in response['metadata']:
            status_code = response['metadata']['statusCode']
            if status_code == 429:
                description = response['metadata'].get('description', '')
                error_msg = f"Status code: {status_code}. Description: {description}"
                raise WebsiteContentExtractionThrottleError(error_msg)

    def _process_successful_item(self, item) -> Tuple[str, str, str]:
        """Process a single successful item from batch response"""
        url = item.get('metadata', {}).get('sourceURL', '')
        title = item.get('metadata', {}).get('title', url) or url
        content = item.get('markdown', '')
        
        if not content:
            raise ValueError("No content found")
            
        return url, title, content

    def _extract_failing_indices(self, error_str: str, urls: List[str]) -> List[Tuple[str, str]]:
        """Extract failing URLs from error message using regex"""
        import re
        failed_urls = []
        
        try:
            path_matches = re.finditer(r"'path':\s*(\[[^\]]+\])", error_str)
            failing_indices = {
                path_list[1] 
                for match in path_matches
                if len(path_list := eval(match.group(1))) > 1 
                and isinstance(path_list[1], int)
            }
            
            failed_urls = [(urls[i], error_str) for i in failing_indices]
        except Exception as parse_error:
            logger.error(f"Error parsing failure response: {parse_error}. Original error: {error_str}")
            
        return failed_urls

    def scrape_urls_batch(self, urls: List[str]) -> Tuple[List[Tuple[str, str, str]], List[Tuple[str, str]]]:
        """
        Scrape multiple URLs in a batch.
        Returns: Tuple[
            List[Tuple[url: str, title: str, content: str]],  # Successful results
            List[Tuple[url: str, error: str]]  # Failed URLs with their error messages
        ]
        """
        try:
            batch_scrape_result = self.app.batch_scrape_urls(
                urls,
                params={'formats': ['markdown'], 'onlyMainContent': True, 'timeout': settings.FIRECRAWL_TIMEOUT_MS, 'waitFor': 2000}
            )

            # batch_scrape_result = {'metadata': {'statusCode': 429, 'description': 'Rate limit exceeded'}}

            # Check for throttling first
            self._check_throttling(batch_scrape_result)
            
            successful_results = []
            failed_urls = []
            
            # Process successful results
            for item in batch_scrape_result.get('data', []):
                try:
                    result = self._process_successful_item(item)
                    successful_results.append(result)
                except ValueError as e:
                    url = item.get('metadata', {}).get('sourceURL', '')
                    failed_urls.append((url, str(e)))
            
            return successful_results, failed_urls
            
        except WebsiteContentExtractionThrottleError:
            raise
        except Exception as e:
            error_str = str(e)
            if "Bad Request" in error_str and "no longer supported" in error_str:
                failed_urls = self._extract_failing_indices(error_str, urls)
                return [], failed_urls or [(url, error_str) for url in urls]
            elif "429" in error_str:
                raise WebsiteContentExtractionThrottleError(error_str)

            logger.error(f"Batch scraping failed: {error_str}")
            return [], [(url, f"Batch scraping failed: {error_str}") for url in urls]

class Crawl4AIScraper(WebScraper):
    """Crawl4AI implementation of WebScraper using AsyncWebCrawler"""
    def __init__(self):
        self.browser_config = BrowserConfig(
            headless=True
        )
        
        # Configure markdown generator with content filter
        md_generator = DefaultMarkdownGenerator(
            # content_filter=PruningContentFilter()
        )
        
        self.run_config = CrawlerRunConfig(
            word_count_threshold=10,
            exclude_external_links=True,
            remove_overlay_elements=True,
            process_iframes=True,
            markdown_generator=md_generator,
            wait_until='domcontentloaded',  # Wait for all these events
            page_timeout=60000,  # 60 seconds timeout for page operations
            wait_for='body',  # Wait for body to be present
        )

    def scrape_url(self, url: str) -> Tuple[str, str]:
        async def _scrape():
            try:
                async with AsyncWebCrawler(config=self.browser_config) as crawler:
                    result = await crawler.arun(url=url, config=self.run_config)
                    
                    if not result.success:
                        status_code = result.status_code or 500
                        if status_code == 429:
                            raise WebsiteContentExtractionThrottleError(
                                f"Status code: {status_code}. Rate limit exceeded."
                            )
                        else:
                            raise WebsiteContentExtractionError(
                                f"Status code: {status_code}. Error: {result.error_message}"
                            )

                    # Get the title from metadata or use URL as fallback
                    title = result.metadata.get('title', url) if result.metadata else url
                    
                    # Try different markdown properties in order of preference
                    content = None
                    if hasattr(result, 'markdown'):
                        if hasattr(result.markdown, 'fit_markdown') and result.markdown.fit_markdown:
                            content = result.markdown.fit_markdown
                        elif hasattr(result.markdown, 'raw_markdown') and result.markdown.raw_markdown:
                            content = result.markdown.raw_markdown
                        else:
                            content = result.markdown
                    
                    if not content:
                        raise WebsiteContentExtractionError("No content found")

                    return title, content
            except Exception as e:
                logger.error(f"Error scraping URL {url}: {str(e)}")
                if "Page.content: Unable to retrieve content because the page is navigating" in str(e):
                    # If we hit the navigation error, try one more time with increased timeouts
                    self.run_config.wait_for_timeout = 10000  # Increase to 10 seconds
                    self.run_config.page_timeout = 90000     # Increase to 90 seconds
                    async with AsyncWebCrawler(config=self.browser_config) as crawler:
                        result = await crawler.arun(url=url, config=self.run_config)
                        title = result.metadata.get('title', url) if result.metadata else url
                        content = result.markdown
                        if not content:
                            raise WebsiteContentExtractionError("No content found after retry")
                        return title, content
                else:
                    raise

        # Run the async function in the event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # If no event loop exists, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(_scrape())

def get_web_scraper() -> WebScraper:
    """Factory function to get the appropriate web scraper based on settings"""
    from core.utils import get_default_settings

    if settings.ENV == 'selfhosted':
        default_settings = get_default_settings()
        scrape_type = default_settings.scrape_type
        scrape_type = scrape_type.lower()
    else:
        scrape_type = settings.WEBSITE_EXTRACTION

    if scrape_type == 'crawl4ai':
        return Crawl4AIScraper(), scrape_type
    elif scrape_type == 'firecrawl':
        return FirecrawlScraper(), scrape_type
    else:
        raise ValueError(f"Invalid website extraction tool: {scrape_type}")

class GuruRequester():
    def __init__(self):
        self.base_url = settings.SOURCE_GURU_BACKEND_URL
        self.headers = {'Authorization': settings.SOURCE_GURU_TOKEN}

    def get_processed_raw_questions(self, page_num):
        url = f"{self.base_url}/{GURU_ENDPOINTS['processed_raw_questions']}/?page_num={page_num}"
        response = requests.get(url, headers=self.headers)
        return response.json()


class OpenAIRequester():
    def __init__(self):
        self.client = None
        self._is_ollama = None

    def _ensure_client_initialized(self):
        if self.client is not None:
            return
        
        from core.models import Settings
        from core.utils import get_default_settings
        from django.conf import settings
        from openai import OpenAI

        if settings.ENV == 'selfhosted':
            default_settings = get_default_settings()
            if default_settings.ai_model_provider == Settings.AIProvider.OLLAMA:
                self.client = OpenAI(base_url=f'{default_settings.ollama_url}/v1', api_key='ollama')
                self._is_ollama = True
            else:
                self.client = OpenAI(api_key=default_settings.openai_api_key)
                self._is_ollama = False
        else:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self._is_ollama = False

    def _get_model_name(self, model_name):
        """Get the appropriate model name based on whether we're using Ollama"""
        self._ensure_client_initialized()
        from core.utils import get_default_settings
        default_settings = get_default_settings()
        if self._is_ollama:
            return default_settings.ollama_base_model
        else:
            return model_name

    def get_context_relevance(self, question_text, user_question, enhanced_question, guru_type_slug, contexts, model_name=settings.GPT_MODEL, cot=True):
        from core.utils import get_tokens_from_openai_response, prepare_contexts_for_context_relevance, prepare_prompt_for_context_relevance

        guru_variables = get_guru_type_prompt_map(guru_type_slug)
        prompt = prepare_prompt_for_context_relevance(cot, guru_variables, contexts)

        formatted_contexts = prepare_contexts_for_context_relevance(contexts)
        single_text_contexts = ''.join(formatted_contexts)
        user_prompt = f"QUESTION: {question_text}\n\nUSER QUESTION: {user_question}\n\nENHANCED QUESTION: {enhanced_question}\n\nCONTEXTS\n{single_text_contexts}"

        model_name = self._get_model_name(model_name)
        response = self.client.beta.chat.completions.parse(
            model=model_name,
            messages=[
                {"role": "system", "content": prompt},                
                {"role": "user", "content": user_prompt}
            ],
            response_format=ContextRelevance if cot else ContextRelevanceWithoutExplanation,
            temperature=0,
        )
        try:
            prompt_tokens, completion_tokens, cached_prompt_tokens = get_tokens_from_openai_response(response)
            usage = {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'cached_prompt_tokens': cached_prompt_tokens,
                'total_tokens': prompt_tokens + completion_tokens + cached_prompt_tokens,
                'model': model_name,
            }
            return json.loads(response.choices[0].message.content), usage, prompt, user_prompt
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON response from OpenAI")

    def rewrite_datasource_context(self, scraped_content, page_title, url, model_name="gpt-4o-mini-2024-07-18"):
        from .prompts import datasource_context_rewrite_prompt
        from core.utils import get_tokens_from_openai_response
        prompt = datasource_context_rewrite_prompt
        
        base_url = urlparse(url).scheme + "://" + urlparse(url).netloc
        prompt = prompt.format(scraped_content=scraped_content, page_title=page_title, url=base_url)
        
        logger.info(f"Prompt sending to openai for the url: {url}")
        model_name = self._get_model_name(model_name)
        response = self.client.beta.chat.completions.parse(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format=MainContent,
            temperature=0,
        )
        
        try:
            content = json.loads(response.choices[0].message.content)['main_content']
            prompt_tokens, completion_tokens, cached_prompt_tokens = get_tokens_from_openai_response(response)
            usage = {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'cached_prompt_tokens': cached_prompt_tokens,
                'total_tokens': prompt_tokens + completion_tokens + cached_prompt_tokens
            }
            return content, usage, prompt
        except (KeyError, json.JSONDecodeError):
            raise ValueError("Invalid response from OpenAI")

    def get_groundedness(self, question, contexts, model_name="gpt-4o"):
        from .prompts import groundedness_prompt
        from core.utils import get_tokens_from_openai_response
        
        prompt = groundedness_prompt
        guru_variables = get_guru_type_prompt_map(question.guru_type.slug)
        prompt = prompt.format(**guru_variables)
        model_name = self._get_model_name(model_name)
        response = self.client.beta.chat.completions.parse(
            model=model_name,
            messages=[
                {"role": "system", "content": prompt},                
                {"role": "user", "content": f"QUESTION: {question.question}\n\nCONTEXTS: {contexts}"}
            ],
            response_format=Groundedness,
            temperature=0,
        )
        try:
            prompt_tokens, completion_tokens, cached_prompt_tokens = get_tokens_from_openai_response(response)
            usage = {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'cached_prompt_tokens': cached_prompt_tokens,
                'total_tokens': prompt_tokens + completion_tokens + cached_prompt_tokens
            }
            return json.loads(response.choices[0].message.content), usage, prompt
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON response from OpenAI")

    def get_answer_relevance(self, question, answer, model_name="gpt-4o"):
        from .prompts import answer_relevance_prompt
        from core.utils import get_tokens_from_openai_response
        prompt = answer_relevance_prompt
        guru_variables = get_guru_type_prompt_map(question.guru_type.slug)
        prompt = prompt.format(**guru_variables)
        model_name = self._get_model_name(model_name)
        response = self.client.beta.chat.completions.parse(
            model=model_name,
            messages=[
                {"role": "system", "content": prompt},                
                {"role": "user", "content": f"QUESTION: {question.question}\n\nANSWER: {answer}"}
            ],
            response_format=AnswerRelevance,
            temperature=0,
        )
        try:
            prompt_tokens, completion_tokens, cached_prompt_tokens = get_tokens_from_openai_response(response)
            usage = {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'cached_prompt_tokens': cached_prompt_tokens,
                'total_tokens': prompt_tokens + completion_tokens + cached_prompt_tokens
            }
            return json.loads(response.choices[0].message.content), usage, prompt
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON response from OpenAI")
        
    def embed_texts(self, texts, model_name=settings.OPENAI_TEXT_EMBEDDING_MODEL):
        while '' in texts:
            texts.remove('')
        model_name = self._get_model_name(model_name)
        response = self.client.embeddings.create(input=texts, model=model_name)
        embeddings = []
        for embedding in response.data:
            embeddings.append(embedding.embedding)
        return embeddings

    def embed_text(self, text, model_name=settings.OPENAI_TEXT_EMBEDDING_MODEL):
        model_name = self._get_model_name(model_name)
        response = self.client.embeddings.create(input=[text], model=model_name)
        return response.data[0].embedding

    def summarize_text(self, text, guru_type, model_name=settings.GPT_MODEL):
        from .prompts import summarize_data_sources_prompt
        from core.utils import get_llm_usage_from_response
        prompt_map = get_guru_type_prompt_map(guru_type.slug)
        prompt = summarize_data_sources_prompt.format(**prompt_map, content=text)
        try:
            model_name = self._get_model_name(model_name)
            response = self.client.beta.chat.completions.parse(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format=MainContent,
                temperature=0,
            )
            return json.loads(response.choices[0].message.content)['main_content'], get_llm_usage_from_response(response, model_name)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON response from OpenAI")
        
    def summarize_guru_type(self, summarizations, guru_type, model_name=settings.GPT_MODEL):
        from .prompts import summarize_data_sources_prompt
        from core.utils import get_llm_usage_from_response
        prompt_map = get_guru_type_prompt_map(guru_type.slug)
        prompt = summarize_data_sources_prompt.format(**prompt_map, content=summarizations)
        try:
            model_name = self._get_model_name(model_name)
            response = self.client.beta.chat.completions.parse(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format=MainContent,
                temperature=0,
            )
            return json.loads(response.choices[0].message.content)['main_content'], get_llm_usage_from_response(response, model_name)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON response from OpenAI")

    def generate_questions_from_summary(self, summary, guru_type, model_name=settings.GPT_MODEL):
        from .prompts import generate_questions_from_summary_prompt
        from core.utils import get_llm_usage_from_response
        prompt_map = get_guru_type_prompt_map(guru_type.slug)
        prompt = generate_questions_from_summary_prompt.format(**prompt_map, summary=summary)
        try:
            model_name = self._get_model_name(model_name)
            response = self.client.beta.chat.completions.parse(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format=QuestionGenerationResponse,
                temperature=0,
            )
            return json.loads(response.choices[0].message.content), get_llm_usage_from_response(response, model_name)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON response from OpenAI")

    def generate_follow_up_questions(
            self, 
            questions,
            last_content, 
            guru_type, 
            contexts, 
            model_name=settings.GPT_MODEL):
        """
        Generate follow-up questions based on question history and available contexts.
        
        Args:
            questions (list): List of previous questions in the conversation
            last_content (str): Content of the last answer
            guru_type (GuruType): The guru type object
            contexts (list): List of relevant contexts from the last question
            model_name (str): The model to use for generation
        
        Returns:
            list: List of generated follow-up questions
        """
        from .prompts import generate_follow_up_questions_prompt
        
        prompt_map = get_guru_type_prompt_map(guru_type.slug)

        # Process custom instruction prompt
        custom_follow_up_prompt = prompt_map.get('custom_follow_up_prompt', '')
        if custom_follow_up_prompt and custom_follow_up_prompt.strip():
            custom_follow_up_section = f"\nCUSTOM INSTRUCTIONS (These take priority if there are conflicts with other guidelines):\n\n{custom_follow_up_prompt}\n\nDEFAULT INSTRUCTIONS (These are the default instructions that will be used if there are no conflicts with the custom instructions):\n"
        else:
            custom_follow_up_section = ""

        prompt = generate_follow_up_questions_prompt.format(
            **prompt_map,
            questions=json.dumps(questions, indent=2),
            answer=last_content,
            contexts=json.dumps(contexts, indent=2),
            num_questions=settings.FOLLOW_UP_EXAMPLE_COUNT,
            custom_follow_up_section=custom_follow_up_section
        )
        
        try:
            model_name = self._get_model_name(model_name)
            response = self.client.beta.chat.completions.parse(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format=FollowUpQuestions,
                temperature=0,
            )
            return json.loads(response.choices[0].message.content)['questions']
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from OpenAI while generating follow-up questions")
            return []
        except Exception as e:
            logger.error(f"Error generating follow-up questions: {str(e)}")
            return []

    def ask_question_with_stream(self, messages, model_name=settings.GPT_MODEL):
        """
        Ask a question with streaming response from OpenAI.
        
        Args:
            messages (list): List of message dictionaries with role and content
            model_name (str): The model to use for generation
        
        Returns:
            Generator: Stream of response chunks
        """
        model_name = self._get_model_name(model_name)
        return self.client.chat.completions.create(
            model=model_name,
            temperature=0,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
        )

    def get_summary(self, prompt, question, model_name=settings.GPT_MODEL):
        """
        Get a summary response from OpenAI.
        
        Args:
            prompt (str): The system prompt
            question (str): The user question
            model_name (str): The model to use for generation
        
        Returns:
            dict: The parsed response from OpenAI
        """
        model_name = self._get_model_name(model_name)
        return self.client.beta.chat.completions.parse(
            model=model_name,
            temperature=0,
            messages=[
                {
                    'role': 'system',
                    'content': prompt
                }
            ],
            response_format=GptSummary
        )

class GeminiEmbedder():
    def __init__(self):
        from google import genai
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def embed_texts(self, texts):
        time.sleep(0.5)
        response = self.client.models.embed_content(model="embedding-001", contents=texts)
        embeddings = response.embeddings
        if type(texts) == str:
            return embeddings[0].values
        else:
            return [embedding.values for embedding in embeddings]

            
class GeminiRequester():
    def __init__(self, model_name):
        self.client = genai.GenerativeModel(model_name)
        self.model_name = model_name

        # Added safety settings because sometimes Gemini does not complete the json response
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

    def scrape_main_content(self, content):
        from .prompts import scrape_main_content_prompt
        prompt = scrape_main_content_prompt.format(content=content)
        response = self.client.generate_content(prompt)
        return response.text

    def summarize_text(self, text, guru_type):
        from .prompts import summarize_data_sources_prompt
        from core.utils import get_llm_usage_from_response
        self.client = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "summary_suitable": {
                            "type": "boolean"
                        },
                        "reasoning": {
                            "type": "string"
                        },
                        "summary": {
                            "type": "string"
                        }
                    },
                    "required": ["summary_suitable", "reasoning", "summary"]
                },
                "response_mime_type": "application/json",
            }
        )
        prompt_map = get_guru_type_prompt_map(guru_type.slug, only_active=False)
        prompt = summarize_data_sources_prompt.format(**prompt_map, content=text)
        time.sleep(0.2)
        response = self.client.generate_content(prompt, safety_settings=self.safety_settings)
        try:
            response_json = json.loads(response.text)
        except Exception as e:
            logger.error(f"Error parsing JSON response from Gemini. Guru type: {guru_type.slug}. Text: {text[:100]}.... Response: {response.text}", exc_info=True)
            raise ValueError("Invalid JSON response from Gemini")
        return response_json, get_llm_usage_from_response(response, self.model_name)

    def generate_questions_from_summary(self, summary, guru_type):
        from .prompts import generate_questions_from_summary_prompt
        from core.utils import get_llm_usage_from_response
        self.client = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "summary_sufficient": {
                            "type": "boolean"
                        },
                        "questions": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        }
                    },
                    "required": ["summary_sufficient", "questions"]
                },
                "response_mime_type": "application/json",
            }
        )
        prompt_map = get_guru_type_prompt_map(guru_type.slug)
        prompt = generate_questions_from_summary_prompt.format(**prompt_map, summary=summary)
        time.sleep(0.2)
        response = self.client.generate_content(prompt, safety_settings=self.safety_settings)
        try:
            response_json = json.loads(response.text)
        except Exception as e:
            logger.error(f"Error parsing JSON response from Gemini. Guru type: {guru_type.slug}. Summary: {summary[:100]}.... Response: {response.text}", exc_info=True)
            raise ValueError("Invalid JSON response from Gemini")
        return response_json, get_llm_usage_from_response(response, self.model_name)

    def generate_topics_from_summary(self, summary, guru_type_name, github_topics, github_description):
        from .prompts import generate_topics_from_summary_prompt
        self.client = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "topics": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        }
                    }
                },
                "response_mime_type": "application/json",
            }
        )
        prompt = generate_topics_from_summary_prompt.format(guru_type=guru_type_name, summary=summary, github_topics=github_topics, github_description=github_description)
        time.sleep(0.2)
        response = self.client.generate_content(prompt, safety_settings=self.safety_settings)
        try:
            response_json = json.loads(response.text)
        except Exception as e:
            logger.error(f"generate_topics_from_summary: Error parsing JSON response from Gemini. Guru type: {guru_type_name}. Summary: {summary[:100]}.... Response: {response.text}", exc_info=True)
            raise ValueError("Invalid JSON response from Gemini")
        return response_json

    def generate_follow_up_questions(
            self, 
            questions, 
            last_content, 
            guru_type, 
            contexts, 
            model_name=None):
        """
        Generate follow-up questions based on question history and available contexts using Gemini.
        
        Args:
            questions (list): List of previous questions in the conversation
            last_content (str): Content of the last answer
            guru_type (GuruType): The guru type object
            contexts (list): List of relevant contexts from the last question
            model_name (str): Optional model override (unused, kept for compatibility)
        
        Returns:
            list: List of generated follow-up questions
        """
        from .prompts import generate_follow_up_questions_prompt
        
        self.client = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "questions": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        }
                    },
                    "required": ["questions"]
                },
                "response_mime_type": "application/json",
            }
        )
        
        prompt_map = get_guru_type_prompt_map(guru_type.slug)

        # Process custom instruction prompt
        custom_follow_up_prompt = prompt_map.get('custom_follow_up_prompt', '')
        if custom_follow_up_prompt and custom_follow_up_prompt.strip():
            custom_follow_up_section = f"\nCUSTOM INSTRUCTIONS (These take priority if there are conflicts with other guidelines):\n\n{custom_follow_up_prompt}\n\nDEFAULT INSTRUCTIONS (These are the default instructions that will be used if there are no conflicts with the custom instructions):\n"
        else:
            custom_follow_up_section = ""

        prompt = generate_follow_up_questions_prompt.format(
            **prompt_map,
            questions=json.dumps(questions, indent=2),
            answer=last_content,
            contexts=json.dumps(contexts, indent=2),
            num_questions=settings.FOLLOW_UP_EXAMPLE_COUNT,
            custom_follow_up_section=custom_follow_up_section
        )
        
        try:
            response = self.client.generate_content(prompt, safety_settings=self.safety_settings)
            response_json = json.loads(response.text)
            return response_json.get('questions', [])
        except Exception as e:
            logger.error(f"Error generating follow-up questions with Gemini: {str(e)}", exc_info=True)
            return []


class GitHubRequester():
    def __init__(self):
        self.base_url = "https://api.github.com/repos"
        self.headers = {
            'Accept': 'application/vnd.github+json', 
            'X-GitHub-Api-Version': '2022-11-28'
        }
        if settings.GITHUB_TOKEN:
            self.headers['Authorization'] = f'Bearer {settings.GITHUB_TOKEN}'

    def get_github_repo_details(self, github_url):
        owner = github_url.split('https://github.com/')[1].split('/')[0]
        repo = github_url.split('https://github.com/')[1].split('/')[1]
        url = f"{self.base_url}/{owner}/{repo}"
        response = requests.get(url, headers=self.headers, timeout=10)
        if response.status_code != 200:
            raise ValueError(f"Error getting GitHub repo details for {github_url}. Status code: {response.status_code}. Response: {response.text}")
        # {"status": "403", "message": "API rate limit exceeded for 34.66.36.109. (But here's the good news: Authenticated requests get a higher rate limit. Check out the documentation for more details.)"}
        if response.json().get('status') == '403':
            raise ValueError(f"GitHub API rate limit exceeded for {github_url}")
        return response.json()

class JiraRequester():
    def __init__(self, integration):
        """
        Initialize Jira Requester with integration credentials
        Args:
            integration (Integration): Integration model instance containing Jira credentials
        """
        from atlassian import Jira
        self.url = f"https://{integration.jira_domain}"
        self.jira = Jira(
            url=self.url,
            username=integration.jira_user_email,
            password=integration.jira_api_key
        )

    def list_issues(self, jql_query, batch=50, start_time=None, end_time=None):
        """
        List Jira issues using JQL query with pagination
        Args:
            jql_query (str): JQL query string to filter issues
            batch (int): Maximum number of results to fetch per request
            start_time (str, optional): Start time for filtering issues.
            end_time (str, optional): End time for filtering issues.
        Returns:
            list: List of Jira issues matching the query
        Raises:
            ValueError: If API request fails
        """
        try:
            all_issues = []
            current_start = 0
            page_size = batch

            query = f'({jql_query})'  # Enclose to prevent operator reordering
            if start_time:
                query += f" AND created >= '{start_time}'"
            if end_time:
                query += f" AND created < '{end_time}'"
            
            while True:
                # Get issues using JQL
                issues_data = self.jira.jql(query, start=current_start, limit=page_size)
                issues = issues_data.get('issues', [])
                
                if not issues:
                    break
                    
                for issue in issues:
                    formatted_issue = {
                        'id': issue.get('id'),
                        # 'key': issue.get('key'),
                        # 'summary': issue.get('fields', {}).get('summary'),
                        # 'issue_type': issue.get('fields', {}).get('issuetype', {}).get('name'),
                        # 'status': issue.get('fields', {}).get('status', {}).get('name'),
                        # 'priority': issue.get('fields', {}).get('priority', {}).get('name'),
                        # 'assignee': issue.get('fields', {}).get('assignee', {}).get('displayName'),
                        'link': f"{self.url}/browse/{issue.get('key')}"
                    }
                    all_issues.append(formatted_issue)
                
                # If we got fewer issues than requested, we've reached the end
                if len(issues) < page_size:
                    break
                    
                # Move to the next page
                current_start += page_size
                
            return all_issues
        except Exception as e:
            logger.error(f"Error listing Jira issues: {str(e)}", exc_info=True)
            if "401" in str(e):
                raise ValueError("Invalid Jira credentials")
            elif "403" in str(e):
                raise ValueError("Jira API access forbidden")
            else:
                raise ValueError(str(e))

    def get_issue(self, issue_key):
        """
        Get detailed information about a specific Jira issue
        Args:
            issue_key (str): Key of the Jira issue (e.g., 'PROJECT-123')
        Returns:
            dict: Issue details
        Raises:
            ValueError: If API request fails
        """
        try:
            # Get issue details
            issue = self.jira.issue(issue_key)
            
            fields = issue.get('fields', {})
            comments = []
            
            # Get comments if available
            for comment in fields.get('comment', {}).get('comments', []):
                comments.append({
                    'content': comment.get('body', '')
                })
            
            # Format issue content with description and comments
            title = fields.get('summary', '')
            
            # Format the content with issue description and comments
            formatted_content = f"<Jira Issue>\n"
            
            # Add description if available
            if fields.get('summary'):
                formatted_content += f"Title: {title}\n"
            if fields.get('description'):
                formatted_content += f"Description: {fields.get('description', '')}\n"
            
            formatted_content += f"</Jira Issue>\n"
            
            # Add comments if available
            for comment in comments:
                formatted_content += f"<Jira Comment>\n{comment['content']}\n</Jira Comment>\n"
            
            return {
                'id': issue.get('id'),
                'title': title,
                'content': formatted_content,
                # 'key': issue.get('key'),
                # 'summary': fields.get('summary'),
                # 'description': fields.get('description'),
                # 'issue_type': fields.get('issuetype', {}).get('name'),
                # 'status': fields.get('status', {}).get('name'),
                # 'priority': fields.get('priority', {}).get('name'),
                # 'assignee': fields.get('assignee', {}).get('displayName'),
                # 'reporter': fields.get('reporter', {}).get('displayName'),
                # 'created': fields.get('created'),
                # 'updated': fields.get('updated'),
                'comments': comments,
                'link': f"{self.url}/browse/{issue.get('key')}"
            }
        except Exception as e:
            if "401" in str(e):
                raise ValueError("Invalid Jira credentials")
            elif "403" in str(e):
                raise ValueError("Jira API access forbidden")
            elif "404" in str(e):
                raise ValueError(f"Issue {issue_key} not found")
            else:
                raise ValueError(f"Error getting Jira issue: {str(e)}")

class ZendeskRequester():
    def __init__(self, integration):
        """
        Initialize ZendeskRequester with integration credentials
        Args:
            integration (Integration): Integration model instance containing Zendesk credentials
        """
        if not all([integration.zendesk_domain, integration.zendesk_user_email, integration.zendesk_api_token]):
            raise ValueError("Zendesk credentials (domain, email, api_token) are missing in the integration settings.")

        self.domain = integration.zendesk_domain
        self.base_url = f"https://{self.domain}/api/v2"
        self.auth = (f"{integration.zendesk_user_email}/token", integration.zendesk_api_token)

    def list_tickets(self, batch_size=400, start_time=None, end_time=None):
        """
        List Zendesk tickets using incremental export API with pagination and date filtering.
        Args:
            batch_size (int): Number of tickets to fetch per request
            start_time (str): Start time in format YYYY-MM-DD
            end_time (str): End time in format YYYY-MM-DD
        Returns:
            list: List of formatted Zendesk tickets with unique links
        Raises:
            ValueError: If API request fails
        """
        all_tickets = []
        seen_links = set()  # Track unique links
        
        # Convert date strings to UTC timestamps
        start_timestamp = None
        end_timestamp = None
        if start_time:
            start_timestamp = int(datetime.strptime(start_time, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp())
        if end_time:
            end_timestamp = int(datetime.strptime(end_time, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp())

        # Use incremental export endpoint
        url = f"{self.base_url}/incremental/tickets.json"
        params = {
            "per_page": batch_size
        }
        if start_timestamp:
            params["start_time"] = start_timestamp

        max_retries = 3
        base_delay = 10  # 10 seconds delay between requests for rate limiting

        try:
            while url:
                retry_count = 0
                data = None
                while retry_count < max_retries:
                    try:
                        response = requests.get(url, auth=self.auth, params=params, timeout=20)
                        
                        # Check for rate limiting
                        if response.status_code == 429:
                            retry_after = int(response.headers.get('Retry-After', base_delay * (2 ** retry_count)))
                            logger.warning(f"Zendesk API rate limit exceeded. Waiting {retry_after} seconds before retry.")
                            time.sleep(retry_after)
                            retry_count += 1
                            continue
                            
                        response.raise_for_status()
                        data = response.json()
                        tickets_batch = data.get('tickets', [])

                        # Process tickets and check timestamps
                        for ticket in tickets_batch:
                            # Skip tickets after end_time
                            if end_timestamp and ticket.get('generated_timestamp', 0) > end_timestamp:
                                continue
                                
                            formatted_ticket = self._format_ticket(ticket)
                            # Only add ticket if its link is unique
                            if formatted_ticket['link'] and formatted_ticket['link'] not in seen_links:
                                seen_links.add(formatted_ticket['link'])
                                all_tickets.append(formatted_ticket)

                        # Check if we've reached the end of our time range
                        if data.get('end_of_stream', False) or (end_timestamp and data.get('end_time', 0) > end_timestamp):
                            url = None
                            break

                        # Check for next page
                        if data.get('next_page'):
                            url = data.get('next_page')
                            params = {}  # Clear params as they're included in next_page URL
                            time.sleep(base_delay)  # Rate limiting delay
                        else:
                            url = None  # Exit loop if no more pages
                            
                        # If we get here, the request was successful
                        break
                        
                    except requests.exceptions.RequestException as e:
                        if retry_count == max_retries - 1:
                            status_code = e.response.status_code if e.response is not None else None
                            error_text = str(e)
                            if status_code == 401:
                                error_text = "Authentication failed. Check Zendesk email and API token."
                            elif status_code == 403:
                                error_text = "Permission denied. Ensure the API token has the required scopes."
                            elif status_code == 404:
                                error_text = f"Resource not found or invalid Zendesk domain: {self.domain}"
                            elif status_code == 429:
                                error_text = "Zendesk API rate limit exceeded."

                            logger.error(f"Zendesk API error listing tickets: {error_text}", exc_info=True)
                            raise ValueError(f"Failed to list Zendesk tickets: {error_text}")
                        
                        retry_count += 1
                        time.sleep(base_delay * (2 ** retry_count))
                        continue

                if data is None:
                    raise ThrottleError(f"Failed to list Zendesk tickets. Encountered a rate limit error.")

            return all_tickets
        except Exception as e:
            logger.error(f"Unexpected error listing Zendesk tickets: {e}", exc_info=True)
            raise ValueError(f"An unexpected error occurred: {str(e)}")

    def get_a_ticket(self):
        """
        Get a single Zendesk ticket.
        Returns:
            dict: Formatted Zendesk ticket
        Raises:
            ValueError: If API request fails
        """
        # Use the standard tickets endpoint and filter in Python
        url = f"{self.base_url}/tickets.json?page[size]=1&sort_by=created_at&sort_order=desc"

        try:
            response = requests.get(url, auth=self.auth, timeout=20)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

            data = response.json()
            tickets_batch = data.get('tickets', [])

            # Filter for solved tickets and format
            for ticket in tickets_batch:
                return self._format_ticket(ticket)

        except requests.exceptions.RequestException as e:
            status_code = e.response.status_code if e.response is not None else None
            error_text = str(e)
            if status_code == 401:
                error_text = "Authentication failed. Check Zendesk email and API token."
            elif status_code == 403:
                error_text = "Permission denied. Ensure the API token has the required scopes."
            elif status_code == 404:
                 error_text = f"Resource not found or invalid Zendesk domain: {self.domain}"
            elif status_code == 429:
                error_text = "Zendesk API rate limit exceeded."

            logger.error(f"Zendesk API error listing tickets: {error_text}", exc_info=True)
            raise ValueError(f"Failed to list Zendesk tickets: {error_text}")
        except Exception as e:
            logger.error(f"Unexpected error listing Zendesk tickets: {e}", exc_info=True)
            raise ValueError(f"An unexpected error occurred: {str(e)}")

    def get_ticket(self, ticket_id):
        """
        Get details and comments for a specific Zendesk ticket and format them.
        Args:
            ticket_id (int): ID of the Zendesk ticket
        Returns:
            dict: Formatted ticket data including comments, similar to Jira's _format_issue
        Raises:
            ValueError: If API request fails or ticket not found
        """
        max_retries = 3
        base_delay = 1

        try:
            # 1. Fetch ticket details
            ticket_url = f"{self.base_url}/tickets/{ticket_id}.json"
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    response = requests.get(ticket_url, auth=self.auth, timeout=15)
                    
                    # Check for rate limiting
                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', base_delay * (2 ** retry_count)))
                        logger.warning(f"Zendesk API rate limit exceeded. Waiting {retry_after} seconds before retry.")
                        time.sleep(retry_after)
                        retry_count += 1
                        continue
                        
                    response.raise_for_status()
                    ticket_data = response.json().get('ticket', {})

                    if not ticket_data:
                        raise ValueError(f"Ticket with ID {ticket_id} not found or invalid response.")

                    # 2. Format base ticket data using the helper method
                    formatted_ticket = self._format_ticket(ticket_data)

                    # 3. Fetch comments using the existing method
                    comments = self._get_ticket_comments(ticket_id)

                    # 4. Append comment content to the existing formatted content
                    for comment_data in comments:
                        formatted_ticket['content'] += f"\n\n{comment_data['content']}"

                    # 5. Return combined data
                    return formatted_ticket
                    
                except requests.exceptions.RequestException as e:
                    if retry_count == max_retries - 1:
                        status_code = e.response.status_code if e.response is not None else None
                        error_text = str(e)
                        if status_code == 401:
                            error_text = "Authentication failed. Check Zendesk email and API token."
                        elif status_code == 403:
                            error_text = "Permission denied. Ensure the API token has the required scopes."
                        elif status_code == 404:
                            error_text = f"Ticket with ID {ticket_id} not found or invalid Zendesk domain: {self.domain}"
                        elif status_code == 429:
                            error_text = "Zendesk API rate limit exceeded."

                        logger.error(f"Zendesk API error getting ticket {ticket_id}: {error_text}", exc_info=True)
                        raise ValueError(f"Failed to get ticket {ticket_id}: {error_text}")
                    
                    retry_count += 1
                    time.sleep(base_delay * (2 ** retry_count))
                    continue

            raise ThrottleError(f"Failed to get ticket {ticket_id}. Encountered a rate limit error.")
        except ThrottleError as e:
            raise e
        except ValueError as e:
            # Catch errors from get_ticket_comments and re-raise
            logger.error(f"Error processing comments for ticket {ticket_id}: {e}", exc_info=True)
            raise ValueError(f"Failed to get comments for ticket {ticket_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting ticket {ticket_id}: {e}", exc_info=True)
            raise ValueError(f"An unexpected error occurred while getting ticket {ticket_id}: {str(e)}")

    def _get_ticket_comments(self, ticket_id, batch_size=100):
        """
        Get comments for a specific Zendesk ticket with pagination
        Args:
            ticket_id (int): ID of the Zendesk ticket
            batch_size (int): Number of comments to fetch per request
        Returns:
            list: List of formatted comments
        Raises:
            ValueError: If API request fails
        """
        all_comments = []
        url = f"{self.base_url}/tickets/{ticket_id}/comments.json?page[size]={batch_size}&sort_by=created_at&sort_order=asc"
        max_retries = 3
        base_delay = 1

        try:
            while url:
                retry_count = 0
                data = None
                while retry_count < max_retries:
                    try:
                        response = requests.get(url, auth=self.auth, timeout=20)
                        
                        # Check for rate limiting
                        if response.status_code == 429:
                            retry_after = int(response.headers.get('Retry-After', base_delay * (2 ** retry_count)))
                            logger.warning(f"Zendesk API rate limit exceeded. Waiting {retry_after} seconds before retry.")
                            time.sleep(retry_after)
                            retry_count += 1
                            continue
                            
                        response.raise_for_status()
                        data = response.json()
                        comments = data.get('comments', [])
                        all_comments.extend([self._format_comment(comment) for comment in comments])

                        # Check for cursor-based pagination meta data
                        if data.get('meta', {}).get('has_more'):
                            url = data.get('links', {}).get('next')

                            time.sleep(0.5)
                        else:
                            url = None
                            
                        # If we get here, the request was successful
                        break
                        
                    except requests.exceptions.RequestException as e:
                        if retry_count == max_retries - 1:
                            status_code = e.response.status_code if e.response is not None else None
                            error_text = str(e)
                            if status_code == 401:
                                error_text = "Authentication failed. Check Zendesk email and API token."
                            elif status_code == 403:
                                error_text = "Permission denied. Ensure the API token has the required scopes."
                            elif status_code == 404:
                                error_text = f"Ticket with ID {ticket_id} not found or invalid Zendesk domain: {self.domain}"
                            elif status_code == 429:
                                error_text = "Zendesk API rate limit exceeded."

                            logger.error(f"Zendesk API error getting comments for ticket {ticket_id}: {error_text}", exc_info=True)
                            raise ValueError(f"Failed to get comments for ticket {ticket_id}: {error_text}")
                        
                        retry_count += 1
                        time.sleep(base_delay * (2 ** retry_count))
                        continue

                if data is None:
                    # Tried all retries, raise a ThrottleError
                    raise ThrottleError(f"Failed to get comments for ticket {ticket_id}. Encountered a rate limit error.")
            return all_comments
        except ThrottleError as e:
            raise e
        except Exception as e:
            logger.error(f"Unexpected error getting comments for ticket {ticket_id}: {e}", exc_info=True)
            raise ValueError(f"An unexpected error occurred while getting comments: {str(e)}")

    def _format_ticket(self, ticket):
        """
        Format a Zendesk ticket into a dictionary.
        Args:
            ticket (dict): Ticket data from Zendesk API
        Returns:
            dict: Formatted ticket data
        """
        ticket_id = ticket.get('id')
        subject = ticket.get('subject', 'No Subject')
        status = ticket.get('status')
        created_at = ticket.get('created_at')
        updated_at = ticket.get('updated_at')

        link = f"https://{self.domain}/agent/tickets/{ticket_id}" if ticket_id else None

        content = f"<Zendesk Ticket>\n\nSubject: {subject}\n\n</Zendesk Ticket>"

        return {
            'id': ticket_id,
            'link': link,
            'title': subject,
            'status': status,
            'created_at': created_at,
            'updated_at': updated_at,
            'content': content
        }

    def _format_comment(self, comment):
        """
        Format a Zendesk comment into a dictionary
        Args:
            comment (dict): Comment data from Zendesk API
        Returns:
            dict: Formatted comment data
        """
        body = comment.get('body', '')
        content = f"<Zendesk Comment>\n\n{body}\n\n</Zendesk Comment>"

        return {
            'id': comment.get('id'),
            'body': body,
            'author_id': comment.get('author_id'),
            'created_at': comment.get('created_at'),
            'public': comment.get('public', True),
            'content': content
        }

    def list_articles(self, batch_size=400, start_time=None, end_time=None):
        """
        List Zendesk help center articles using incremental export API with pagination and date filtering.
        Args:
            batch_size (int): Number of articles to fetch per request
            start_time (str): Start time in format YYYY-MM-DD
            end_time (str): End time in format YYYY-MM-DD
        Returns:
            list: List of formatted, non-draft Zendesk articles with unique links
        Raises:
            ValueError: If API request fails
        """
        all_articles = []
        seen_links = set()  # Track unique links
        
        # Convert date strings to UTC timestamps
        start_timestamp = None
        end_timestamp = None
        if start_time:
            start_timestamp = int(datetime.strptime(start_time, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp())
        if end_time:
            end_timestamp = int(datetime.strptime(end_time, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp())

        # Use incremental export endpoint
        url = f"{self.base_url}/help_center/incremental/articles"
        params = {
            "per_page": batch_size
        }
        if start_timestamp:
            params["start_time"] = start_timestamp

        max_retries = 3
        base_delay = 10  # 10 seconds delay between requests for rate limiting

        try:
            while url:
                retry_count = 0
                data = None
                while retry_count < max_retries:
                    try:
                        response = requests.get(url, auth=self.auth, params=params, timeout=20)
                        
                        # Check for rate limiting
                        if response.status_code == 429:
                            retry_after = int(response.headers.get('Retry-After', base_delay * (2 ** retry_count)))
                            logger.warning(f"Zendesk API rate limit exceeded. Waiting {retry_after} seconds before retry.")
                            time.sleep(retry_after)
                            retry_count += 1
                            continue
                            
                        response.raise_for_status()
                        data = response.json()
                        articles_batch = data.get('articles', [])

                        # Process articles and check timestamps
                        for article in articles_batch:
                            # Skip draft articles
                            if article.get('draft', True):
                                continue
                                
                            # Convert created_at to timestamp and check against end_time
                            created_at = article.get('created_at')
                            if created_at:
                                article_timestamp = int(datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp())
                                if end_timestamp and article_timestamp > end_timestamp:
                                    continue
                                    
                            formatted_article = self._format_article(article)
                            # Only add article if its link is unique
                            if formatted_article['link'] and formatted_article['link'] not in seen_links:
                                seen_links.add(formatted_article['link'])
                                all_articles.append(formatted_article)

                        # Check if we've reached the end of our time range
                        if data.get('end_of_stream', False) or (end_timestamp and data.get('end_time', 0) > end_timestamp):
                            url = None
                            break

                        # Check for next page
                        if data.get('next_page'):
                            url = data.get('next_page')
                            params = {}  # Clear params as they're included in next_page URL
                            time.sleep(base_delay)  # Rate limiting delay
                        else:
                            url = None  # Exit loop if no more pages
                            
                        # If we get here, the request was successful
                        break
                        
                    except requests.exceptions.RequestException as e:
                        if retry_count == max_retries - 1:
                            status_code = e.response.status_code if e.response is not None else None
                            error_text = str(e)
                            if status_code == 401:
                                error_text = "Authentication failed. Check Zendesk email and API token."
                            elif status_code == 403:
                                error_text = "Permission denied. Ensure the API token has the required scopes."
                            elif status_code == 404:
                                error_text = f"Resource not found or invalid Zendesk domain: {self.domain}"
                            elif status_code == 429:
                                error_text = "Zendesk API rate limit exceeded."

                            logger.error(f"Zendesk API error listing articles: {error_text}", exc_info=True)
                            raise ValueError(f"Failed to list Zendesk articles: {error_text}")
                        
                        retry_count += 1
                        time.sleep(base_delay * (2 ** retry_count))
                        continue

                if data is None:
                    raise ThrottleError(f"Failed to list Zendesk articles. Encountered a rate limit error.")

            return all_articles
        except Exception as e:
            logger.error(f"Unexpected error listing Zendesk articles: {e}", exc_info=True)
            raise ValueError(f"An unexpected error occurred: {str(e)}")

    def get_article(self, article_id, batch_size=100):
        """
        Get a specific Zendesk help center article and its comments, formatted similarly to tickets.
        Args:
            article_id (int): ID of the Zendesk article
            batch_size (int): Pagination size for comments
        Returns:
            dict: Formatted article data including comments
        Raises:
            ValueError: If API request fails or article not found
        """
        max_retries = 3
        base_delay = 1

        try:
            # 1. Fetch article details
            article_url = f"{self.base_url}/help_center/articles/{article_id}.json"
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    response = requests.get(article_url, auth=self.auth, timeout=15)
                    
                    # Check for rate limiting
                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', base_delay * (2 ** retry_count)))
                        logger.warning(f"Zendesk API rate limit exceeded. Waiting {retry_after} seconds before retry.")
                        time.sleep(retry_after)
                        retry_count += 1
                        continue
                        
                    response.raise_for_status()
                    article_data = response.json().get('article', {})

                    if not article_data:
                        raise ValueError(f"Article with ID {article_id} not found or invalid response.")

                    # 2. Format article
                    formatted_article = self._format_article(article_data)

                    # 3. Fetch and format comments
                    comments = self._get_article_comments(article_id, batch_size=batch_size)
                    for comment_data in comments:
                        formatted_article['content'] += f"\n\n{comment_data['content']}"

                    # 4. Return combined data
                    return formatted_article
                    
                except requests.exceptions.RequestException as e:
                    if retry_count == max_retries - 1:
                        status_code = e.response.status_code if e.response is not None else None
                        error_text = str(e)
                        if status_code == 401:
                            error_text = "Authentication failed. Check Zendesk email and API token."
                        elif status_code == 403:
                            error_text = "Permission denied. Ensure the API token has the required scopes."
                        elif status_code == 404:
                            error_text = f"Article with ID {article_id} not found or invalid Zendesk domain: {self.domain}"
                        elif status_code == 429:
                            error_text = "Zendesk API rate limit exceeded."

                        logger.error(f"Zendesk API error getting article {article_id}: {error_text}", exc_info=True)
                        raise ValueError(f"Failed to get article {article_id}: {error_text}")
                    
                    retry_count += 1
                    time.sleep(base_delay * (2 ** retry_count))
                    continue

            raise ThrottleError(f"Failed to get article {article_id}. Encountered a rate limit error.")
        except ThrottleError as e:
            raise e
        except ValueError as e:
            # Catch errors from get_article_comments and re-raise
            logger.error(f"Error processing comments for article {article_id}: {e}", exc_info=True)
            raise ValueError(f"Failed to get comments for article {article_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting article {article_id}: {e}", exc_info=True)
            raise ValueError(f"An unexpected error occurred while getting article {article_id}: {str(e)}")

    def _get_article_comments(self, article_id, batch_size=100):
        """
        Get comments for a specific Zendesk article with pagination.
        Args:
            article_id (int): ID of the Zendesk article
            batch_size (int): Number of comments to fetch per request
        Returns:
            list: List of formatted comments
        Raises:
            ValueError: If API request fails
        """
        all_comments = []
        url = f"{self.base_url}/help_center/articles/{article_id}/comments.json?page[size]={batch_size}&sort_by=created_at&sort_order=asc"
        max_retries = 3
        base_delay = 1

        try:
            while url:
                retry_count = 0
                data = None
                while retry_count < max_retries:
                    try:
                        response = requests.get(url, auth=self.auth, timeout=20)
                        
                        # Check for rate limiting
                        if response.status_code == 429:
                            retry_after = int(response.headers.get('Retry-After', base_delay * (2 ** retry_count)))
                            logger.warning(f"Zendesk API rate limit exceeded. Waiting {retry_after} seconds before retry.")
                            time.sleep(retry_after)
                            retry_count += 1
                            continue
                            
                        response.raise_for_status()
                        data = response.json()
                        comments = data.get('comments', [])
                        all_comments.extend([self._format_article_comment(comment) for comment in comments])

                        # Check for cursor-based pagination meta data
                        if data.get('meta', {}).get('has_more'):
                            url = data.get('links', {}).get('next')
                            time.sleep(0.5)
                        else:
                            url = None
                            
                        # If we get here, the request was successful
                        break
                        
                    except requests.exceptions.RequestException as e:
                        if retry_count == max_retries - 1:
                            status_code = e.response.status_code if e.response is not None else None
                            error_text = str(e)
                            if status_code == 401:
                                error_text = "Authentication failed. Check Zendesk email and API token."
                            elif status_code == 403:
                                error_text = "Permission denied. Ensure the API token has the required scopes."
                            elif status_code == 404:
                                error_text = f"Article with ID {article_id} not found or invalid Zendesk domain: {self.domain}"
                            elif status_code == 429:
                                error_text = "Zendesk API rate limit exceeded."

                            logger.error(f"Zendesk API error getting comments for article {article_id}: {error_text}", exc_info=True)
                            raise ValueError(f"Failed to get comments for article {article_id}: {error_text}")
                        
                        retry_count += 1
                        time.sleep(base_delay * (2 ** retry_count))
                        continue

                if data is None:
                    # Tried all retries, raise a ThrottleError
                    raise ThrottleError(f"Failed to get comments for article {article_id}. Encountered a rate limit error.")
                    
            all_comments.sort(key=lambda x: x['created_at'])
            return all_comments
        except ThrottleError as e:
            raise e
        except Exception as e:
            logger.error(f"Unexpected error getting comments for article {article_id}: {e}", exc_info=True)
            raise ValueError(f"An unexpected error occurred while getting comments: {str(e)}")

    def _format_article(self, article):
        """
        Format a Zendesk article into a dictionary.
        Args:
            article (dict): Article data from Zendesk API
        Returns:
            dict: Formatted article data
        """
        title = article.get('title', 'No Title')
        body_html = article.get('body', article.get('body_html', ''))
        body_markdown = html2text.html2text(body_html) if body_html else ''

        content = f"<Zendesk Article>\n\nTitle: {title}\n\n{body_markdown}\n\n</Zendesk Article>"

        return {
            'id': article.get('id'),
            'link': article.get('html_url', f"https://{self.domain}/hc/en-us/articles/{article.get('id')}"),
            'title': title,
            'created_at': article.get('created_at'),
            'updated_at': article.get('updated_at'),
            'content': content,
            'draft': article.get('draft')
        }

    def _format_article_comment(self, comment):
        """
        Format a Zendesk article comment into a dictionary.
        Args:
            comment (dict): Comment data from Zendesk API
        Returns:
            dict: Formatted comment data
        """
        body_html = comment.get('body', '')
        body_markdown = html2text.html2text(body_html)
        content = f"<Zendesk Article Comment>\n\n{body_markdown}\n\n</Zendesk Article Comment>"

        return {
            'id': comment.get('id'),
            'author_id': comment.get('author_id'),
            'created_at': comment.get('created_at'),
            'public': comment.get('public', True),
            'content': content
        }

class CloudflareRequester():
    def __init__(self):
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.zone_id = settings.CLOUDFLARE_ZONE_ID
        self.auth_token = settings.CLOUDFLARE_AUTH_TOKEN
        self.headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json'
        }
        
        self.zone_url = f"{self.base_url}/zones/{self.zone_id}"

    def purge_cache(self, guru_slug, question_slug):
        if settings.ENV != 'production':
            logger.info("Skipping cache purge in non-production environment")
            return

        url = f"{self.zone_url}/purge_cache"
        data = {
            "files": [
                f"https://gurubase.io/g/{guru_slug}/{question_slug}"
            ]
        }
        try:
            response = requests.post(url, headers=self.headers, json=data, timeout=10)

            if response.status_code != 200:
                logger.error(f"Error purging cache for {guru_slug}/{question_slug}. Status code: {response.status_code}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error purging cache for {guru_slug}/{question_slug}", exc_info=True)
            return False

class RerankerRequester():
    def __init__(self):
        self.headers = {"Content-Type": "application/json"}
        if settings.RERANK_API_KEY:
            self.headers["Authorization"] = f"Bearer {settings.RERANK_API_KEY}"

    def rerank_health_check(self):
        data = json.dumps({"query":"What is Deep Learning?", "texts": ["Deep Learning is not...", "Deep learning is..."]})
        try:
            response = requests.post(settings.RERANK_API_URL, headers=self.headers, data=data, timeout=10)
        except Exception as e:
            logger.error(f"Error reranking health check", exc_info=True)
            return False
        if response.status_code == 200:
            return True
        else:
            logger.error(f"Reranker health check failed. Status code: {response.status_code}. Response: {response.text}")
            return False


class Auth0Requester():
    def __init__(self):
        self.base_url = settings.AUTH0_MANAGEMENT_API_DOMAIN
        self.client_id = settings.AUTH0_CLIENT_ID
        self.client_secret = settings.AUTH0_CLIENT_SECRET
        self.audience = f"{settings.AUTH0_MANAGEMENT_API_DOMAIN}api/v2/"
        self.token = None
        self.token_expiry = 0

    def _get_management_token(self):
        if self.token and time.time() < self.token_expiry:
            return self.token

        url = f"{self.base_url}oauth/token"
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'audience': self.audience
        }
        headers = {'content-type': 'application/x-www-form-urlencoded'}

        try:
            response = requests.post(url, headers=headers, data=data, timeout=10)
            response.raise_for_status()
            token_data = response.json()
            self.token = token_data['access_token']
            # Set expiry 5 minutes before actual expiry to be safe
            self.token_expiry = time.time() + token_data['expires_in'] - 300
            return self.token
        except Exception as e:
            logger.error("Error getting Auth0 management token", exc_info=True)
            return None

    def delete_user(self, user_id):
        token = self._get_management_token()
        if not token:
            return False

        url = f"{self.base_url}api/v2/users/{user_id}"
        headers = {'Authorization': f'Bearer {token}'}
        
        try:
            response = requests.delete(url, headers=headers, timeout=10)
            if not response.ok:
                logger.error(f"Error deleting user {user_id}. Status code: {response.status_code}. Response: {response.text}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error deleting user {user_id}", exc_info=True)
            return False


class WebshareRequester():
    def __init__(self):
        self.base_url = "https://proxy.webshare.io/api/v2"
        self.token = settings.WEBSHARE_TOKEN
        self.headers = {
            'Authorization': f'Token {self.token}'
        }

    def get_proxies(self):
        url = f"{self.base_url}/proxy/list?mode=direct&page=1&page_size=100&valid=true&ordering=-last_verification,created_at"
        response = requests.get(url, headers=self.headers, timeout=10)
        if not response.ok:
            logger.error(f"Error getting proxies from Webshare. Status code: {response.status_code}. Response: {response.text}")
            return []

        return response.json()


class MailgunRequester():
    def __init__(self):
        self.base_url = "https://api.mailgun.net/v3"
        self.api_key = settings.MAILGUN_API_KEY

    def send_email(self, to, subject, body):
        data = {
            "from": "Anteon (formerly Ddosify) <support@getanteon.com>",
            "to": to,
            "subject": subject,
            "text": body
        }
        try:
            email_response = requests.post(url="https://api.mailgun.net/v3/mail.getanteon.com/messages",
                                        auth=("api", self.api_key),
                                        data=data)

            if not email_response.ok:
                if email_response.status_code >= 400:
                    raise ThrottlingException(f"Email send error: {email_response.text} - Status Code: {email_response.status_code}")
                raise Exception(f"Email send error: {email_response.text} - Status Code: {email_response.status_code}")

            logger.info(f"Email sent to: {to}. Subject: {subject}")
        except ThrottlingException as e:
            exception_code = "E-101"
            logger.fatal(f"Can not send email. Email: {to}. Subject: {subject} Code: {exception_code}")
            raise
        except Exception as e:
            exception_code = "E-100"
            logger.fatal(f"Can not send email. Email: {to}. Subject: {subject} Code: {exception_code}")

class YouTubeRequester():
    def __init__(self, api_key=None):
        self.base_url = "https://content-youtube.googleapis.com/youtube/v3"
        if not api_key:
            api_key = get_youtube_api_key()
        self.api_key = api_key

    def get_most_popular_video(self):
        """
        Get the most popular video from YouTube
        Returns:
            dict: Response from YouTube API containing video details
        Raises:
            ValueError: If API request fails
        """
        try:
            url = f"{self.base_url}/videos"
            params = {
                "part": "id,snippet,statistics",
                "chart": "mostPopular",
                "maxResults": 1,
                "key": self.api_key
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])[0]
        except Exception as e:
            raise ValueError(f"Failed to get most popular video: {str(e)}")
   
    def fetch_channel(self, username=None, channel_id=None):
        """
        Fetch channel details from YouTube API
        Args:
            username (str, optional): YouTube channel username
            channel_id (str, optional): YouTube channel ID
        Returns:
            dict: Response from YouTube API containing channel details
        Raises:
            ValueError: If neither username nor channel_id is provided or API request fails
        """
        if not username and not channel_id:
            raise ValueError("Either username or channel_id must be provided")
            
        try:
            url = f"{self.base_url}/channels"
            params = {
                "part": "contentDetails,id",
                "key": self.api_key
            }
            
            if username:
                params["forHandle"] = username
            else:
                params["id"] = channel_id
                
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if not data.get("items"):
                raise ValueError(f"Channel not found: {username or channel_id}")
                
            return data
            
        except requests.exceptions.RequestException as e:
            if response.status_code == 403:
                if '"YouTube Data API v3 has not been used in project' in response.text:
                    raise ValueError("YouTube API is not enabled for this project. Please enable it in the project settings.")
                else:
                   raise ValueError("YouTube API quota exceeded or invalid API key")
            else:
                raise ValueError(f"Failed to fetch channel: {str(e)}")
                
    def fetch_all_playlist_videos(self, playlist_id):
        """
        Fetch all videos from a playlist, handling pagination
        Args:
            playlist_id (str): ID of the playlist
        Returns:
            list: List of all video items in the playlist
        """
        videos = []
        next_page_token = None
        
        try:
            while True:
                url = f"{self.base_url}/playlistItems"
                params = {
                    "part": "id,contentDetails,snippet,status",
                    "maxResults": 50,
                    "playlistId": playlist_id,
                    "key": self.api_key
                }
                
                if next_page_token:
                    params["pageToken"] = next_page_token
                    
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                videos.extend(data.get("items", []))
                next_page_token = data.get("nextPageToken")
                
                if not next_page_token:
                    break
                    
            return videos
            
        except requests.exceptions.RequestException as e:
            if response.status_code == 404:
                raise ValueError(f"Playlist not found: {playlist_id}")
            elif response.status_code == 403:
                if '"YouTube Data API v3 has not been used in project' in response.text:
                    raise ValueError("YouTube API is not enabled for this project. Please enable it in the project settings.")
                else:
                   raise ValueError("YouTube API quota exceeded or invalid API key")
            else:
                raise ValueError(f"Failed to fetch playlist videos: {str(e)}")
                
    def fetch_all_channel_videos(self, username=None, channel_id=None):
        """
        Fetch all videos from a channel by first getting the uploads playlist ID
        Args:
            username (str, optional): YouTube channel username
            channel_id (str, optional): YouTube channel ID
        Returns:
            list: List of all video items from the channel
        """
        try:
            # First get the channel details to get the uploads playlist ID
            channel_data = self.fetch_channel(username=username, channel_id=channel_id)
            if not channel_data.get("items"):
                raise ValueError(f"Channel not found: {username or channel_id}")
                
            # Get the uploads playlist ID
            uploads_playlist_id = channel_data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            # Now fetch all videos from the uploads playlist
            return self.fetch_all_playlist_videos(uploads_playlist_id)
            
        except ValueError as e:
            raise ValueError(f"Failed to fetch channel videos: {str(e)}")
        

class OllamaRequester():
    def __init__(self, base_url=None):
        self.base_url = base_url or settings.OLLAMA_URL
        self.headers = {
            'Content-Type': 'application/json'
        }

    def check_ollama_health(self):
        """
        Check if Ollama server is healthy and return available models
        Returns:
            tuple: (is_healthy: bool, models: list, error: str)
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", headers=self.headers, timeout=10)
            if response.status_code != 200:
                return False, [], f"Ollama API returned status code {response.status_code}"
            
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            return True, models, None
            
        except requests.exceptions.RequestException as e:
            return False, [], f"Failed to connect to Ollama server: {str(e)}"
        except Exception as e:
            return False, [], f"Unexpected error checking Ollama health: {str(e)}"

    def validate_models(self, embedding_model, base_model):
        """
        Validate if the specified models exist in Ollama
        Args:
            embedding_model (str): Name of the embedding model to validate
            base_model (str): Name of the base model to validate
        Returns:
            tuple: (is_embedding_valid: bool, is_base_valid: bool, error: str)
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", headers=self.headers, timeout=10)
            if response.status_code != 200:
                return False, False, f"Ollama API returned status code {response.status_code}"
            
            data = response.json()
            available_models = [model['name'] for model in data.get('models', [])]
            
            is_embedding_valid = embedding_model in available_models
            is_base_valid = base_model in available_models
            
            return is_embedding_valid, is_base_valid, None
            
        except requests.exceptions.RequestException as e:
            return False, False, f"Failed to connect to Ollama server: {str(e)}"
        except Exception as e:
            return False, False, f"Unexpected error validating models: {str(e)}"

    def embed_text(self, text, model_name):
        url = f"{self.base_url}/api/embeddings"
        data = json.dumps({"model": model_name, "prompt": text})
        response = requests.post(url, headers=self.headers, data=data, timeout=10)
        if response.status_code != 200:
            logger.error(f"Ollama API text embedding failed. Text: {text}. Model: {model_name}. Status code: {response.status_code}. {response.text}")
            return False, f"Ollama API returned status code {response.status_code}"
        return True, response.json()

    def embed_texts(self, texts, model_name):
        results = []
        for text in texts:
            is_valid, result = self.embed_text(text, model_name)
            if not is_valid:
                return False, f"Ollama API failed to embed text: {text}"
            results.append(result)
        return True, results

class ConfluenceRequester():
    def __init__(self, integration):
        """
        Initialize Confluence Requester with integration credentials
        Args:
            integration (Integration): Integration model instance containing Confluence credentials
        """
        from atlassian import Confluence
        self.domain = integration.confluence_domain
        self.url = f"https://{integration.confluence_domain}"
        self.confluence = Confluence(
            url=self.url,
            username=integration.confluence_user_email,
            password=integration.confluence_api_token
        )

    def _format_space(self, space):
        """
        Format a Confluence space into a dictionary
        Args:
            space (dict): Space data from Confluence API
        Returns:
            dict: Formatted space data
        """
        return {
            'key': space.get('key'),
            'name': space.get('name'),
            'type': space.get('type'),
            'url': f"{self.url}/wiki/spaces/{space.get('key')}"
        }

    def _format_page(self, page, space_key=None, space_name=None):
        """
        Format a Confluence page into a dictionary
        Args:
            page (dict): Page data from Confluence API
            space_key (str, optional): Space key if not included in page data
            space_name (str, optional): Space name if not included in page data
        Returns:
            dict: Formatted page data
        """
        return {
            'id': page.get('id'),
            'title': page.get('title'),
            'type': page.get('type', 'page'),
            'space_key': space_key or page.get('space', {}).get('key'),
            'space_name': space_name or page.get('space', {}).get('name', ''),
            'link': f"{self.url}/wiki{page.get('_links', {}).get('webui', '')}"
        }

    def _format_comment(self, comment):
        """
        Format a Confluence comment into a dictionary
        Args:
            comment (dict): Comment data from Confluence API
        Returns:
            dict: Formatted comment data
        """
        # Try to get content from body.view first (expanded response)
        content = ''
        if comment.get('body') and comment['body'].get('view') and comment['body']['view'].get('value'):
            content = comment['body']['view']['value']
        # Fall back to storage format if view is not available
        elif comment.get('body') and comment['body'].get('storage') and comment['body']['storage'].get('value'):
            content = comment['body']['storage']['value']
        
        # Convert HTML to markdown if content is HTML
        if content and ('<' in content or '&lt;' in content):
            content = html2text.html2text(content)
        
        return {
            'id': comment.get('id'),
            'content': content,
        }
        
    def _format_page_content(self, page, comments=None):
        """
        Format a Confluence page with its content into a dictionary
        Args:
            page (dict): Page data from Confluence API with content
            comments (list, optional): List of comments for the page
        Returns:
            dict: Formatted page data with content
        """
        space = page.get('space', {})
        body = page.get('body', {}).get('storage', {}).get('value', '')
        markdown_body = html2text.html2text(body) if body else ''

        formatted_body = f"<Confluence Page>\n{markdown_body}\n</Confluence Page>\n"
        if comments:
            for comment in comments:
                formatted_body += f"<Confluence Comment>\n{comment['content']}\n</Confluence Comment>"
        
        return {
            'id': page.get('id'),
            'title': page.get('title'),
            'content': formatted_body,
            'space_key': space.get('key'),
            'space_name': space.get('name'),
            'version': page.get('version', {}).get('number'),
            'created_at': page.get('created'),
            'updated_at': page.get('version', {}).get('when'),
            'comments': comments or [],
            'url': f"{self.url}/wiki/spaces/{space.get('key')}/pages/{page.get('id')}"
        }

    def list_pages(self, cql=None, start_time=None, end_time=None):
        """
        List Confluence pages using CQL or list all pages if no CQL is provided.
        This method combines the functionality of listing spaces and pages.
        
        Args:
            cql (str, optional): Confluence Query Language query to filter pages.
                                Examples: 
                                - "type=page AND space=DEV"
                                - "title ~ 'Project'"
                                - "created > '2023-01-01'"
            start_time (str, optional): Start time for filtering pages.
            end_time (str, optional): End time for filtering pages.
        
        Returns:
            dict: Contains 'pages' list
        
        Raises:
            ValueError: If API request fails
        """
        try:
            query = "type=page"
            # If CQL is provided, use it directly to get pages
            if cql:
                query += f" AND ({cql})"  # Enclose to prevent operator reordering
            
            if start_time:
                query += f" AND created >= '{start_time}'"
            if end_time:
                query += f" AND created < '{end_time}'"

            all_pages = []
            seen_page_ids = set()  # Track unique page IDs
            cql_limit = 100  # Fetch 100 results at a time
            
            # Initial request
            url = f"{self.url}/wiki/rest/api/search"
            params = {
                'cql': query,
                'limit': cql_limit,
                'expand': 'space'
            }
            
            while True:
                response = requests.get(
                    url,
                    auth=(self.confluence.username, self.confluence.password),
                    params=params,
                    timeout=30
                )
                
                if response.status_code == 401:
                    raise ValueError("Invalid Confluence credentials")
                elif response.status_code == 403:
                    raise ValueError("Confluence API access forbidden")
                elif response.status_code != 200:
                    if 'could not parse' in response.text.lower():
                        raise ValueError(f"Invalid CQL query.")
                    else:
                        split = response.json().get('message', '').split(':', 1)
                        if len(split) > 1:
                            raise ValueError(split[1].strip())
                        else:
                            raise ValueError(f"Confluence API request failed with status {response.status_code}")
                
                cql_results = response.json()
                results = cql_results.get('results', [])
                
                if not results:
                    break
                    
                for result in results:
                    content = result.get('content', {})
                    page_id = content.get('id')
                    
                    # Skip if we've seen this page ID before
                    if not page_id or page_id in seen_page_ids:
                        continue
                        
                    seen_page_ids.add(page_id)
                    
                    # Get space info from the expanded result
                    space = content.get('space', {})
                    space_key = space.get('key')
                    space_name = space.get('name', '')
                    
                    # Format and add the page
                    formatted_page = self._format_page(content, space_key, space_name)
                    all_pages.append(formatted_page)
                
                # Check if there's a next page
                next_link = cql_results.get('_links', {}).get('next')
                if not next_link:
                    break
                    
                # Update URL and params for next request
                url = f"{self.url}/wiki{next_link}"
                params = {}  # Clear params as they're included in the next_link
            
            return {
                'pages': all_pages,
                'page_count': len(all_pages)
            }
                
        except Exception as e:
            if "401" in str(e):
                raise ValueError("Invalid Confluence credentials")
            elif "403" in str(e):
                raise ValueError("Confluence API access forbidden")
            else:
                raise ValueError(str(e))

    def get_page_content(self, page_id, include_comments=True):
        """
        Get content of a specific Confluence page
        Args:
            page_id (str): ID of the Confluence page
            include_comments (bool): Whether to include comments
        Returns:
            dict: Page details with content
        Raises:
            ValueError: If API request fails
        """
        try:
            # Get page and its content 
            page = self.confluence.get_page_by_id(page_id, expand='body.storage,version,space')
            
            # Get comments if requested
            comments = []
            if include_comments:
                try:
                    comments_data = self.get_page_comments(page_id)
                    comments = comments_data.get('comments', [])
                except Exception:
                    # Continue even if comments can't be fetched
                    pass
            
            return self._format_page_content(page, comments)
            
        except Exception as e:
            if "401" in str(e):
                raise ValueError("Invalid Confluence credentials")
            elif "403" in str(e):
                raise ValueError("Confluence API access forbidden")
            elif "404" in str(e):
                raise ValueError(f"Confluence page {page_id} not found")
            else:
                raise ValueError(f"Error getting Confluence page: {str(e)}")

    def get_page_comments(self, page_id, start=0, limit=50):
        """
        Get comments for a specific Confluence page with pagination
        Args:
            page_id (str): ID of the Confluence page
            start (int): Starting index for pagination
            limit (int): Maximum number of results to fetch per request
        Returns:
            dict: Contains comments list with pagination details
        Raises:
            ValueError: If API request fails
        """
        try:
            # Get all comments with proper pagination
            all_comments = []
            
            # Use pagination to get all comments
            page_start = 0
            page_limit = 100  # Fetch 100 comments at a time
            while True:
                try:
                    # The Confluence API doesn't support direct pagination for comments
                    # So we fetch all comments and then paginate in memory
                    # Expand body.view to get the comment content
                    comments_data = self.confluence.get_page_comments(
                        page_id, 
                        expand='body.view,version',
                        start=page_start,
                        limit=page_limit
                    )
                    results = comments_data.get('results', [])
                    
                    if not results:
                        break
                        
                    for comment in results:
                        formatted_comment = self._format_comment(comment)
                        all_comments.append(formatted_comment)
                        
                    # If we got fewer comments than requested, we've reached the end
                    if len(results) < page_limit:
                        break
                        
                    # Move to the next page
                    page_start += page_limit
                    
                except Exception as e:
                    logger.warning(f"Error fetching comments for page {page_id}: {str(e)}")
                    break
            
            # Apply pagination for the response
            total_size = len(all_comments)
            end_index = min(start + limit, total_size)
            paginated_comments = all_comments[start:end_index] if start < total_size else []
            
            return {
                'comments': paginated_comments,
                'size': total_size,
                'start': start,
                'limit': limit
            }
                
        except Exception as e:
            if "401" in str(e):
                raise ValueError("Invalid Confluence credentials")
            elif "403" in str(e):
                raise ValueError("Confluence API access forbidden")
            elif "404" in str(e):
                raise ValueError(f"Confluence page {page_id} not found")
            else:
                raise ValueError(f"Error getting Confluence page comments: {str(e)}")

    def list_spaces(self, start=0, limit=50):
        """
        List all Confluence spaces with pagination
        
        Args:
            start (int): Starting index for pagination
            limit (int): Maximum number of results to fetch per request
        
        Returns:
            dict: Contains spaces list with pagination details
        
        Raises:
            ValueError: If API request fails
        """
        try:
            # Get all spaces with proper pagination
            all_spaces = []
            
            # Use pagination to get all spaces
            space_start = 0
            space_limit = 25  # Fetch 25 spaces at a time
            while True:
                spaces_data = self.confluence.get_all_spaces(start=space_start, limit=space_limit)
                results = spaces_data.get('results', [])
                
                if not results:
                    break
                    
                for space in results:
                    formatted_space = self._format_space(space)
                    all_spaces.append(formatted_space)
                    
                # If we got fewer spaces than requested, we've reached the end
                if len(results) < space_limit:
                    break
                    
                # Move to the next page
                space_start += space_limit
            
            # Apply pagination for the response
            total_size = len(all_spaces)
            end_index = min(start + limit, total_size)
            paginated_spaces = all_spaces[start:end_index] if start < total_size else []
            
            return {
                'spaces': paginated_spaces,
                'size': total_size,
                'start': start,
                'limit': limit
            }
                
        except Exception as e:
            if "401" in str(e):
                raise ValueError("Invalid Confluence credentials")
            elif "403" in str(e):
                raise ValueError("Confluence API access forbidden")
            else:
                raise ValueError(f"Error listing Confluence spaces: {str(e)}")

    def get_space_with_homepage(self, space_key):
        """
        Get space details including homepage information
        
        Args:
            space_key (str): Key of the Confluence space
            
        Returns:
            dict: Space details with homepage information
            
        Raises:
            ValueError: If API request fails
        """
        try:
            # Get space details with homepage expanded
            space = self.confluence.get_space(space_key, expand='homepage')
            
            # Format space details
            space_data = {
                'key': space.get('key'),
                'name': space.get('name'),
                'type': space.get('type'),
                'homepage': space.get('homepage')
            }
            
            # Add URL to space
            space_data['url'] = f"{self.url}/wiki/spaces/{space_data['key']}"
            
            return space_data
                
        except Exception as e:
            if "401" in str(e):
                raise ValueError("Invalid Confluence credentials")
            elif "403" in str(e):
                raise ValueError("Confluence API access forbidden")
            elif "404" in str(e):
                raise ValueError(f"Confluence space '{space_key}' not found")
            else:
                raise ValueError(str(e))
