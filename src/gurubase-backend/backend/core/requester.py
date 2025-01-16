import json
import time
import logging
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from typing import List
from django.conf import settings
from openai import OpenAI
import requests
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

from core.models import GuruType
from core.guru_types import get_guru_type_prompt_map
genai.configure(api_key=settings.GEMINI_API_KEY)


GURU_ENDPOINTS = {
    'processed_raw_questions': 'processed_raw_questions'
}

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
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def get_context_relevance(self, question_text, user_question, guru_type_slug, contexts, model_name=settings.GPT_MODEL, cot=True):
        from core.utils import get_tokens_from_openai_response, prepare_contexts_for_context_relevance, prepare_prompt_for_context_relevance

        guru_variables = get_guru_type_prompt_map(guru_type_slug)
        prompt = prepare_prompt_for_context_relevance(cot, guru_variables)

        formatted_contexts = prepare_contexts_for_context_relevance(contexts)
        single_text_contexts = ''.join(formatted_contexts)
        user_prompt = f"QUESTION: {question_text}\n\nUSER QUESTION: {user_question}\n\nCONTEXTS\n{single_text_contexts}"

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
        response = self.client.embeddings.create(input=texts, model=model_name)
        embeddings = []
        for embedding in response.data:
            embeddings.append(embedding.embedding)
        return embeddings

    def embed_text(self, text, model_name=settings.OPENAI_TEXT_EMBEDDING_MODEL):
        response = self.client.embeddings.create(input=[text], model=model_name)
        return response.data[0].embedding

    def summarize_text(self, text, guru_type, model_name=settings.GPT_MODEL):
        from .prompts import summarize_data_sources_prompt
        from core.utils import get_llm_usage_from_response
        prompt_map = get_guru_type_prompt_map(guru_type.slug)
        prompt = summarize_data_sources_prompt.format(**prompt_map, content=text)
        try:
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
            questions: list, 
            last_content: str, 
            guru_type: GuruType, 
            contexts: list, 
            model_name: str = settings.GPT_MODEL):
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
        prompt = generate_follow_up_questions_prompt.format(
            guru_type=guru_type.name,
            domain_knowledge=prompt_map['domain_knowledge'],
            questions=json.dumps(questions, indent=2),
            answer=last_content,
            contexts=json.dumps(contexts, indent=2),
            num_questions=settings.FOLLOW_UP_EXAMPLE_COUNT
        )
        
        try:
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
