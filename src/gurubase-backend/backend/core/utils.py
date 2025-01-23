from enum import Enum
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from urllib.parse import urlparse
import re
from datetime import UTC, datetime, timedelta
import functools
import html
import logging
import os
import time
import traceback
import uuid
from django.db.models.functions import Lower
from openai import OpenAI
from django.conf import settings
import requests
from core.milvus_utils import search_for_closest
from core.guru_types import get_guru_type_object, get_guru_type_prompt_map, get_guru_type_names
from core import exceptions
from pymilvus import MilvusClient
from core.models import GithubFile, GuruType, Question, OutOfContextQuestion, Summarization, Settings, SummaryQuestionGeneration
import json
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from core.models import Favicon
from pydantic import BaseModel
import jwt
from colorthief import ColorThief
from io import BytesIO
from slugify import slugify
from core.requester import GeminiRequester, OpenAIRequester, CloudflareRequester 
from PIL import Image
from core.models import DataSource, Binge
from accounts.models import User
from dataclasses import dataclass
from typing import Optional, Generator, Union, Dict
from django.db.models import Model, Q
from django.core.cache import caches
import hashlib
import pickle

logger = logging.getLogger(__name__)

cloudflare_requester = CloudflareRequester()
chatgpt_client = OpenAI(api_key=settings.OPENAI_API_KEY)
openai_requester = OpenAIRequester()

def stream_and_save(
        user_question, 
        question, 
        guru_type, 
        question_slug, 
        description, 
        response, 
        prompt, 
        links, 
        summary_completion_tokens, 
        summary_prompt_tokens, 
        summary_cached_tokens, 
        context_vals, 
        context_distances, 
        times, 
        reranked_scores, 
        trust_score, 
        processed_ctx_relevances, 
        ctx_rel_usage,
        user=None,
        parent=None, 
        binge=None, 
        source=Question.Source.USER.value):
    stream_start = time.time()
    total_response = []
    chunks = []
    latency_start = time.time()
    for chunk in response:
        chunks.append(chunk)
        try:
            if len(chunk.choices) == 0:
                # Last chunk
                yield ''
            else:
                data = chunk.choices[0].delta.content
                if data is None:
                    continue
                total_response.append(data)
                yield data
        except Exception as e:
            logger.error(f'Error while streaming the response: {e}', exc_info=True)
            break
        
    latency_sec = time.time() - latency_start
    stream_time = time.time() - stream_start

    cost_start = time.time()
    prompt_tokens, completion_tokens, cached_prompt_tokens = get_tokens_from_openai_response(chunk)

    cost_dollars = get_llm_usage(settings.GPT_MODEL, prompt_tokens, completion_tokens, cached_prompt_tokens)
    cost_time = time.time() - cost_start
    
    guru_type_object = get_guru_type_object(guru_type)

    question_save_start = time.time()
    answer = ''.join(total_response)

    llm_usages = {}
    llm_usages['summary'] = {
        'prompt_tokens': summary_prompt_tokens,
        'completion_tokens': summary_completion_tokens,
        'cached_prompt_tokens': summary_cached_tokens,
        'cost_dollars': get_llm_usage(settings.GPT_MODEL, summary_prompt_tokens, summary_completion_tokens, summary_cached_tokens),
        'model': settings.GPT_MODEL
    }

    prompt_tokens, completion_tokens, cached_prompt_tokens = get_tokens_from_openai_response(chunk)
    llm_usages['answer'] = {
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion_tokens,
        'cached_prompt_tokens': cached_prompt_tokens,
        'cost_dollars': get_llm_usage(settings.GPT_MODEL, prompt_tokens, completion_tokens, cached_prompt_tokens),
        'model': settings.GPT_MODEL
    }

    llm_usages['context_relevance'] = ctx_rel_usage

    existing_question = Question.objects.filter(
        slug=question_slug,
        guru_type=guru_type_object,
        binge=binge
    ).first()

    try:
        if existing_question:
            question_obj = existing_question
            question_obj.question = question
            question_obj.user_question = user_question
            question_obj.content = answer
            question_obj.description = description
            question_obj.change_count += 1
            question_obj.completion_tokens = completion_tokens
            question_obj.prompt_tokens = prompt_tokens
            question_obj.cached_prompt_tokens = cached_prompt_tokens
            question_obj.cost_dollars = cost_dollars
            question_obj.latency_sec = latency_sec
            question_obj.source = source,
            question_obj.prompt = prompt
            question_obj.references = links
            question_obj.context_distances = context_distances
            question_obj.reranked_scores = reranked_scores
            question_obj.trust_score = trust_score
            question_obj.parent = parent
            question_obj.binge = binge
            question_obj.llm_usages = llm_usages
            question_obj.processed_ctx_relevances = processed_ctx_relevances
            question_obj.user = user
            question_obj.save()
            cloudflare_requester.purge_cache(guru_type, question_slug)
            
        else:
            question_obj = Question(
                slug=question_slug,
                question=question,
                user_question=user_question,
                content=answer,
                description=description,
                guru_type=guru_type_object,
                completion_tokens=completion_tokens,
                prompt_tokens=prompt_tokens,
                cached_prompt_tokens=cached_prompt_tokens,
                cost_dollars=cost_dollars,
                latency_sec=latency_sec,
                source=source,
                prompt=prompt,
                references=links,
                context_distances=context_distances,
                reranked_scores=reranked_scores,
                trust_score=trust_score,
                parent=parent,
                binge=binge,
                user=user,
                processed_ctx_relevances=processed_ctx_relevances,
                llm_usages=llm_usages
            )
            question_obj.save()
    except Exception as e:
        logger.error(f'Error while saving question after stream. Arguments are: \nQuestion: {question}\nUser question: {user_question}\nSlug: {question_slug}\nGuru Type: {guru_type_object}\nBinge: {binge}', exc_info=True)
        raise e

    question_save_time = time.time() - question_save_start

    if binge:
        binge.save() # To update the last used field

    endpoint_time = time.time() - times['endpoint_start']

    times['stream_time'] = stream_time
    times['cost_time'] = cost_time
    times['question_save_time'] = question_save_time
    times['endpoint_time'] = endpoint_time

    del times['endpoint_start']

    if settings.LOG_STREAM_TIMES:
        logger.info(f'Times: {times}')

class LLM_MODEL:
    OPENAI = 'openai'
    GEMINI = 'gemini'


def prepare_contexts(contexts, reranked_scores):
    references = {}
    formatted_contexts = []
    
    # Find the PDF files that need to be masked
    pdf_links = []
    for context in contexts:
        if ('entity' in context and 
            'metadata' in context['entity'] and 
            'type' in context['entity']['metadata'] and 
            context['entity']['metadata']['type'] == 'PDF' and 
            'link' in context['entity']['metadata']):
            pdf_links.append(context['entity']['metadata']['link'])
    
    private_pdf_links = set()
    if pdf_links:
        from core.models import DataSource
        private_pdf_links = set(DataSource.objects.filter(url__in=pdf_links, private=True).values_list('url', flat=True))

    for context_num, context in enumerate(contexts, start=1):
        if isinstance(context, dict) and 'question' in context and 'accepted_answer' in context:
            # StackOverflow context with accepted answer
            context_parts = [f"<{context['prefix']} context>\n", f"Context {context_num}:"]
            
            question = context['question']
            metadata = {
                'type': 'stackoverflow',
                'score': question['entity']['metadata']['score'],
                'owner_badges': question['entity']['metadata']['owner_badges'],
                'owner_reputation': question['entity']['metadata']['owner_reputation'],
                'question': question['entity']['metadata']['question'],
                'link': question['entity']['metadata']['link']
            }
            context_parts.extend([
                f"Metadata: '''{metadata}'''",
                f"Question: '''{question['entity']['text']}'''"
            ])
            
            reference_key = question['entity']['metadata']['question']
            reference_link = question['entity']['metadata']['link']
            
            context_parts.append(f"Accepted answer: '''{context['accepted_answer']['entity']['text']}'''")

            # Sort other answers by score (assuming score is in metadata)
            sorted_answers = sorted(context.get('other_answers', []), 
                                    key=lambda x: x['entity']['metadata'].get('score', 0), 
                                    reverse=True)
            
            for i, answer in enumerate(sorted_answers, start=1):
                context_parts.append(f"Answer {i} with higher score: '''{answer['entity']['text']}'''")

            context_parts.append(f'</{context["prefix"]} context>')
            
            formatted_contexts.append('\n'.join(context_parts))
            
            references[reference_key] = {
                'question': reference_key,
                'link': reference_link
            }
        elif 'type' in context['entity']['metadata'] and context['entity']['metadata']['type'] in ['WEBSITE', 'PDF', 'YOUTUBE']:
            # Data Sources except Github Repo (unchanged)
            metadata = {
                'type': context['entity']['metadata']['type'],
                'title': context['entity']['metadata']['title'],
                'link': context['entity']['metadata']['link']
            }
            
            # Remove link from metadata if it's a private PDF
            if metadata['type'] == 'PDF' and metadata['link'] in private_pdf_links:
                metadata['link'] = None

            context_parts = [
                f"<{context['prefix']} context>\n",
                f"Context {context_num}:",
                f"Metadata: '''{metadata}'''",
                f"Text: '''{context['entity']['text']}'''"
                f"</{context['prefix']} context>"
            ]
            
            formatted_contexts.append('\n'.join(context_parts))

            references[context['entity']['metadata']['title']] = {
                'question': context['entity']['metadata']['title'],
                'link': context['entity']['metadata']['link']
            }
        elif 'type' in context['entity']['metadata'] and context['entity']['metadata']['type'] == 'GITHUB_REPO':
            metadata = {
                'type': context['entity']['metadata']['type'],
                'title': context['entity']['metadata']['title'],
                'link': context['entity']['metadata']['link']
            }

            context_parts = [
                f"<{context['prefix']} context>\n",
                f"Context {context_num}:",
                f"Metadata: '''{metadata}'''",
                f"Text: '''{context['entity']['text']}'''"
                f"</{context['prefix']} context>"
            ]
            
            formatted_contexts.append('\n'.join(context_parts))

            references[context['entity']['metadata']['title']] = {
                'question': context['entity']['metadata']['title'],
                'link': context['entity']['metadata']['link']
            }
        else:
            # YC essays or videos (unchanged)
            metadata = {
                'title': context['entity']['metadata']['title'],
                'author': context['entity']['metadata']['author'],
            }
            if 'type' in context['entity']['metadata']:
                # Essay
                metadata['type'] = context['entity']['metadata']['type']
                link = context['entity']['metadata']['url']
                metadata['link'] = link
            else:
                # YC videos
                metadata['view_count'] = context['entity']['metadata']['view_count']
                link = f'https://www.youtube.com/watch?v={context["entity"]["metadata"]["source"]}'
                metadata['link'] = link
            
            context_parts = [
                f"<{context['prefix']} context>\n",
                f"Context {context_num}:",
                f"Metadata: '''{metadata}'''",
                f"Text: '''{context['entity']['text']}'''"
                f"</{context['prefix']} context>"
            ]
            
            formatted_contexts.append('\n'.join(context_parts))

            references[context['entity']['metadata']['title']] = {
                'question': context['entity']['metadata']['title'],
                'link': link
            }

    formatted_contexts = '\n\n'.join(formatted_contexts)
    
    # Get unique references
    references = list(references.values())

    # Sort by reranked_scores using the link
    # Example reranked_scores: [{"link": "https://stackoverflow.com/q/78838212", "score": 0.061199225}, {"link": "https://stackoverflow.com/q/79005130", "score": 0.05014425}, ...
    # Example references: [{"link": "https://stackoverflow.com/q/78838212", "question": "Upgrade mysql version 5.7 to 8.0 in Docker. Error mysql auto restarting after upgrade"}, ...
    references = sorted(references, key=lambda x: next((item['score'] for item in reranked_scores if item['link'] == x['link']), 0), reverse=True)
    
    return {'contexts': formatted_contexts}, references


def get_milvus_client():
    try:
        milvus_client = MilvusClient(
            uri = f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}"
        )
    except Exception as e:
        logger.error(f'Error while connecting to Milvus: {e}', exc_info=True)
        milvus_client = None

    return milvus_client


def vector_db_fetch(milvus_client, collection_name, question, guru_type_slug, user_question, llm_eval=False):
    embedding = embed_text(question)
    embedding_user_question = embed_text(user_question)
    # logger.info(f'Embedding dimensions: {len(embedding)}')
    all_docs = {}
    search_params = None

    def merge_splits(fetched_doc, collection_name, link_key, link, merge_limit=None):
        # Merge fetched doc with its other splits
        merged_text = {}
        # Fetching all splits once as they are already limited by stackoverflow itself and pymilvus does not support ordering
        if merge_limit:
            results = milvus_client.search(
                collection_name=collection_name, 
                data=[embedding], 
                limit=merge_limit, 
                output_fields=['text', 'metadata'], 
                filter=f'metadata["{link_key}"] == "{link}"'
            )[0]
        else:
            results = milvus_client.search(
                collection_name=collection_name, 
                data=[embedding], 
                limit=16384,
                output_fields=['text', 'metadata'], 
                filter=f'metadata["{link_key}"] == "{link}"'
            )[0]
        
        for backup_num, result in enumerate(results):
            split_num = result['entity']['metadata']['split_num'] if 'split_num' in result['entity']['metadata'] else backup_num
            merged_text[split_num] = result['entity']['text']

        # Merge them in order
        fetched_doc['entity']['text'] = ' '.join([merged_text[key] for key in sorted(merged_text.keys())])
        return fetched_doc

    def fetch_and_merge_answers(question_id):
        # First, fetch only the first split of each answer
        answer_first_splits = milvus_client.search(
            collection_name=collection_name,
            data=[embedding],
            limit=16384,
            output_fields=['text', 'metadata'],
            filter=f'metadata["question_id"] == {question_id} and metadata["type"] == "answer" and metadata["split_num"] == 1'
        )[0]
        
        merged_answers = []
        for answer_first_split in answer_first_splits:
            link = answer_first_split['entity']['metadata']['link']
            merged_answer = merge_splits(answer_first_split, collection_name, 'link', link)
            merged_answers.append(merged_answer)
        
        return merged_answers

    def rerank_batch(batch, question, llm_eval):
        if settings.ENV == 'selfhosted':
            # Do not rerank in selfhosted
            return [i for i in range(len(batch))], [1 for _ in range(len(batch))]
        batch_texts = [result['entity']['text'] for result in batch]
        reranked_batch = rerank_texts(question, batch_texts)
        # reranked_batch: [{"index": 3, "score": 0.91432924}, {"index": 0, "score": 0.51251252}, {"index": 9, "score": 0.3}]

        if reranked_batch is None:
            logger.warning(f'Reranking failed for the batch: {[text[:100] for text in batch_texts]}. Using original order.')
            reranked_batch_indices = [i for i in range(len(batch_texts))]
            reranked_batch_scores = [0 for _ in range(len(batch_texts))]
        else:
            reranked_batch_indices = [result['index'] for result in reranked_batch]
            reranked_batch_scores = [result['score'] for result in reranked_batch]

        # Apply Rerank Threshold
        default_settings = get_default_settings()
        threshold = default_settings.rerank_threshold if not llm_eval else default_settings.rerank_threshold_llm_eval
        filtered_indices = [index for index, score in zip(reranked_batch_indices, reranked_batch_scores) if score > threshold]
        filtered_scores = [score for score in reranked_batch_scores if score > threshold]

        return filtered_indices, filtered_scores

    def fetch_stackoverflow_sources():
        stackoverflow_sources = {}
        reranked_scores = []
        if settings.ENV == 'selfhosted':
            return [], []
        batch = milvus_client.search(
            collection_name=collection_name,
            data=[embedding],
            limit=20,
            output_fields=['id', 'text', 'metadata'],
            filter='metadata["type"] in ["question", "answer"]',
            search_params=search_params
        )[0]

        if not batch:
            return [], []

        user_question_batch = milvus_client.search(
            collection_name=collection_name,
            data=[embedding_user_question],
            limit=10,
            output_fields=['id', 'text', 'metadata'],
            filter='metadata["type"] in ["question", "answer"]',
            search_params=search_params
        )[0]

        final_user_question_docs_without_duplicates = []
        for doc in user_question_batch:
            if doc["id"] not in [doc["id"] for doc in batch]:
                final_user_question_docs_without_duplicates.append(doc)

        batch = batch + final_user_question_docs_without_duplicates

        reranked_batch_indices, reranked_batch_scores = rerank_batch(batch, question, llm_eval)

        for index, score in zip(reranked_batch_indices, reranked_batch_scores):
            if len(stackoverflow_sources) >= 3:
                break
            
            try:
                question_title = batch[index]['entity']['metadata']['question']
                question_id = batch[index]['entity']['metadata']['question_id']
                if question_title not in stackoverflow_sources:
                    # Try to fetch the question
                    milvus_question = milvus_client.search(
                        collection_name=collection_name,
                        data=[embedding],
                        limit=1,
                        output_fields=['text', 'metadata'],
                        filter=f'metadata["question_id"] == {question_id} and metadata["type"] == "question"'
                    )[0]
                    
                    # Try to fetch the accepted answer
                    accepted_answer = milvus_client.search(
                        collection_name=collection_name,
                        data=[embedding],
                        limit=1,
                        output_fields=['text', 'metadata'],
                        filter=f'metadata["question_id"] == {question_id} and metadata["type"] == "answer" and metadata["is_accepted"] == True'
                    )[0]

                    if not accepted_answer:
                        # If accepted answer is not found with is_accepted key, try with accepted key for old collections. is_accepted is the new key.
                        accepted_answer = milvus_client.search(
                            collection_name=collection_name,
                            data=[embedding],
                            limit=1,
                            output_fields=['text', 'metadata'],
                            filter=f'metadata["question_id"] == {question_id} and metadata["type"] == "answer" and metadata["accepted"] == True'
                        )[0]
                    
                    # Only proceed if both question and accepted answer are found
                    if milvus_question and accepted_answer:
                        question_link = milvus_question[0]['entity']['metadata']['link']
                        accepted_answer_link = accepted_answer[0]['entity']['metadata']['link']
                        stackoverflow_sources[question_title] = {
                            "question": merge_splits(milvus_question[0], collection_name, 'link', question_link),
                            "accepted_answer": merge_splits(accepted_answer[0], collection_name, 'link', accepted_answer_link),
                            "other_answers": []
                        }
                        
                        # Fetch other answers
                        other_answers = fetch_and_merge_answers(question_id)
                        stackoverflow_sources[question_title]["other_answers"] = [
                            answer for answer in other_answers 
                            if answer['entity']['metadata']['link'] != accepted_answer_link
                        ]
                        reranked_scores.append({'link': question_link, 'score': score})
                    else:
                        logger.warning(f'Question found: {milvus_question[0]["id"] if milvus_question else None}, accepted answer found: {accepted_answer[0]["id"] if accepted_answer else None}')
                    
            except Exception as e:
                logger.error(f'Error while fetching stackoverflow sources: {e}', exc_info=True)
        
        return list(stackoverflow_sources.values()), reranked_scores

    def fetch_non_stackoverflow_sources():
        non_stackoverflow_sources = []
        reranked_scores = []
        question_milvus_limit = 20
        user_question_milvus_limit = 10
        if settings.ENV == 'selfhosted':
            question_milvus_limit = 3
            user_question_milvus_limit = 3
        batch = milvus_client.search(
            collection_name=collection_name,
            data=[embedding],
            limit=question_milvus_limit,
            output_fields=['id', 'text', 'metadata'],
            filter='metadata["type"] not in ["question", "answer", "comment"]',
            search_params=search_params
        )[0]
        if not batch:
            return [], []

        user_question_batch = milvus_client.search(
            collection_name=collection_name,
            data=[embedding_user_question],
            limit=user_question_milvus_limit,
            output_fields=['id', 'text', 'metadata'],
            filter='metadata["type"] not in ["question", "answer", "comment"]',
            search_params=search_params
        )[0]

        final_user_question_docs_without_duplicates = []
        for doc in user_question_batch:
            if doc["id"] not in [doc["id"] for doc in batch]:
                final_user_question_docs_without_duplicates.append(doc)

        batch = batch + final_user_question_docs_without_duplicates

        reranked_batch_indices, reranked_batch_scores = rerank_batch(batch, question, llm_eval)

        for index, score in zip(reranked_batch_indices, reranked_batch_scores):
            if len(non_stackoverflow_sources) >= 3:
                break
            
            try:
                link = batch[index]['entity']['metadata'].get('link') or batch[index]['entity']['metadata'].get('url')
                if link and link not in [doc['entity']['metadata'].get('link') or doc['entity']['metadata'].get('url') for doc in non_stackoverflow_sources]:
                    merged_doc = merge_splits(batch[index], collection_name, 'link' if 'link' in batch[index]['entity']['metadata'] else 'url', link, merge_limit=5)
                    non_stackoverflow_sources.append(merged_doc)
                    reranked_scores.append({'link': link, 'score': score})
            except Exception as e:
                logger.error(f'Error while fetching non stackoverflow sources: {e}', exc_info=True)
        
        return non_stackoverflow_sources, reranked_scores

    def fetch_github_repo_sources():
        github_repo_sources = []
        reranked_scores = []
        question_milvus_limit = 20
        user_question_milvus_limit = 10
        if settings.ENV == 'selfhosted':
            question_milvus_limit = 3
            user_question_milvus_limit = 3
        batch = milvus_client.search(
            collection_name=settings.GITHUB_REPO_CODE_COLLECTION_NAME,
            data=[embedding],
            limit=question_milvus_limit,
            output_fields=['id', 'text', 'metadata'],
            filter=f'guru_slug == "{guru_type_slug}"',
            search_params=search_params
        )[0]
        if not batch:
            return [], []

        user_question_batch = milvus_client.search(
            collection_name=settings.GITHUB_REPO_CODE_COLLECTION_NAME,
            data=[embedding_user_question],
            limit=user_question_milvus_limit,
            output_fields=['id', 'text', 'metadata'],
            filter=f'guru_slug == "{guru_type_slug}"',
            search_params=search_params
        )[0]

        final_user_question_docs_without_duplicates = []
        for doc in user_question_batch:
            if doc["id"] not in [doc["id"] for doc in batch]:
                final_user_question_docs_without_duplicates.append(doc)

        batch = batch + final_user_question_docs_without_duplicates

        reranked_batch_indices, reranked_batch_scores = rerank_batch(batch, question, llm_eval)

        for index, score in zip(reranked_batch_indices, reranked_batch_scores):
            if len(github_repo_sources) >= 2:
                break
            
            try:
                link = batch[index]['entity']['metadata'].get('link') or batch[index]['entity']['metadata'].get('url')
                if link and link not in [doc['entity']['metadata'].get('link') or doc['entity']['metadata'].get('url') for doc in github_repo_sources]:
                    merged_doc = merge_splits(batch[index], settings.GITHUB_REPO_CODE_COLLECTION_NAME, 'link', link, merge_limit=5)
                    github_repo_sources.append(merged_doc)
                    reranked_scores.append({'link': link, 'score': score})
            except Exception as e:
                logger.error(f'Error while fetching non stackoverflow sources: {e}', exc_info=True)
        
        return github_repo_sources, reranked_scores        

    def filter_by_trust_score(contexts, reranked_scores, question, user_question, guru_type_slug):
        context_relevance, ctx_rel_usage, prompt, user_prompt = openai_requester.get_context_relevance(question, user_question, guru_type_slug, contexts, cot=False)
        ctx_rel_usage['cost_dollars'] = get_llm_usage(settings.GPT_MODEL, ctx_rel_usage['prompt_tokens'], ctx_rel_usage['completion_tokens'], ctx_rel_usage['cached_prompt_tokens'])
        filtered_contexts = []
        filtered_reranked_scores = []
        trust_score = 0

        default_settings = get_default_settings()

        processed_ctx_relevances = {
            'removed': [],
            'kept': []
        }

        formatted_contexts = prepare_contexts_for_context_relevance(contexts)

        for i, ctx in enumerate(context_relevance['contexts']):
            ctx['context'] = formatted_contexts[i]
            if ctx['score'] >= default_settings.trust_score_threshold:
                filtered_contexts.append(contexts[i])
                filtered_reranked_scores.append(reranked_scores[i])
                trust_score += ctx['score']
                processed_ctx_relevances['kept'].append(ctx)
            else:
                processed_ctx_relevances['removed'].append(ctx)

        return filtered_contexts, filtered_reranked_scores, (trust_score / len(filtered_contexts)) if filtered_contexts else 0, processed_ctx_relevances, ctx_rel_usage

    try:
        reranked_scores = []
        try:
            stackoverflow_sources, stackoverflow_reranked_scores = fetch_stackoverflow_sources()
            for source in stackoverflow_sources:
                source['prefix'] = 'Text'
        except Exception as e:
            logger.error(f'Error while fetching stackoverflow sources: {e}', exc_info=True)
            stackoverflow_sources = []
            stackoverflow_reranked_scores = []
        try:
            non_stackoverflow_sources, non_stackoverflow_reranked_scores = fetch_non_stackoverflow_sources()
            for source in non_stackoverflow_sources:
                source['prefix'] = 'Text'
        except Exception as e:
            logger.error(f'Error while fetching non stackoverflow sources: {e}', exc_info=True)
            non_stackoverflow_sources = []
            non_stackoverflow_reranked_scores = []
        try:
            github_repo_sources, github_repo_reranked_scores = fetch_github_repo_sources()
            for source in github_repo_sources:
                source['prefix'] = 'Code'
        except Exception as e:
            logger.error(f'Error while fetching github repo sources: {e}', exc_info=True)
            github_repo_sources = []
            github_repo_reranked_scores = []
        reranked_scores = stackoverflow_reranked_scores + non_stackoverflow_reranked_scores + github_repo_reranked_scores
        contexts = stackoverflow_sources + non_stackoverflow_sources + github_repo_sources
    except Exception as e:
        logger.info(f'Vector db fetch failed for question: {question}. Error: {e}', exc_info=True)
        contexts = []
        reranked_scores = []

    # Contexts and rerankes_scores are in the same order (Same index corresponds to the same context)
    filtered_contexts, filtered_reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage = filter_by_trust_score(contexts, reranked_scores, question, user_question, guru_type_slug)
    
    return filtered_contexts, filtered_reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage


def get_contexts(milvus_client, collection_name, question, guru_type_slug, user_question):
    try:
        contexts, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage = vector_db_fetch(milvus_client, collection_name, question, guru_type_slug, user_question)
    except Exception as e:
        logger.error(f'Error while fetching the context from the vector database: {e}', exc_info=True)
        contexts = []
        reranked_scores = []

    # if contexts == [] and settings.ENV == 'production':
    #     raise exceptions.InvalidRequestError({'msg': 'No context found for the question.'})

    logger.debug(f'Contexts: {contexts}')
    context_vals, links = prepare_contexts(contexts, reranked_scores)
    context_distances = []
    for ctx in contexts:
        if 'question' in ctx and ctx['question']:
            # Stackoverflow context
            context_distances.append({'context_id': ctx['question']['id'],'distance': ctx['question']['distance']})
            if 'accepted_answer' in ctx and ctx['accepted_answer']:
                context_distances.append({'context_id': ctx['accepted_answer']['id'],'distance': ctx['accepted_answer']['distance']})
            for answer in ctx['other_answers']:
                context_distances.append({'context_id': answer['id'],'distance': answer['distance']})
        else:
            # Non stackoverflow context
            context_distances.append({'context_id': ctx['id'],'distance': ctx['distance']})

    return context_vals, links, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage

    
def parse_summary_response(question, response):
    try:
        prompt_tokens, completion_tokens, cached_prompt_tokens = get_tokens_from_openai_response(response)
        if response.choices[0].message.refusal:
            answer = GptSummary(question=question, user_question=question, question_slug='', answer="An error occurred while processing the question. Please try again.", description="", valid_question=False)
            logger.error(f'Gpt refused to answer for summary. Refusal: {response.choices[0].message.refusal}')
            return {
                'question': question,
                'user_question': question,
                'question_slug': '',
                'description': '',
                'valid_question': False,
                'completion_tokens': completion_tokens,
                'prompt_tokens': prompt_tokens,
                'cached_prompt_tokens': cached_prompt_tokens,
            }
        else:
            gptSummary =  response.choices[0].message.parsed
    except Exception as e:
        logger.error(f'Error while getting the answer from the response: {e}. Response: {response.choices[0].message.parsed}', exc_info=True)
        answer = {
            'question': question,
            'user_question': question,
            'question_slug': '',
            'description': '',
            'valid_question': False,
            'completion_tokens': completion_tokens,
            'prompt_tokens': prompt_tokens,
            'cached_prompt_tokens': cached_prompt_tokens,
        }
        return answer

    slug = validate_slug(gptSummary.question_slug)
    
    return {
        'question': gptSummary.question,
        'user_question': question,
        'question_slug': slug,
        'description': gptSummary.description,
        'valid_question': gptSummary.valid_question,
        'completion_tokens': completion_tokens,
        'prompt_tokens': prompt_tokens,
        'cached_prompt_tokens': cached_prompt_tokens,
        'user_intent': gptSummary.user_intent,
        'answer_length': gptSummary.answer_length,
        "jwt" : generate_jwt(), # for answer step after summary
    }


def validate_slug(input_string):
    # Convert to lowercase
    input_string = input_string.lower()
    
    # Replace any non-alphanumeric character with a hyphen
    transformed = re.sub(r'[^a-z0-9\s-]', '-', input_string)
    
    # Replace spaces with hyphens
    transformed = transformed.replace(' ', '-')
    
    # Replace multiple hyphens in a row with a single hyphen
    transformed = re.sub(r'-+', '-', transformed)
    
    # Remove leading and trailing hyphens
    transformed = transformed.strip('-')

    return transformed


def create_custom_guru_type_slug(name):
    # Custom replacements for special cases
    custom_replacements = [
        ('+', 'plus'),
        ('#', 'sharp'),
        ('&', 'and'),
        ('@', 'at'),
        ('|', 'or'),
        ('%', 'percent'),
        ('*', 'star'),
    ]
    # Convert to lowercase
    name = name.lower()

    # Apply custom replacements
    for old, new in custom_replacements:
        name = name.replace(old, new)

    # Use slugify with custom settings
    slug = slugify(name, 
                   replacements=custom_replacements,
                   allow_unicode=False,
                   lowercase=True,
                   separator='-')

    return slug

class GptSummary(BaseModel):
    question: str
    user_question: str
    question_slug: str
    description: str
    valid_question: bool
    user_intent: str
    answer_length: int


def slack_send_outofcontext_question_notification(guru_type, user_question, question, user=None):
    if settings.SLACK_NOTIFIER_ENABLED:
        payload = {"text": f"🔴 Out of context question detected\nGuru Type: {guru_type}\nUser Question: {user_question}\nQuestion: {question}"}
        if user:
            payload["text"] += f"\nUser Email: {user.email}"
        try:
            response = requests.post(settings.SLACK_NOTIFIER_WEBHOOK_URL, json=payload, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Slack notification for out of context question: {str(e)}", exc_info=True)

def get_github_details_if_applicable(guru_type):
    guru_type_obj = get_guru_type_object(guru_type)
    response = ""
    if guru_type_obj.github_details:
        simplified_github_details = {}
        simplified_github_details['name'] = guru_type_obj.github_details['name']
        simplified_github_details['description'] = guru_type_obj.github_details['description']
        simplified_github_details['topics'] = guru_type_obj.github_details['topics']
        simplified_github_details['language'] = guru_type_obj.github_details['language']
        simplified_github_details['size'] = guru_type_obj.github_details['size']
        simplified_github_details['homepage'] = guru_type_obj.github_details['homepage']
        simplified_github_details['stargazers_count'] = guru_type_obj.github_details['stargazers_count']
        simplified_github_details['forks_count'] = guru_type_obj.github_details['forks_count']
        simplified_github_details['license_name'] = guru_type_obj.github_details.get('license', {}).get('name')
        simplified_github_details['open_issues_count'] = guru_type_obj.github_details['open_issues_count']
        simplified_github_details['pushed_at'] = guru_type_obj.github_details['pushed_at']
        simplified_github_details['created_at'] = guru_type_obj.github_details['created_at']
        simplified_github_details['owner_login'] = guru_type_obj.github_details['owner']['login']
        response = f"Here is the GitHub details for {guru_type_obj.name}: {simplified_github_details}"
    return response


def format_history_for_prompt(history):
    """Format conversation history into a string."""
    history_text = "Here are the history of user questions and questions for this conversation:\n\n"
    for i, h in enumerate(history, 1):
        history_text += f"{i}. User Question: {h['user_question']}\n   Question: {h['question']}\n"
    
    # Add the answer of the last question
    last_item = history[-1]
    history_text += f"\nThis is the answer of the last question: {last_item['answer']}\n"
    history_text += "\nTake these questions and answers into consideration for future answers."
    return history_text

def format_question_history(history):
    """Format the question history for the binge mini prompt."""
    history_text = ""
    for i, h in enumerate(history, 1):
        history_text += f"{i}. User Question: {h['user_question']}\n   Question: {h['question']}\n"
    return history_text.strip()

def prepare_chat_messages(user_question, question, guru_variables, context_vals, history=None):
    from core.prompts import prompt_template, binge_mini_prompt
    """Prepare messages for the chat completion API."""
    user_message = f"User Question: {user_question}\nQuestion: {question}"
    
    if history:
        question_history = format_question_history(history)
        last_answer = history[-1]['answer']
        binge_mini_prompt = binge_mini_prompt.format(
            question_history=question_history,
            answer=last_answer
        )
    else:
        binge_mini_prompt = ""
    
    # Insert binge_mini_prompt into the main prompt
    final_prompt = prompt_template.format(
        binge_mini_prompt=binge_mini_prompt if history else "",
        **guru_variables,
        **context_vals
    )
    
    messages = [
        {'role': 'system', 'content': final_prompt},
        {'role': 'user', 'content': user_message}
    ]
    
    return messages


def ask_question_with_stream(milvus_client, collection_name, question, guru_type, user_intent, answer_length, user_question, parent_question, user=None):
    vector_db_fetch_start = time.time()

    vector_db_fetch_time = time.time() - vector_db_fetch_start

    context_preprocess_start = time.time()
    default_settings = get_default_settings()
    context_vals, links, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage = get_contexts(milvus_client, collection_name, question, guru_type, user_question)
    if not reranked_scores:
        OutOfContextQuestion.objects.create(question=question, guru_type=get_guru_type_object(guru_type), user_question=user_question, rerank_threshold=default_settings.rerank_threshold, trust_score_threshold=default_settings.trust_score_threshold, processed_ctx_relevances=processed_ctx_relevances)
        slack_send_outofcontext_question_notification(guru_type, user_question, question, user)
        return None, None, None, None, None, None, None, None, None

    context_preprocess_time = time.time() - context_preprocess_start
    
    if settings.LOG_STREAM_TIMES:
        logger.info(f'Vector db fetch time: {vector_db_fetch_time}. Context preprocess time: {context_preprocess_time}')

    simplified_github_details = get_github_details_if_applicable(guru_type)

    # logger.debug(f'Contexts: {contexts}')
    guru_variables = get_guru_type_prompt_map(guru_type)
    guru_variables['streaming_type']='streaming'
    guru_variables['date'] = datetime.now().strftime("%Y-%m-%d")
    guru_variables['user_intent'] = user_intent
    guru_variables['answer_length'] = answer_length
    guru_variables['github_details_if_applicable'] = simplified_github_details

    # prompt = prompt_template.format(**guru_variables, **context_vals)
    history = get_question_history(parent_question)

    messages = prepare_chat_messages(user_question, question, guru_variables, context_vals, history)
    used_prompt = messages[0]['content']

    response = chatgpt_client.chat.completions.create(
        model=settings.GPT_MODEL,
        temperature=0,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True},
    )

    return response, used_prompt, links, context_vals, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage

def get_summary(question, guru_type, short_answer=False):
    from core.prompts import summary_template, summary_prompt_widget_addition, summary_prompt_non_widget_addition
    context_variables = get_guru_type_prompt_map(guru_type)
    context_variables['date'] = datetime.now().strftime("%Y-%m-%d")
    default_settings = get_default_settings()
    if short_answer:
        summary_prompt_widget_addition = summary_prompt_widget_addition.format(widget_answer_max_length=default_settings.widget_answer_max_length)
        summary_prompt_non_widget_addition = ""
    else:
        summary_prompt_widget_addition = ""
        summary_prompt_non_widget_addition = summary_prompt_non_widget_addition

    prompt = summary_template.format(
        **context_variables, 
        summary_prompt_widget_addition=summary_prompt_widget_addition, 
        summary_prompt_non_widget_addition=summary_prompt_non_widget_addition
    )

    if guru_type.lower() not in question.lower():
        guru_type_obj = get_guru_type_object(guru_type)
        question = f"{guru_type_obj.name} - {question}"

    try:
        response = chatgpt_client.beta.chat.completions.parse(
            model=settings.GPT_MODEL,
            temperature=0,
            messages=[
                {
                    'role': 'system',
                    'content': prompt
                },
                {
                    'role': 'user',
                    'content': question
                }
            ],
            response_format=GptSummary
        )
    except Exception as e:
        logger.error(f'Error while getting summary: {question}. Exception: {e}', exc_info=True)
        return None

    return response


def get_question_summary(question: str, guru_type: str, binge: Binge, short_answer: bool = False):
    response = get_summary(question, guru_type, short_answer)
    parsed_response = parse_summary_response(question, response)
    guru_type_object = get_guru_type_object(guru_type)
    if binge:
        parsed_response['question_slug'] = validate_slug_existence(
            parsed_response['question_slug'], 
            guru_type_object, 
            binge
        )
    return parsed_response


def ask_if_english(question):
    response = chatgpt_client.chat.completions.create(
        model=settings.GPT_MODEL_MINI,
        temperature=0,
        messages=[
            {
                'role': 'system',
                'content': "Is this question in English?. Return this json: {'question': 'question', 'is_english': True/False}"
            },
            {
                'role': 'user',
                'content': question
            }
        ],
        response_format={'type': 'json_object'}
    )

    try:
        answer = response.choices[0].message.content
        answer = json.loads(answer)
    except Exception as e:
        logger.error(f'Error while getting the answer from the response: {e}. Response: {response.choices[0].message.content}', exc_info=True)
        answer = {
            'question': question,
            'is_english': False
        }

    if "is_english" not in answer:
        answer["is_english"] = False

    return answer['is_english'], get_llm_usage_from_response(response, settings.GPT_MODEL_MINI)
            

def stream_question_answer(
        question, 
        guru_type, 
        user_intent, 
        answer_length, 
        user_question, 
        parent_question=None,
        user=None
    ):
    guru_type_obj = get_guru_type_object(guru_type)
    collection_name = guru_type_obj.milvus_collection_name
    milvus_client = get_milvus_client()

    response, prompt, links, context_vals, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage = ask_question_with_stream(
        milvus_client, 
        collection_name, 
        question, 
        guru_type, 
        user_intent, 
        answer_length, 
        user_question, 
        parent_question,
        user
    )
    if not response:
        return None, None, None, None, None, None, None, None, None

    return response, prompt, links, context_vals, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage

def validate_guru_type(guru_type, only_active=True):
    if guru_type not in get_guru_type_names(only_active=only_active):
        raise exceptions.InvalidRequestError({'msg': 'Guru type is invalid.'})


class SeoFriendlyTitleAnswer(BaseModel):
    seo_frienly_title: str

def get_more_seo_friendly_title(title):
    # Obsolete
    from core.prompts import seo_friendly_title_template
    prompt = seo_friendly_title_template.format(question=title)

    response = chatgpt_client.beta.chat.completions.parse(
        model=settings.GPT_MODEL_MINI,
        temperature=0,
        messages=[
            {
                'role': 'system',
                'content': prompt
            },
            {
                'role': 'user',
                'content': title
            }
        ],
        response_format=SeoFriendlyTitleAnswer
    )
    
    try:
        seoFriendlyTitleAnswer = response.choices[0].message.parsed
    except Exception as e:
        logger.error(f'Error while getting the answer from the response: {e}. Response: {response.choices[0].message.parsed}', exc_info=True)
        return  ""

    return seoFriendlyTitleAnswer.seo_frienly_title


def generate_similar_questions(model, guru_type, questions, generate_count_per_category):
    # Obsolete
    from core.prompts import similar_questions_template,create_question_categories
    context_variables = get_guru_type_prompt_map(guru_type)

    questions = list(map(lambda x: '- ' + x, questions))
    formatted_questions = '"""' + "\r\n".join(questions) + '"""'

    total_completion_tokens = 0
    total_prompt_tokens = 0
    total_cached_prompt_tokens = 0
    
    prompt = create_question_categories.format(questions=formatted_questions, **context_variables)
    response = chatgpt_client.chat.completions.create(
            model=settings.GPT_MODEL,
            temperature=1,
            messages=[
                {
                    'role': 'system',
                    'content': prompt
                }
            ],
            response_format={'type': 'json_object'},
            timeout=60
        )
    try:
        generated_categories = json.loads(response.choices[0].message.content)['categories']
        prompt_tokens, completion_tokens, cached_prompt_tokens = get_tokens_from_openai_response(response)
        total_completion_tokens += completion_tokens
        total_prompt_tokens += prompt_tokens
        total_cached_prompt_tokens += cached_prompt_tokens
    except Exception as e:
        logger.error(f'Error while parsing generated categories: {e}. Response: {response.choices[0].message.content}', exc_info=True)
        generated_categories = []

    # generated_categories = ['Kubernetes Cluster Configuration', 'Kubernetes Installation Issues', 'Kubernetes Controller and Cache Management', 'Kubernetes Init Containers', 'Kubernetes Resource Management', 'Kubernetes Networking and Protocols', 'Kubernetes Deployment Strategies', 'Kubernetes Helm Chart Management', 'Kubernetes Ingress and Load Balancing', 'Kubernetes API and Permissions']
    logger.info(f'Generated categories: {generated_categories}')

    # keys are categories, values are questions
    generated_questions = {}

    # go to gpt per category, when asked for all at once, it fails to generate wanted amount of questions
    prompts = []
    for category in generated_categories:
        prompt = similar_questions_template.format(questions=formatted_questions, question_count=generate_count_per_category, category=category, **context_variables)
        prompts.append(prompt)
        if model == 'claude':
            import anthropic
            claude_client = anthropic.Anthropic(
                api_key=settings.CLAUDE_API_KEY,
            )
            response = claude_client.messages.create(
                model="claude-3-5-sonnet-20240620",
                messages=[
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=8192
            )
            try:
                generated_questions[category] = json.loads(response.content[0].text)['questions']
            except Exception as e:
                logger.error(f'Error while parsing generated raw questions with claude: {e}. Response: {response.content[0].text}', exc_info=True)
        elif model == 'chatgpt':
            response = chatgpt_client.chat.completions.create(
                model=settings.GPT_MODEL,
                temperature=1,
                messages=[
                    {
                        'role': 'system',
                        'content': prompt
                    }
                ],
                response_format={'type': 'json_object'},
                timeout=120
            )
            try:
                generated_questions[category] = json.loads(response.choices[0].message.content)['questions']
                total_completion_tokens += completion_tokens
                total_prompt_tokens += prompt_tokens
                total_cached_prompt_tokens += cached_prompt_tokens
            except Exception as e:
                logger.error(f'Error while parsing generated raw questions with chatgpt: {e}. Response: {response.choices[0].message.content}', exc_info=True)
        elif model == 'gemini':
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            gemini_client = genai.GenerativeModel('gemini-1.5-pro', generation_config={"response_mime_type": "application/json"})

            chat = gemini_client.start_chat()
            response = chat.send_message(prompt)
            try:
                generated_questions[category] = json.loads(response.text)['questions']
            except Exception as e:
                logger.error(f'Error while parsing generated raw questions with gemini: {e}. Response: {response.text}', exc_info=True)

    return generated_questions, total_completion_tokens, total_prompt_tokens, total_cached_prompt_tokens, prompts


def embed_text(text, use_openai=settings.USE_OPENAI_TEXT_EMBEDDING):
    if text is None or text == '':
        logger.error(f'Empty or None text passed to embed_text')
        return None
    
    # Generate cache key using hash of text and use_openai flag
    cache_key = f"embedding:{hashlib.sha256(f'{text}:{use_openai}'.encode()).hexdigest()}"
    
    # Try to get from cache
    try:
        cache = caches['alternate']
        cached_embedding = cache.get(cache_key)
        if cached_embedding:
            return pickle.loads(cached_embedding)
    except Exception as e:
        logger.error(f'Error while getting the embedding from the cache: {e}. Cache key: {cache_key}. Text: {text}')
    
    # Generate embedding if not in cache
    if use_openai:
        requester = OpenAIRequester()
        embedding = requester.embed_text(text)
    else:
        url = settings.EMBED_API_URL
        headers = {"Content-Type": "application/json"}
        if settings.EMBED_API_KEY:
            headers["Authorization"] = f"Bearer {settings.EMBED_API_KEY}"
        response = requests.post(url, headers=headers, data=json.dumps({"inputs": text}), timeout=30)
        if response.status_code == 200:
            embedding = response.json()[0]
        else:
            logger.error(f'Error while embedding the text: {text}. Response: {response.text}. Url: {url}, Auth key: {settings.EMBED_API_KEY}')
            return None

    if embedding:
        try:
            # Cache the embedding (8 weeks expiration)
            cache.set(cache_key, pickle.dumps(embedding), timeout=60*60*24*7*8)
        except Exception as e:
            logger.error(f'Error while caching the embedding: {e}. Cache key: {cache_key}. Text: {text}')
        
    return embedding


def embed_texts(texts, use_openai=settings.USE_OPENAI_TEXT_EMBEDDING):
    batch_size = 32
    embeddings = []
    for i in range(0, len(texts), batch_size):
        if use_openai:
            requester = OpenAIRequester()
            openai_embeddings = requester.embed_texts(texts[i:i+batch_size])
            embeddings.extend(openai_embeddings)
        else:
            url = settings.EMBED_API_URL
            headers = {"Content-Type": "application/json"}
            if settings.EMBED_API_KEY:
                headers["Authorization"] = f"Bearer {settings.EMBED_API_KEY}"
            response = requests.post(url, headers=headers, data=json.dumps({"inputs": texts[i:i+batch_size]}), timeout=30)
        
            if response.status_code == 200:
                embeddings.extend(response.json())
            else:
                logger.error(f'Error while embedding the batch: {texts[i:i+batch_size]}. Response: {response.text}. Url: {url}')
                raise Exception(f'Error while embedding the batch. Response: {response.text}. Url: {url}')
    return embeddings


def rerank_texts(query, texts):
    # Using BAAI/bge-reranker-large model for reranking
    # This model's input size is limited to 512 tokens. If the input size is too big, we will truncate the texts
    # We will try to rerank the results in batches
    max_limits = [1300, 1200, 1000, 800, 500, 100]
    url = settings.RERANK_API_URL
    headers = {"Content-Type": "application/json"}
    if settings.RERANK_API_KEY:
        headers["Authorization"] = f"Bearer {settings.RERANK_API_KEY}"

    for limit in max_limits:
        truncated_texts = [text[:limit] for text in texts]
        data = json.dumps({"query": query, "texts": truncated_texts})
        
        try:
            response = requests.post(url, headers=headers, data=data, timeout=30)
        except Exception as e:
            logger.error(f'Reranking: Error while reranking the batch: {[text[:100] for text in texts]}. Response: {e}. Url: {url}')
            return None
        
        if response.status_code == 200:
            return response.json()
        
        if response.reason == "Payload Too Large" and response.status_code == 413:
            # '{"error":"Input validation error: `inputs` must have less than 512 tokens. Given: 565","error_type":"Validation"}'
            logger.warning(f'Reranking: Text is too long for limit {limit}. Trying again with new limit. Question: {query}')
            continue
    
    logger.error(f'Reranking: Tried all the limits. Error while reranking the batch: {[text[:100] for text in texts]}. Response: {response.text}. Url: {url}')
    return None


def get_most_similar_questions(slug, text, guru_type, column, top_k=10, sitemap_constraint=False):

    if settings.ENV == 'selfhosted':
        return []
    
    if column not in ['title', 'description', 'content']:
        raise ValueError(f'Invalid column: {column}')
    
    embedding = embed_text(text)
    if not embedding:
        return []

    closest = search_for_closest(settings.MILVUS_QUESTIONS_COLLECTION_NAME, embedding, guru_type, top_k=top_k, column=column, sitemap_constraint=sitemap_constraint)

    processed = []
    for element in closest:
        entity = element['entity']
        entity['distance'] = element['distance']
        entity['id'] = element['id']
        processed.append(entity)

    for i, similar_question in enumerate(processed):
        if similar_question['slug'] == slug:
            processed.pop(i)
            break

    return processed


def with_redis_lock(redis_client, lock_key_func, timeout):
    class Locked(Exception):
        pass

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug(f'Args: {args}. Kwargs: {kwargs}')
            try:
                # Handle both guru_type_slug and is_github parameters
                is_github = kwargs.get('is_github')
                if 'guru_type_slug' in kwargs:
                    if is_github is not None:
                        lock_key = lock_key_func(kwargs['guru_type_slug'], is_github)
                    else:
                        lock_key = lock_key_func(kwargs['guru_type_slug'])
                elif 'guru_type' in kwargs:
                    if is_github is not None:
                        lock_key = lock_key_func(kwargs['guru_type'].slug, is_github)
                    else:
                        lock_key = lock_key_func(kwargs['guru_type'].slug)
                elif type(lock_key_func) == str:
                    lock_key = lock_key_func
                else:
                    raise ValueError("Missing required guru_type_slug or guru_type parameter")
                
            except Exception as e:
                logger.error(f"Error generating lock key: {str(e)}", exc_info=True)
                raise e
                
            try:
                pipe = redis_client.pipeline()
                pipe.watch(lock_key)
                locked = pipe.get(lock_key)
                if locked == 'true':
                    raise Locked()
                pipe.multi()
                pipe.set(lock_key, 'true', ex=timeout)
                pipe.execute()

                try:
                    start_time = datetime.now(UTC)
                    result = func(*args, **kwargs)
                except Exception as e2:
                    raise e2
                finally:
                    if datetime.now(UTC) - start_time > timedelta(seconds=timeout):
                        logging.warn(f'The function {func.__name__} took longer than {timeout} seconds to execute.')
                    else:
                        redis_client.delete(lock_key)
                    
                return result

            except Locked:
                logging.warn(f'Could not acquire lock {lock_key}.')
                
            except Exception as e:
                logging.error(f'Failed to execute the function {func.__name__} due to {traceback.format_exc()}.')
                
        return wrapper
    return decorator

    
def format_references(references):
    processed_references = []
    for reference in references:
        reference['question'] = html.unescape(reference['question'])
        processed_references.append(reference)
    return processed_references


def generate_og_image(question):
    from PIL import Image, ImageDraw, ImageFont
    from core.gcp import OG_IMAGES_GCP
    # generates and saves og image to gcp bucket
    # keeps url in question model
    template_filename = f'images/{question.guru_type}_og_image.jpg'
    font_filename = 'fonts/Inter-VariableFont_opsz,wght.ttf'

    template_path = os.path.join(settings.STATICFILES_DIRS[0], 'backend', template_filename)
    font_path = os.path.join(settings.STATICFILES_DIRS[0], 'backend', font_filename)

    if not os.path.exists(template_path):
        # check if question guru type is custom
        if question.guru_type.custom and question.guru_type.ogimage_url != '':
            template_path = os.path.join(settings.STATICFILES_DIRS[0], 'backend', template_filename)
            # go fetch the image and save under template_path            
            response = requests.get(question.guru_type.ogimage_url, timeout=30)
            if response.status_code == 200:
                with open(template_path, 'wb') as f:
                    f.write(response.content)
        else:
            template_path = os.path.join(settings.STATICFILES_DIRS[0], 'backend', 'images', '0_default_og_image.jpg')

    output_path = os.path.join(settings.MEDIA_ROOT, f'{question.id}.jpg') 

    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    template = Image.open(template_path)
    
    # Convert the image to RGB mode
    template = template.convert('RGB')
    
    guru_width_at_right = 228 * 2
    logger.debug(f'Image size: {template.size}, Width: {template.width}, Height: {template.height}')
    og_width, og_height = template.width - guru_width_at_right, template.height
    
    font = 50
    if len(question.question) > 150:
        font = 40
    title_font = ImageFont.truetype(font_path, 2*font) 

    draw = ImageDraw.Draw(template)

    padding_to_guru_type_at_right = 2 * 40
    gurubase_logo_height_at_bottom = 2 * 40.5

    title_height = calculate_text_height(draw, question.question, title_font, og_width, padding_to_guru_type_at_right)
    
    # padding from up and left
    start_y = (og_height - gurubase_logo_height_at_bottom - title_height) // 2
    logger.debug(f'Start y: {start_y}, Title height: {title_height}, Guru logo height at bottom: {gurubase_logo_height_at_bottom}')
    start_x = 40 * 2
    next_y = draw_text(draw, start_x, start_y, question.question, title_font, og_width, padding_to_guru_type_at_right,(0, 0, 0))

    # Before saving, ensure the image is in RGB mode
    template = template.convert('RGB')
    template.save(output_path, 'JPEG')

    folder = settings.ENV
    gcpTargetPath = f'./{folder}/{question.guru_type}/{question.slug}-{question.id}.jpg'
    logger.debug(f'gcp target path: {gcpTargetPath}')
    url, success = OG_IMAGES_GCP.upload_image(open(output_path, 'rb'), gcpTargetPath)

    if not success:
        return f'Failed to upload og image for {question.id}', False
    
    publicly_accessible_persistent_url = url.split('?', 1)[0]
    logger.debug(f'gcp url for {question.id} : {publicly_accessible_persistent_url}')
    question.og_image_url = publicly_accessible_persistent_url
    question.save()

    # clean output_path
    os.remove(output_path)
    return question.og_image_url, True

def calculate_text_height(draw, text, font, max_width, padding):
    """
    Calculate the height needed for a block of text.
    """
    y = 0
    limit = max_width - 2 * padding
    line = ""
    for word in text.split():
        line += word + " "
        l = draw.textlength(line, font=font)
        if l > limit:
            y += font.size
            line = word + " "
    logger.debug(f'Calculated text height: {y}')
    return y + font.size


def draw_line(draw, x, y, line, font, color):
    """
    Draw a line of text at a specific position.
    """
    if line == "":
        return y
    logger.debug(f'Drawing line: {line}, x: {x}, y: {y}')
    draw.text((x, y), line.strip(), font=font, fill=color)
    return y + font.size

def draw_text(draw, x, y, text, font, max_width, padding, color):
    """
    Draw text onto an image.
    """
    line = ""
    for word in text.split():
        if is_line_too_long(line, word, draw, font, max_width, padding):
            y = draw_line(draw, x + padding, y, line, font, color)
            line = ""
        line += word + " "
    return draw_line(draw, x + padding, y, line, font, color)

def is_line_too_long(line, word, draw, font, max_width, padding):
    """
    Check if adding a word to a line makes it too long.
    """
    return draw.textlength(line + word, font=font) > max_width - 3 * padding

# generate a jwt with 1 minute expiration
def generate_jwt():
    encoded = jwt.encode(
        {
            "iss": "guru-backend",
            "aud": "nextjs-client",
            "exp": datetime.utcnow() + timedelta(seconds=settings.JWT_EXPIRATION_SECONDS)
        },
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    return encoded

# check given jwt's validity, it checks expiry, issuer and audience automatically
# of course jwt must be signed with corresponding private key, that's the whole point.
def decode_jwt(encoded_jwt):
    try:
        jwt.decode(
            encoded_jwt,
            settings.SECRET_KEY,
            issuer="guru-backend",
            audience=["nextjs-client"],
            algorithms=["HS256"]
        )
        return True
    except Exception as e:
        return False


def get_website_icon(domain):
    try:
        # Check if the favicon is already in the database
        favicon = Favicon.objects.filter(domain=domain).first()
        if favicon:
            return favicon.url

        # First, try to get favicon.ico
        favicon_url = f"https://{domain}/favicon.ico"
        response = requests.head(favicon_url, timeout=5)
        if response.status_code == 200:
            # Save the favicon to the database
            Favicon.objects.create(domain=domain, favicon_url=favicon_url, valid=True)
            return favicon_url

        # If favicon.ico doesn't exist, try to parse the HTM
        url = f"https://{domain}"
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for link tags with rel="icon" or rel="shortcut icon"
        icon_link = soup.find('link', rel=lambda x: x and x.lower() in ['icon', 'shortcut icon'])
        if icon_link and icon_link.get('href'):
            favicon_url = urljoin(url, icon_link['href'])
            # Save the favicon to the database
            Favicon.objects.create(domain=domain, favicon_url=favicon_url, valid=True)
            return favicon_url

    except Exception as e:
        logger.error(f"Error fetching icon for {domain}: {str(e)}", exc_info=True)
    
    # Icon validity check failed
    favicon = Favicon.objects.create(domain=domain, favicon_url=favicon_url, valid=False)
    return favicon.url


def get_links(content):
    # Get everything in the format (link_name)[url]
    links = re.findall(r'\[[^\]]+\]\([^)]+\)', content)
    return links


def validate_image(image):
    if not image:
        return 'No image provided', None
    split = image.name.rsplit('.', 1)
    if len(split) != 2 or split[1] not in ['jpg', 'png', 'jpeg', 'svg']:
        return 'Invalid image extension', None
    return None, split


def upload_image_to_storage(image, name_without_extension, extension):
    from io import BytesIO

    # Open and process image
    img = Image.open(image)
    
    # Create 100x100 white background
    background = Image.new('RGBA', (100, 100), (255, 255, 255, 255))
    
    # Calculate resize dimensions while maintaining aspect ratio
    ratio = min(100 / img.width, 100 / img.height)
    new_size = (int(img.width * ratio), int(img.height * ratio))
    img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # Calculate position to center image
    pos = ((100 - new_size[0]) // 2, (100 - new_size[1]) // 2)
    
    # Paste resized image onto white background
    background.paste(img, pos, img if img.mode == 'RGBA' else None)
    
    # Convert to bytes
    img_byte_arr = BytesIO()
    background.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    random_key = uuid.uuid4().hex[:30]
    expected_path = f'{settings.ENV}/guru_type_images/{name_without_extension}-{random_key}.png'
    if settings.ENV == 'selfhosted':
        from core.gcp import DATA_SOURCES_FILESYSTEM
        path, success = DATA_SOURCES_FILESYSTEM.upload_file(img_byte_arr, expected_path)
    else:
        from core.gcp import DATA_SOURCES_GCP
        path, success = DATA_SOURCES_GCP.upload_file(img_byte_arr, expected_path)
    if not success:
        return 'Error uploading image', None
    if settings.ENV == 'selfhosted':
        return None, os.path.join(settings.MEDIA_ROOT, expected_path)
    return None, f'https://storage.googleapis.com/{settings.GS_DATA_SOURCES_BUCKET_NAME}/{expected_path}'


def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])

def get_dominant_color(image_url):
    if settings.ENV == 'selfhosted':
        img = Image.open(image_url)
        img_bytes = BytesIO()
        img.save(img_bytes, format=img.format)
        img_bytes.seek(0)
        color_thief = ColorThief(img_bytes)
    else:
        response = requests.get(image_url, timeout=30)
        img = BytesIO(response.content)
        color_thief = ColorThief(img)
    
    # Get the dominant color
    dominant_color = color_thief.get_color(quality=1)
    
    # Check if the dominant color has enough contrast with white
    if not has_sufficient_contrast(dominant_color):
        # Try to get a color palette
        palette = color_thief.get_palette(color_count=5)
        
        # Find the first color in the palette that has sufficient contrast
        for color in palette:
            if has_sufficient_contrast(color):
                return rgb_to_hex(color)
        
        # If all colors in the palette have insufficient contrast, use a soft red
        return '#FF6B6B'  # Soft red color
    
    return rgb_to_hex(dominant_color)

def has_sufficient_contrast(rgb_color):
    # Calculate relative luminance
    r, g, b = [x / 255.0 for x in rgb_color]
    r = adjust_color(r)
    g = adjust_color(g)
    b = adjust_color(b)
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    
    # Calculate contrast ratio with white (luminance of white is 1)
    contrast_ratio = (luminance + 0.05) / (1 + 0.05)
    
    # Return True if the contrast ratio is sufficient (e.g., greater than 3:1)
    return contrast_ratio <= 1/2  # This is equivalent to the inverse being >= 3

def adjust_color(color):
    if color <= 0.03928:
        return color / 12.92
    else:
        return ((color + 0.055) / 1.055) ** 2.4

def lighten_color(hex_color):
    # Convert hex to RGB
    rgb = tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    
    # Lighten the color by blending with white
    lightened_rgb = tuple(int(c + (255 - c) * 0.9) for c in rgb)
    
    # Convert to 6-digit hex and return
    return '#{:02x}{:02x}{:02x}'.format(*lightened_rgb)

def create_guru_type_object(slug, name, intro_text, domain_knowledge, icon_url, stackoverflow_tag, stackoverflow_source, github_repo, maintainer=None):
    base_color = get_dominant_color(icon_url)
    light_color = lighten_color(base_color)
    colors = {"base_color": base_color, "light_color": light_color}
    ogimage_url = ''
    active = True

    guru_type = GuruType.objects.create(
        slug=slug,
        name=name,
        intro_text=intro_text,
        domain_knowledge=domain_knowledge,
        colors=colors,
        icon_url=icon_url,
        ogimage_url=ogimage_url,
        stackoverflow_tag=stackoverflow_tag,
        stackoverflow_source=stackoverflow_source,
        github_repo=github_repo,
        active=active
    )
    if maintainer:
        guru_type.maintainers.add(maintainer)
    return guru_type
  
# parses the context metadata from the prompt and saves the context distances in the question model
def parse_context_from_prompt(question):
    milvus_client = get_milvus_client()
    prompt = question.prompt
    collection_name = question.guru_type.milvus_collection_name

    # Regular expression pattern to match the context metadata
    pattern = r"Context \d+ metadata: \n'''(.*?)'''"

    # Finding all matches of the pattern in the text
    matches = re.findall(pattern, prompt, re.DOTALL)

    # Parsing each match as a dictionary
    context_metadatas = [eval(match) for match in matches]

    embedding = embed_text(question.question)
    
    # [ {'context_id': 1, 'distance': 0.1}, ...]
    context_distances = []

    # Printing the extracted contexts
    for i, metadata in enumerate(context_metadatas, 1):
        filter = ''
        if 'type' in metadata and metadata['type'] in ['WEBSITE', 'PDF', 'YOUTUBE']:
            # type , title, link
            filter += f'metadata["type"] == "{metadata["type"]}"'
            if 'title' in metadata and metadata['title']:
                filter += f' && metadata["title"] == "{metadata["title"]}"'
            if 'link' in metadata and metadata['link']:
                filter += f' && metadata["link"] == "{metadata["link"]}"'
        else:
            # Stackoverflow questions
            if 'type' in metadata and metadata['type']:
                filter += f'metadata["type"] == "{metadata["type"]}"'
                if 'question' in metadata and metadata['question']:
                    filter += f' && metadata["question"] == "{metadata["question"]}"'
                if 'score' in metadata and metadata['score']:
                    filter += f' && metadata["score"] == {metadata["score"]}'
                if 'owner_reputation' in metadata and metadata['owner_reputation']:
                    filter += f' && metadata["owner_reputation"] == {metadata["owner_reputation"]}'
                # if 'owner_badges' in metadata and metadata['owner_badges']:
                #     filter += f' && metadata["owner_badges"] == {metadata["owner_badges"]}'
                if 'link' in metadata and metadata['link']:
                    filter += f' && metadata["link"] == "{metadata["link"]}"'
            else:
                # YC essays
                if 'title' in metadata and metadata['title']:
                    filter += f'metadata["title"] == "{metadata["title"]}"'
                    if 'author' in metadata and metadata['author']:
                        filter += f' && metadata["author"] == "{metadata["author"]}"'
                # YC videos
                elif 'view_count' in metadata and metadata['view_count']: 
                    filter += f'metadata["view_count"] == {metadata["view_count"]}'
                    if 'link' in metadata and metadata['link']:
                        filter += f' && metadata["link"] == "{metadata["link"]}"'
        
        logger.info(f'Filter: {filter}')
        result = milvus_client.query(collection_name,
                     filter=filter,
                     output_fields=['id'])
        
        logger.info(f'Query result: {result}')

        docs = milvus_client.search(collection_name=collection_name, 
            data=[embedding], 
            limit=1, 
            filter=filter,
            output_fields=['id'])
        
        if len(docs[0]) == 0:
            logger.error(f'context search failed for {metadata}')
            continue
        
        d = docs[0][0]        
        id = d['id']
        distance = d['distance']

        context_distances.append({'context_id': id, 'distance': distance})

    # save the distance in question model
    question.context_distances = context_distances
    question.save()


def finalize_data_source_summarizations(data_source, max_length=settings.SUMMARIZATION_MAX_LENGTH):
    """
    Finalizes the data source summarizations by merging and summarizing the content of the summarizations.

    Args:
        data_source: The data source object to finalize the summarizations for.
        max_length: The maximum length of the merged content.
    """

    if data_source.final_summarization_created:
        logger.warning(f"Data source {data_source.id} final summarization already created")
        return

    if Summarization.objects.filter(
        is_data_source_summarization=True,
        data_source_ref=data_source,
        is_root=True
    ).exists():
        # If root summarization exists, it means the data source summarizations are already finalized
        logger.warning(f"Data source {data_source.id} final summarization already created. Setting it as so.")
        data_source.final_summarization_created = True
        data_source.save()
        return
    
    unprocessed_summarizations = Summarization.objects.filter(
        is_data_source_summarization=True,
        data_source_ref=data_source,
        processed=False,
        is_root=False
    )
    
    current_content = ""
    current_summarizations = []

    content_metadata = [data_source.get_metadata()]
    
    for summarization in unprocessed_summarizations:
        if len(current_content) + len(summarization.result_content) > max_length:
            if not current_content:
                logger.error(f"The content max limit is smaller than the size of a single summarization for data source {data_source.id} and summarization {summarization.id}")
                return
            try:
                merged_content = current_content.strip()
                merged_content = f'\n<METADATA>{content_metadata}</METADATA>\n\n{merged_content}'
                summarized, model_name, usages, summary_suitable, reasoning = summarize_text(merged_content, data_source.guru_type)
                new_summarization = Summarization.objects.create(
                    guru_type=data_source.guru_type,
                    is_data_source_summarization=True,
                    content_metadata=content_metadata,
                    data_source_ref=data_source,
                    source_content=merged_content,
                    result_content=summarized,
                    is_root=False,
                    processed=False,
                    initial=False,
                    model=model_name,
                    usages=usages,
                    summary_suitable=summary_suitable,
                    reasoning=reasoning
                )
                new_summarization.summarization_refs.set(current_summarizations)
                Summarization.objects.filter(id__in=[s.id for s in current_summarizations]).update(processed=True)
                
                current_content = summarization.result_content
                current_summarizations = [summarization]
            except Exception as e:
                logger.error(f"Error while summarizing content: {str(e)}")
                return
        else:
            current_content += " " + summarization.result_content
            current_summarizations.append(summarization)
    
    # Process any remaining content
    if current_content:
        try:
            is_root = len(unprocessed_summarizations) == len(current_summarizations)
            merged_content = current_content.strip()
            merged_content = f'\n<METADATA>{content_metadata}</METADATA>\n\n{merged_content}'
            summarized, model_name, usages, summary_suitable, reasoning = summarize_text(merged_content, data_source.guru_type)
            new_summarization = Summarization.objects.create(
                guru_type=data_source.guru_type,
                is_data_source_summarization=True,
                content_metadata=content_metadata,
                data_source_ref=data_source,
                source_content=merged_content,
                result_content=summarized,
                is_root=is_root,
                processed=False,
                model=model_name,
                usages=usages,
                summary_suitable=summary_suitable,
                reasoning=reasoning
            )
            new_summarization.summarization_refs.set(current_summarizations)
            Summarization.objects.filter(id__in=[s.id for s in current_summarizations]).update(processed=True)

            if is_root:
                data_source.final_summarization_created = True
                data_source.save()
        except Exception as e:
            logger.error(f"Error while summarizing remaining content: {str(e)}")
            return

    # logger.info(f"Successfully merged and summarized content for a layer of the data source {data_source.id}")


def create_guru_type_summarization(guru_type, max_length=settings.SUMMARIZATION_MAX_LENGTH):
    """
    Gets a guru type, and then fetches a list of final data source summaries belonging to that guru type.
    It then merges them until a single summarization is created.
    A batch is introduced to prevent memory issues.

    Args:
        guru_type: The guru type object to merge summarizations for.
        max_length: The maximum length of the merged content.
    """

    # Finished data source summarizations
    data_source_summarizations = Summarization.objects.filter(
        guru_type=guru_type,
        is_data_source_summarization=True,
        processed=False,
        is_root=True
    )[:settings.TASK_FETCH_LIMIT] # Batch to prevent memory issues
    
    # Intermediate merged summarizations
    intermediate_summarizations = Summarization.objects.filter(
        guru_type=guru_type,
        is_data_source_summarization=False,
        processed=False
    )[:settings.TASK_FETCH_LIMIT] # Batch to prevent memory issues

    summarizations = list(data_source_summarizations) + list(intermediate_summarizations)
    
    if len(summarizations) < 2:
        # logger.info(f"No summarizations to merge for guru type {guru_type.slug}")
        return

    logger.info(f"Merging {len(summarizations)} summarizations for guru type {guru_type.slug}")
    # Check if a final summarization for the whole guru type already exists
    final_summarization = Summarization.objects.filter(
        guru_type=guru_type,
        is_data_source_summarization=False,
        is_root=True
    ).first()

    if final_summarization:
        # Set it as not root 
        final_summarization.is_root = False
        final_summarization.save()
    
    current_content = ""
    current_summarizations = []
    current_content_metadata = []
    
    for summarization in summarizations:
        if len(current_content) + len(summarization.result_content) > max_length:
            if not current_content:
                logger.error(f"The content max limit is smaller than the size of a single summarization for summarization {summarization.id}")
                return
            try:
                merged_content = current_content.strip()
                summarized, model_name, usages, summary_suitable, reasoning = summarize_text(text=merged_content, guru_type=guru_type)
                new_summarization = Summarization.objects.create(
                    guru_type=guru_type,
                    is_data_source_summarization=False,
                    source_content=merged_content,
                    result_content=summarized,
                    content_metadata=current_content_metadata,
                    is_root=False,
                    processed=False,
                    initial=False,
                    model=model_name,
                    usages=usages,
                    summary_suitable=summary_suitable,
                    reasoning=reasoning
                )
                new_summarization.summarization_refs.set(current_summarizations)
                Summarization.objects.filter(id__in=[s.id for s in current_summarizations]).update(processed=True)
                
                current_content = f'\n<METADATA>{summarization.content_metadata}</METADATA>\n\n{summarization.result_content}'
                current_summarizations = [summarization]
                current_content_metadata = summarization.content_metadata or []
            except Exception as e:
                logger.error(f"Error while summarizing content: {str(e)}")
                return
        else:
            current_content += f"\n<METADATA>{summarization.content_metadata}</METADATA>\n\n{summarization.result_content}"
            current_summarizations.append(summarization)
            if summarization.content_metadata:
                current_content_metadata.extend(summarization.content_metadata)
    
    # Process any remaining content
    if current_content:
        try:
            is_root = len(summarizations) == len(current_summarizations)
            merged_content = current_content.strip()
            summarized, model_name, usages, summary_suitable, reasoning = summarize_text(text=merged_content, guru_type=guru_type)
            new_summarization = Summarization.objects.create(
                guru_type=guru_type,
                is_data_source_summarization=False,
                source_content=merged_content,
                result_content=summarized,
                content_metadata=current_content_metadata,
                is_root=is_root,
                processed=False,
                model=model_name,
                usages=usages,
                summary_suitable=summary_suitable,
                reasoning=reasoning
            )
            new_summarization.summarization_refs.set(current_summarizations)
            Summarization.objects.filter(id__in=[s.id for s in current_summarizations]).update(processed=True)
        except Exception as e:
            logger.error(f"Error while summarizing remaining content: {str(e)}")
            return
            


def get_default_settings():
    try:
        settings, created = Settings.objects.get_or_create(id=1)
    except Exception as exc:
        logger.error(f'Error getting default settings: {exc}', exc_info=True)
        raise exc
    return settings


def simulate_summary_and_answer(question, guru_type, check_existence, save, source):
    """
    Simulate the summary and answer endpoints to get the answer and the usages of the tokens.
    
    Args:
        question (str): The question to simulate the summary and answer for.
        guru_type (GuruType): The guru type to simulate the summary and answer for.
        check_existence (bool): Whether to check if the question exists.
        save (bool): Whether to save the question and answer.
        source (Question.Source): The source of the question. Only used if save is True.
    
    Returns:
        tuple: A tuple containing the answer, an error message (None if no error), and the usages of the tokens.
    """

    usages = {
        'prompt_tokens': 0,
        'completion_tokens': 0,
    }
    
    # Did not use the actual endpoints but used the helpers used themselves
    # This is done to:
    # 1- Conditionally avoid question existence checks while summarizing and answering the question
    # 2- Be able to get the usages of the tokens
    
    # Conditionally check if the question exists
    # First without slug
    if check_existence:
        existing_question = search_question(
            None, 
            guru_type, 
            None, 
            None, 
            question
        )
        if existing_question:
            logger.warning(f"Question {question} already exists for guru type {guru_type.slug}")
            return existing_question.content, None, usages, None

    summary_data = get_question_summary(question, guru_type.slug, None, short_answer=False)
    # Then with slug
    if check_existence:
        existing_question = search_question(
            None, 
            guru_type, 
            None, 
            summary_data['question_slug'], 
            question
        )
        if existing_question:
            logger.warning(f"Question {question} already exists for guru type {guru_type.slug}")
            return existing_question.content, None, usages, None
    
    if 'valid_question' not in summary_data or not summary_data['valid_question']:
        return None, "Invalid question", usages, None

    summary_prompt_tokens = summary_data.get('prompt_tokens', 0)
    summary_completion_tokens = summary_data.get('completion_tokens', 0)
    summary_cached_prompt_tokens = summary_data.get('cached_prompt_tokens', 0)
    user_intent = summary_data.get('user_intent', '')
    answer_length = summary_data.get('answer_length', '')
    user_question = summary_data['user_question']
    question_slug = summary_data['question_slug']
    description = summary_data['description']

    response, prompt, links, context_vals, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage = stream_question_answer(
        question, 
        guru_type.slug, 
        user_intent, 
        answer_length, 
        user_question
    )

    total_response = []
    chunks = []
    latency_start = time.time()
    if not response:
        logger.error(f"No response from the LLM for question {question} and guru type {guru_type.slug}.")
        return None, "No response from the LLM", usages, None

    for chunk in response:
        chunks.append(chunk)
        try:
            if len(chunk.choices) == 0:
                # Last chunk
                pass
            else:
                data = chunk.choices[0].delta.content
                if data is None:
                    continue
                total_response.append(data)
        except Exception as e:
            logger.error(f'Error while streaming the response: {e}', exc_info=True)
            break

    if chunk is None:
        log_error_with_stack(f'No chunk is given to calculate the tokens. Will find the last one.')
        # Get last non-null chunk
        for c in reversed(chunks):
            if c is not None:
                chunk = c
                break

    latency_sec = time.time() - latency_start

    answer = ''.join(total_response)

    prompt_tokens, completion_tokens, cached_prompt_tokens = get_tokens_from_openai_response(chunk)
    prompt_tokens += summary_prompt_tokens
    completion_tokens += summary_completion_tokens
    cached_prompt_tokens += summary_cached_prompt_tokens

    usages['completion_tokens'] = completion_tokens
    usages['prompt_tokens'] = prompt_tokens
    usages['cached_prompt_tokens'] = cached_prompt_tokens
    question_obj = None

    llm_usages = {}
    llm_usages['summary'] = {
        'prompt_tokens': summary_prompt_tokens,
        'completion_tokens': summary_completion_tokens,
        'cached_prompt_tokens': summary_cached_prompt_tokens,
        'cost_dollars': get_llm_usage(settings.GPT_MODEL, summary_prompt_tokens, summary_completion_tokens, summary_cached_prompt_tokens),
        'model': settings.GPT_MODEL
    }

    llm_usages['answer'] = {
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion_tokens,
        'cached_prompt_tokens': cached_prompt_tokens,
        'cost_dollars': get_llm_usage(settings.GPT_MODEL, prompt_tokens, completion_tokens, cached_prompt_tokens),
        'model': settings.GPT_MODEL
    }

    llm_usages['context_relevance'] = ctx_rel_usage

    if save:
        cost_dollars = get_llm_usage(settings.GPT_MODEL, prompt_tokens, completion_tokens, cached_prompt_tokens)
        existing_question = Question.objects.filter(slug=question_slug, guru_type=guru_type).first()
        if not existing_question:
            existing_question = Question.objects.filter(question=question, guru_type=guru_type).first()
        if existing_question:
            question_obj = existing_question
            question_obj.question = question
            question_obj.user_question = user_question
            question_obj.content = answer
            question_obj.description = description
            question_obj.change_count += 1
            question_obj.completion_tokens = completion_tokens
            question_obj.prompt_tokens = prompt_tokens
            question_obj.cached_prompt_tokens = cached_prompt_tokens
            question_obj.cost_dollars = cost_dollars
            question_obj.latency_sec = latency_sec
            question_obj.source = source
            question_obj.prompt = prompt
            question_obj.references = links
            question_obj.context_distances = context_distances
            question_obj.reranked_scores = reranked_scores
            question_obj.trust_score = trust_score
            question_obj.processed_ctx_relevances = processed_ctx_relevances
            question_obj.save()
        else:
            question_obj = Question(
                slug=question_slug,
                question=question,
                user_question=user_question,
                content=answer,
                description=description,
                guru_type=guru_type,
                completion_tokens=completion_tokens,
                prompt_tokens=prompt_tokens,
                cached_prompt_tokens=cached_prompt_tokens,
                cost_dollars=cost_dollars,
                latency_sec=latency_sec,
                source=source,
                prompt=prompt,
                references=links,
                context_distances=context_distances,
                reranked_scores=reranked_scores,
                trust_score=trust_score,
                processed_ctx_relevances=processed_ctx_relevances,
                llm_usages=llm_usages
            )
            question_obj.save()

    return answer, None, usages, question_obj

    
def split_text(text, max_length, min_length, overlap, separators=None):
    def merge_small_chunks(chunks, min_size=1000):
        merged_chunks = []
        current_chunk = ""

        for chunk in chunks:
            current_chunk += chunk
            if len(current_chunk) >= min_size:
                merged_chunks.append(current_chunk)
                current_chunk = ""
        
        if current_chunk:  # Add any remaining content
            if merged_chunks:
                merged_chunks[-1] += current_chunk  # Append to the last chunk if it exists
            else:
                merged_chunks.append(current_chunk)  # Create a new chunk if it's the only content

        return merged_chunks
    
    if separators is None:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_length,
            chunk_overlap=overlap,
        )
    else:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_length,
            chunk_overlap=overlap,
            separators=separators
        )

    chunks = splitter.split_text(text)
    merged_chunks = merge_small_chunks(chunks, min_length)

    return merged_chunks

def map_extension_to_language(extension: str):
    map = {
        'cpp': Language.CPP,
        'h': Language.CPP,
        'hpp': Language.CPP,
        'go': Language.GO,
        'java': Language.JAVA,
        'kt': Language.KOTLIN,
        'js': Language.JS,
        'jsx': Language.JS,
        'ts': Language.TS,
        'tsx': Language.TS,
        'php': Language.PHP,
        'proto': Language.PROTO,
        'py': Language.PYTHON,
        'rst': Language.RST,
        'rb': Language.RUBY,
        'rs': Language.RUST,
        'scala': Language.SCALA,
        'swift': Language.SWIFT,
        'md': Language.MARKDOWN,
        'tex': Language.LATEX,
        'html': Language.HTML,
        'htm': Language.HTML,
        'sol': Language.SOL,
        'cs': Language.CSHARP,
        'cob': Language.COBOL,
        'cbl': Language.COBOL,
        'c': Language.C,
        'h': Language.C,
        'lua': Language.LUA,
        'pl': Language.PERL,
        'pm': Language.PERL,
        'hs': Language.HASKELL,
        'lhs': Language.HASKELL,
        'ex': Language.ELIXIR,
        'exs': Language.ELIXIR,
        'ps1': Language.POWERSHELL,
        'psm1': Language.POWERSHELL,
        'psd1': Language.POWERSHELL,
    }
    if extension in map:
        return map[extension]
    return None

def split_code(code: str, max_length: int, min_length: int, overlap: int, language: Language):
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=language, 
        chunk_size=max_length, 
        chunk_overlap=overlap
    )
    chunks = splitter.split_text(code)
    return chunks

    
def get_question_history(question):
    history = []
    if question is None:
        return history

    while question.parent:
        history.append({
            'prompt': question.prompt,
            'question': question.question,
            'user_question': question.user_question,
            'answer': question.content,
        })
        question = question.parent

    history.append({
        'prompt': question.prompt,
        'question': question.question,
        'user_question': question.user_question,
        'answer': question.content,
    })

    history.reverse()
    return history


def get_tokens_from_openai_response(response):
    if response is None:
        log_error_with_stack('No response is given to calculate the tokens.')
        return 0, 0, 0
    
    try:
        return response.usage.prompt_tokens, response.usage.completion_tokens, response.usage.prompt_tokens_details.cached_tokens
    except Exception as e:
        log_error_with_stack(f'Error while getting the tokens from the response {e}.')
        return 0, 0, 0


def get_llm_usage(model_name, prompt_tokens, completion_tokens, cached_tokens=None):
    settings = get_default_settings()
    pricing = settings.pricings.get(model_name, {})
    if not pricing:
        logger.error(f"No pricing found for model {model_name}")
        return 0, 0, 0, 0

    if 'completion' in pricing:
        completion_cost = pricing.get('completion', 0) * completion_tokens
    else:
        logger.error(f"No completion cost found for model {model_name}")
        completion_cost = 0

    if cached_tokens is not None:
        if 'cached_prompt' in pricing:
            cached_prompt_cost = pricing.get('cached_prompt', 0) * cached_tokens
        else:
            if model_name.startswith('gpt'):
                logger.error(f"No cached prompt cost found for model {model_name}")
            cached_prompt_cost = 0
        
        prompt_tokens -= cached_tokens
    else:
        cached_prompt_cost = 0
        
    if 'prompt' in pricing:
        prompt_cost = pricing.get('prompt', 0) * prompt_tokens
    else:
        logger.error(f"No prompt cost found for model {model_name}")
        prompt_cost = 0
        
    total_cost = prompt_cost + completion_cost + cached_prompt_cost

    return total_cost

    
def get_question_depth(question):
    depth = 1
    
    if not question:
        return 0
    
    while question.parent:
        depth += 1
        question = question.parent
        
    return depth

    
    
def get_summary_generation_model():
    model = settings.SUMMARY_GENERATION_MODEL
    if model == 'gpt-4o-2024-08-06':
        return LLM_MODEL.OPENAI, 'gpt-4o-2024-08-06'
    elif model == 'gemini-1.5-flash-002':
        return LLM_MODEL.GEMINI, 'gemini-1.5-flash-002'
    else:
        raise ValueError(f"Invalid summary generation model: {model}")

def get_summary_question_generation_model():
    model = settings.SUMMARY_QUESTION_GENERATION_MODEL
    if model == 'gpt-4o-mini-2024-07-18':
        return LLM_MODEL.OPENAI, 'gpt-4o-mini-2024-07-18'
    elif model == 'gemini-1.5-flash-002':
        return LLM_MODEL.GEMINI, 'gemini-1.5-flash-002'
    else:
        raise ValueError(f"Invalid summary question generation model: {model}")

def summarize_text(text, guru_type):
    llm_model, model_name = get_summary_generation_model()
    if llm_model == LLM_MODEL.OPENAI:
        summary_response, usages = openai_requester.summarize_text(text, guru_type, model_name=model_name)
    elif llm_model == LLM_MODEL.GEMINI:
        summary_response, usages = GeminiRequester(model_name).summarize_text(text, guru_type)
        
    cleaned_summarization = re.sub(r'<METADATA>.*?</METADATA>', '', summary_response['summary'])
    return cleaned_summarization, model_name, usages, summary_response['summary_suitable'], summary_response['reasoning']

def generate_questions_from_summary(summary, guru_type):
    llm_model, model_name = get_summary_question_generation_model()
    if llm_model == LLM_MODEL.OPENAI:
        questions, usages = openai_requester.generate_questions_from_summary(summary, guru_type, model_name=model_name)
    elif llm_model == LLM_MODEL.GEMINI:
        questions, usages = GeminiRequester(model_name).generate_questions_from_summary(summary, guru_type)
        
    return questions, model_name, usages

def get_llm_usage_from_response(response, model):
    usages = {
        'prompt_tokens': 0,
        'completion_tokens': 0,
        'cached_prompt_tokens': 0,
        'cost_dollars': 0,
        'price_eval_success': True,
        'model': model
    }
    
    # OpenAI
    if model == 'gpt-4o-2024-08-06':
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        cached_prompt_tokens = response.usage.prompt_tokens_details.cached_tokens
    elif model == 'gpt-4o-mini-2024-07-18':
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        cached_prompt_tokens = response.usage.prompt_tokens_details.cached_tokens
    # Gemini
    elif model == 'gemini-1.5-flash-002':
        prompt_tokens = response.usage_metadata.prompt_token_count
        completion_tokens = response.usage_metadata.candidates_token_count
        cached_prompt_tokens = 0
    else:
        usages['price_eval_success'] = False
        return usages

    cost_dollars = get_llm_usage(model, prompt_tokens, completion_tokens, cached_prompt_tokens)
    usages['prompt_tokens'] = prompt_tokens
    usages['completion_tokens'] = completion_tokens
    usages['cost_dollars'] = cost_dollars
    usages['cached_prompt_tokens'] = cached_prompt_tokens
    return usages

    
def guru_type_has_enough_generated_questions(guru_type):
    total_generated = sum(
        len(gen.questions) 
        for gen in SummaryQuestionGeneration.objects.filter(guru_type=guru_type)
    )
    return total_generated >= settings.GENERATED_QUESTION_PER_GURU_LIMIT, total_generated


def get_root_summarization_of_guru_type(guru_type_slug):
    return Summarization.objects.filter(guru_type__slug=guru_type_slug, is_data_source_summarization=False, is_root=True).last()


def get_all_root_summarizations():
    return Summarization.objects.filter(is_data_source_summarization=False, is_root=True)

# Add this function after get_root_summarization_of_guru_type
def get_github_url_from_data_source(guru_type_slug):
    """
    Get the first GitHub URL from a guru type's data sources.
    
    Args:
        guru_type_slug: The slug of the guru type to search data sources for.
        
    Returns:
        str: The GitHub URL if found, None otherwise.
    """
    data_sources = DataSource.objects.filter(guru_type__slug=guru_type_slug, url__contains='github.com')
    if not data_sources.exists():
        logger.info(f'No github data source found for {guru_type_slug}')
        return None
    if data_sources.count() > 1:
        logger.error(f'Multiple github data sources found for {guru_type_slug}')
        return None
    return data_sources[0].url

def check_binge_auth(binge, user):
    if not binge:
        return True
    if settings.ENV == 'selfhosted':
        return True
    if user.is_admin:
        return True
    return binge.owner == user

def search_question(user, guru_type_object, binge, slug=None, question=None, will_check_binge_auth=True, include_api=False, only_widget=False):
    def get_source_conditions(user):
        """Helper function to get source conditions based on user"""
        if user is None:
            # For anonymous users
            # API requests are not allowed
            # Widget requests are allowed
            if only_widget:
                return Q(source__in=[Question.Source.WIDGET_QUESTION.value])
            else:
                return ~Q(source__in=[Question.Source.API.value, Question.Source.WIDGET_QUESTION.value])
        else:
            # For authenticated users:
            # API requests are allowed
            # Widget requests are not possible
            # Include non-API/WIDGET questions OR user's own API/WIDGET questions
            if user.is_admin:
                return Q()
            else:
                if include_api:
                    return (
                        ~Q(source__in=[Question.Source.API.value, Question.Source.WIDGET_QUESTION.value]) |
                        Q(source__in=[Question.Source.API.value], user=user)
                    )
                else:
                    return ~Q(source__in=[Question.Source.API.value, Question.Source.WIDGET_QUESTION.value])

    def search_question_by_slug(slug, guru_type_object, binge, source_conditions):
        if not slug:
            return None
        try:
            query = Question.objects.filter(source_conditions)
            if binge:
                return query.get(slug=slug, guru_type=guru_type_object, binge=binge)
            else:
                return query.get(slug=slug, guru_type=guru_type_object, binge=None)
        except Question.DoesNotExist:
            return None

    def search_question_by_question(question, guru_type_object, binge, source_conditions):
        if not question:
            return None
        try:
            question_lower = question.lower()
            query = Question.objects.annotate(
                question_lower=Lower('question'),
                user_question_lower=Lower('user_question')
            ).filter(
                source_conditions,
                Q(question_lower=question_lower) | Q(user_question_lower=question_lower),
                guru_type=guru_type_object
            )

            if binge:
                questions = query.filter(binge=binge)
            else:
                questions = query.filter(binge=None)

            questions = questions.order_by('-date_updated')
            
            if questions:
                return questions.first()
            raise Question.DoesNotExist
        except Question.DoesNotExist:
            return None

    if user and user.is_anonymous:
        user = None

    if will_check_binge_auth and binge and not check_binge_auth(binge, user):
        raise Exception('User does not have access to this binge')

    assert slug or question, 'Either slug or question must be provided'

    source_conditions = get_source_conditions(user)
    return search_question_by_slug(slug, guru_type_object, binge, source_conditions) or search_question_by_question(question, guru_type_object, binge, source_conditions)

def send_question_request_for_cloudflare_cache(question):
    try:
        res = requests.get(f"{settings.BASE_URL}/g/{question.guru_type.slug}/{question.slug}", timeout=10)
        res.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send request for Cloudflare cache for question {question.slug}: {str(e)}", exc_info=True)

def send_guru_type_request_for_cloudflare_cache(guru_type):
    try:
        res = requests.get(f"{settings.BASE_URL}/g/{guru_type.slug}", timeout=10)
        res.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send request for Cloudflare cache for guru type {guru_type.slug}: {str(e)}", exc_info=True)

def prepare_contexts_for_context_relevance(contexts):
    formatted_contexts = []
    
    for idx, context in enumerate(contexts):
        if 'question' in context:
            metadata = {
                "type": context['question']['entity']['metadata']['type'],
                "link": context['question']['entity']['metadata']['link'],
                "title": context['question']['entity']['metadata']['question']
            }
            
            formatted_text = context['question']['entity']['text']
            if 'accepted_answer' in context and context['accepted_answer']:
                formatted_text += f"\n\nAccepted Answer:\n{context['accepted_answer']['entity']['text']}"
            for other_answer in context['other_answers']:
                formatted_text += f"\n\nAnswer:\n{other_answer['entity']['text']}"
                
            
            formatted_contexts.append(f'<{context["prefix"]} context id="{idx+1}">\nContext {idx+1} Metadata:\n{metadata}\n\nContext {idx+1} Text:\n{formatted_text}\n</{context["prefix"]} context>\n\n--------\n\n')
        else:
            metadata = {
                "type": context["entity"]["metadata"]["type"],
                "link": context["entity"]["metadata"]["link"],
                "title": context["entity"]["metadata"]["title"]
            }
            formatted_contexts.append(f'<{context["prefix"]} context id="{idx+1}">\nContext {idx+1} Metadata:\n{metadata}\n\nContext {idx+1} Text:\n{context["entity"]["text"]}\n</{context["prefix"]} context>\n\n--------\n\n')

    return formatted_contexts

def log_error_with_stack(error_message):
    logger.error(f'{error_message}\nLast 4 functions: \n%s', '\n'.join(traceback.format_stack()[-4:]))

def clean_data_source_urls(urls):
    cleaned_urls = []
    for u in urls:
        # remove carriage return `\r` and newline `\n`
        url = u.replace('\r', '').replace('\n', '').strip()
        cleaned_urls.append(url)
    return cleaned_urls

def is_question_dirty(question: Question):
    """
    Check if the question is dirty by checking if the guru type is dirty (new data sources added or updated) or if a question reference has been deleted.

    Args:
        question: Question object
        
    Returns:
        bool: True if the question is dirty, False otherwise
    """
    
    def is_guru_dirty(guru_type: GuruType, question: Question):
        from django.db import models
        # Either new data sources are added or existing ones are updated AFTER the question is last answered
        
        # Get all data sources for the guru type
        data_sources = DataSource.objects.filter(guru_type=guru_type, status=DataSource.Status.SUCCESS)
        
        # If no data sources, guru is not dirty
        if not data_sources.exists():
            return False
            
        # Get the latest reindex date from data sources
        latest_reindex = data_sources.aggregate(latest=models.Max('last_reindex_date'))['latest']
        latest_created_date = data_sources.aggregate(latest=models.Max('date_created'))['latest']
        
        # If question was answered before the latest reindex or latest created date, it's dirty
        if (latest_reindex and question.date_updated < latest_reindex) or question.date_updated < latest_created_date:
            return True
            
        return False

    def is_question_reference_deleted(guru_type: GuruType, question: Question):
        data_source_references = []
        for reference in question.references:
            # Skip stackoverflow questions
            if reference['link'].startswith('https://stackoverflow.com'):
                continue
            data_source_references.append(reference['link'])
            
        # Compare reference['link'] with DataSource.url
        # First check DataSource urls
        data_sources = DataSource.objects.filter(url__in=data_source_references, guru_type=guru_type)
        found_urls = set(data_sources.values_list('url', flat=True))
        
        # Check remaining urls in GithubFile
        remaining_urls = set(data_source_references) - found_urls
        if remaining_urls:
            github_files = GithubFile.objects.filter(link__in=remaining_urls, data_source__guru_type=guru_type)
            found_urls.update(github_files.values_list('link', flat=True))

        # If any urls not found in either model, question is dirty
        if len(data_source_references) != len(found_urls):
            return True
        return False

    if question.binge:
        # Do not re-answer questions in binge
        return False

    return is_guru_dirty(question.guru_type, question) or is_question_reference_deleted(question.guru_type, question)

def handle_failed_root_reanswer(question_slug: str, guru_type_slug: str, user_question: str, question: str):
    """
    1- Notify the guru type maintainer
    2- Remove from sitemap (if it is on sitemap)
    
    Args:
        question_slug: Slug of the question
        guru_type_slug: Slug of the guru type
        user_question: User question
        question: Question
        
    Returns:
        None
    """

    def slack_send_outofcontext_question_notification(guru_type_slug: str, user_question: str, question: str, trust_score_threshold: float, was_on_sitemap: bool):
        payload = {"text": f":rotating_light: Re-answer failed due to lack of context\nGuru Type: {guru_type_slug}\nUser Question: {user_question}\nQuestion: {question}\nContext relevance threshold: {trust_score_threshold}\nWas on sitemap: {was_on_sitemap}"}
        if settings.SLACK_NOTIFIER_ENABLED:
            try:
                response = requests.post(settings.SLACK_NOTIFIER_WEBHOOK_URL, json=payload, timeout=30)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to send Slack notification for out of context question: {str(e)}", exc_info=True)
        else:
            logger.info(payload['text'])
        
    # Check if question exists in db
    question_obj = Question.objects.filter(slug=question_slug, guru_type__slug=guru_type_slug, binge=None)
    if not question_obj.exists():
        return

    question_obj = question_obj.first()

    # Notify the guru type maintainer
    def_settings = get_default_settings()
    slack_send_outofcontext_question_notification(guru_type_slug, user_question, question, def_settings.trust_score_threshold, question_obj.add_to_sitemap)

    # Remove from sitemap (if it is on sitemap)
    if question_obj.add_to_sitemap:
        question_obj.add_to_sitemap = False
        question_obj.sitemap_reason = f"Re-answer failed due to lack of context with threshold {def_settings.trust_score_threshold}"
        question_obj.sitemap_date = None
        question_obj.save()

    if question_obj.default_question:
        question_obj.default_question = False
        question_obj.save()


@dataclass
class APIAskResponse:
    """Response object for widget_ask function containing all possible return values"""
    content: Optional[Union[str, Generator]]  # Either direct content or stream generator
    error: Optional[str]                      # Error message if any
    question_obj: Optional[Question]                 # Question model instance if exists
    is_existing: bool                         # Whether this is an existing question

    @classmethod
    def from_existing(cls, question_obj: Question) -> 'APIAskResponse':
        """Create response for existing question"""
        return cls(
            content=question_obj.content,
            error=None,
            question_obj=question_obj,
            is_existing=True
        )

    @classmethod
    def from_stream(cls, stream_generator: Generator) -> 'APIAskResponse':
        """Create response for new streaming question"""
        return cls(
            content=stream_generator,
            error=None,
            question_obj=None,
            is_existing=False
        )

    @classmethod
    def from_error(cls, error_msg: str) -> 'APIAskResponse':
        """Create response for error case"""
        return cls(
            content=None,
            error=error_msg,
            question_obj=None,
            is_existing=False
        )

class APIType:
    API = 'API'
    WIDGET = 'WIDGET'
    DISCORD = 'DISCORD'
    SLACK = 'SLACK'

    @classmethod
    def is_api_type(cls, api_type: str) -> bool:
        return api_type in [cls.API, cls.DISCORD, cls.SLACK]

    @classmethod
    def get_question_source(cls, api_type: str) -> str:
        return {
            cls.WIDGET: Question.Source.WIDGET_QUESTION.value,
            cls.API: Question.Source.API.value,
            cls.DISCORD: Question.Source.DISCORD.value,
            cls.SLACK: Question.Source.SLACK.value,
        }[api_type]

def api_ask(question: str, 
            guru_type: GuruType, 
            binge: Binge | None, 
            parent: Question | None, 
            fetch_existing: bool, 
            api_type: APIType, 
            user: User | None) -> APIAskResponse:
    """
    API ask endpoint.
    It either returns the existing answer or streams the new one
    
    Args:
        question (str): The question to simulate the summary and answer for.
        guru_type (GuruType): The guru type to simulate the summary and answer for.
        binge (Binge): The binge to simulate the summary and answer for.
        parent (Question): The parent question.
        fetch_existing (bool): Whether to fetch the existing question data.
        api_type (APIType): The type of API call (WIDGET, API, DISCORD, SLACK).
        user (User): The user making the request.
    
    Returns:
        APIAskResponse: A dataclass containing all response information
    """

    is_widget = api_type == APIType.WIDGET
    is_api = APIType.is_api_type(api_type)

    if is_widget or api_type in [APIType.DISCORD, APIType.SLACK]:
        short_answer = True

    include_api = is_api
    only_widget = api_type == APIType.WIDGET

    question_source = APIType.get_question_source(api_type)

    if fetch_existing:
        # Only check for existing questions if not in a binge
        # Check if question exists without slug
        existing_question = search_question(
            user, 
            guru_type, 
            binge, 
            None, 
            question,
            will_check_binge_auth=False,
            include_api=include_api,
            only_widget=only_widget
        )
        if existing_question and not is_question_dirty(existing_question):
            logger.info(f"Found existing question {question} for guru type {guru_type.slug}")
            return APIAskResponse.from_existing(existing_question)

    # Get question summary and check with slug
    summary_data = get_question_summary(question, guru_type.slug, binge, short_answer=short_answer)
    if fetch_existing:
        # Only check for existing questions if not in a binge
        existing_question = search_question(
            user, 
            guru_type, 
            binge, 
            summary_data['question_slug'], 
            question,
            will_check_binge_auth=False,
            include_api=include_api,
            only_widget=only_widget
        )
        if existing_question and not is_question_dirty(existing_question):
            logger.info(f"Found existing question with slug for {question} in guru type {guru_type.slug}")
            return APIAskResponse.from_existing(existing_question)
    
    if 'valid_question' not in summary_data or not summary_data['valid_question']:
        return APIAskResponse.from_error(f"This question is not related to {guru_type.name}.")

    # Prepare summary data
    summary_prompt_tokens = summary_data.get('prompt_tokens', 0)
    summary_completion_tokens = summary_data.get('completion_tokens', 0)
    summary_cached_prompt_tokens = summary_data.get('cached_prompt_tokens', 0)
    user_intent = summary_data.get('user_intent', '')
    answer_length = summary_data.get('answer_length', '')
    default_settings = get_default_settings()

    if short_answer and answer_length > default_settings.widget_answer_max_length:
        # Double check just in case
        answer_length = default_settings.widget_answer_max_length
    
    user_question = summary_data['user_question']
    question_slug = summary_data['question_slug']
    description = summary_data['description']
    question = summary_data['question']

    question_slug += f'-{uuid.uuid4()}'

    try:
        # Get streaming response
        response, prompt, links, context_vals, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage = stream_question_answer(
            question, 
            guru_type.slug, 
            user_intent, 
            answer_length, 
            user_question,
            parent,
            user
        )

        if not response:
            logger.error(f"No response from the LLM for question {question} and guru type {guru_type.slug}.")
            return APIAskResponse.from_error(f"{guru_type.name} Guru doesn't have enough data as a source to generate a reliable answer for this question.")

        times = {'endpoint_start': time.time()}
        stream_generator = stream_and_save(
            user_question=user_question,
            question=question,
            guru_type=guru_type.slug,
            question_slug=question_slug,
            description=description,
            response=response,
            prompt=prompt,
            links=links,
            summary_completion_tokens=summary_completion_tokens,
            summary_prompt_tokens=summary_prompt_tokens,
            summary_cached_tokens=summary_cached_prompt_tokens,
            context_vals=context_vals,
            context_distances=context_distances,
            reranked_scores=reranked_scores,
            trust_score=trust_score,
            processed_ctx_relevances=processed_ctx_relevances,
            ctx_rel_usage=ctx_rel_usage,
            times=times,
            source=question_source,
            parent=parent,
            binge=binge,
            user=user
        )
    except Exception as e:
        logger.error(f"Error in api_ask: {str(e)}", exc_info=True)
        return APIAskResponse.from_error(f"There was an error in the stream. We are investigating the issue. Please try again later.")
    
    return APIAskResponse.from_stream(stream_generator)

def format_trust_score(trust_score: float) -> str:
    return int(trust_score * 100) if trust_score is not None else None

def format_date_updated(date_updated: datetime) -> str:
    return date_updated.strftime('%-d %B %Y') if date_updated else None

def format_references(references: list, api: bool = False) -> list:
    processed_references = []
    for reference in references:
        if 'question' in reference and 'link' in reference:
            processed_reference = reference.copy()
        else:
            processed_reference = {'question': '', 'link': reference}
        
        if 'stackoverflow.com' in processed_reference['link']:
            processed_reference['icon'] = "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/stackoverflow/stackoverflow-original.svg"
        elif 'youtube.com' in processed_reference['link']:
            processed_reference['icon'] = "https://s3.eu-central-1.amazonaws.com/anteon-strapi-cms-wuby8hpna3bdecoduzfibtrucp5x/youtube_dfa3f7b5b9.svg"
        elif processed_reference['link'].endswith('.pdf'):
            processed_reference['icon'] = settings.PDF_ICON_URL
        else:
            domain = urlparse(processed_reference['link']).netloc
            processed_reference['icon'] = get_website_icon(domain)

        processed_reference['question'] = html.unescape(processed_reference['question'])

        if api and 'question' in processed_reference:
            processed_reference['title'] = processed_reference['question']
            del processed_reference['question']

        processed_references.append(processed_reference)

    # Find all pdf files in references
    pdf_files = [reference['link'] for reference in processed_references if reference['link'].endswith('.pdf')]
    pdf_data_sources = DataSource.objects.filter(url__in=pdf_files)
    for pdf_data_source in pdf_data_sources:
        if pdf_data_source.private:
            for reference in processed_references:
                if reference['link'] == pdf_data_source.url:
                    # del reference['link']
                    reference['link'] = None
        else:
            if settings.ENV == 'selfhosted':
                reference['link'] = reference['link'].replace("/workspace/backend", "")

    return processed_references

def validate_binge_follow_up(parent_question: Question, binge: Binge | None, user: User | None):
    if not binge:
        return (True, None)

    history_depth = get_question_depth(parent_question) if parent_question else 0
    if history_depth + 1 > settings.FOLLOW_UP_QUESTION_LIMIT:
        logger.error(f'User {user.id} is trying to ask a follow up question after reaching the maximum number of follow-up questions ({settings.FOLLOW_UP_QUESTION_LIMIT})')
        return (False, f"You have reached the maximum number of follow-up questions ({settings.FOLLOW_UP_QUESTION_LIMIT})")

    last_binge_time = binge.last_used if binge else None
    # If more than 5 minutes have passed, reject the request
    if last_binge_time and (datetime.now(UTC) - last_binge_time).total_seconds() > settings.FOLLOW_UP_QUESTION_TIME_LIMIT_SECONDS:
        logger.error(f'User {user.id} is trying to ask a follow up question after {settings.FOLLOW_UP_QUESTION_TIME_LIMIT_SECONDS} seconds have passed since using the binge {binge.id}')
        return (False, f"You can't ask follow up questions after {settings.FOLLOW_UP_QUESTION_TIME_LIMIT_SECONDS} seconds have passed since using the binge.")

    return (True, None)


def create_binge_helper(guru_type: GuruType, user: User | None, root_question: Question):
    # Create binge with empty root question initially
    binge = Binge.objects.create(
        guru_type=guru_type,
        root_question=None,
        owner=user,
    )

    # Duplicate the root question by copying all fields
    root_question.pk = None  # This will create a new object on save
    root_question.binge = binge
    root_question.change_count = 0
    root_question.date_updated = datetime.now(UTC)
    root_question.date_created = datetime.now(UTC)
    root_question.add_to_sitemap = False
    root_question.sitemap_reason = "Binge root question"
    root_question.sitemap_date = None
    root_question.cost_dollars = 0
    root_question.completion_tokens = 0
    root_question.prompt_tokens = 0
    root_question.cached_prompt_tokens = 0
    root_question.latency_sec = 0
    root_question.llm_eval = False
    root_question.similarity_written_to_milvus = False
    root_question.parent = None
    root_question.user = user
    root_question.save()

    # Update binge with duplicated question as root
    binge.root_question = root_question
    binge.save()

    return binge

def create_fresh_binge(guru_type: GuruType, user: User | None):
    """
    Creates a new binge without requiring a root question.
    Args:
        guru_type: GuruType instance
        user: User instance or None
    Returns:
        Binge instance
    """
    binge = Binge.objects.create(
        guru_type=guru_type,
        owner=user
    )
    return binge

def validate_slug_existence(slug: str, guru_type_object: GuruType, binge: Binge):
    """
    For binge questions, we always create a new question with enumerated slug if needed

    Args:
        slug: Slug to validate
        guru_type_object: Guru type object
        binge: Binge object

    Returns:
        Validated slug
    """

    # For binge questions, we always create a new question with enumerated slug if needed
    base_slug = slug
    if Question.objects.filter(slug=base_slug, guru_type=guru_type_object, binge=binge).exists():
        # Find the largest enumeration for this slug
        similar_questions = Question.objects.filter(
            slug__regex=f"^{base_slug}(-\d+)?$",
            guru_type=guru_type_object,
            binge=binge
        ).values_list('slug', flat=True)
        
        max_enum = 0
        for slug in similar_questions:
            match = re.search(r'-(\d+)$', slug)
            if match:
                enum = int(match.group(1))
                max_enum = max(max_enum, enum)
        
        return f"{base_slug}-{max_enum + 1}"
    else:
        return base_slug

def prepare_prompt_for_context_relevance(cot: bool, guru_variables: dict) -> str:
    from core.prompts import (context_relevance_prompt, 
        context_relevance_cot_expected_output, 
        context_relevance_cot_output_format, 
        context_relevance_without_cot_expected_output, 
        context_relevance_without_cot_output_format)

    if cot:
        expected_output = context_relevance_cot_expected_output
        output_format = context_relevance_cot_output_format
    else:
        expected_output = context_relevance_without_cot_expected_output
        output_format = context_relevance_without_cot_output_format

    prompt = context_relevance_prompt.format(**guru_variables, expected_output=expected_output, output_format=output_format)
    return prompt

def string_to_boolean(value: str) -> bool:
    return value.lower() in ['true']

def format_github_repo_error(error: str) -> str:
    if error.startswith('No repository exists at this URL'):
        return error
    elif error.startswith('The codebase exceeds'):
        return error
    else:
        return 'Something went wrong. The team has been notified about the issue. You can also contact us on Discord.'