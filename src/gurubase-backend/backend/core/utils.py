from django.core.signing import Signer, BadSignature
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
from core.requester import GeminiEmbedder, GeminiRequester, OpenAIRequester, CloudflareRequester, get_openai_api_key, OllamaRequester
from PIL import Image
from core.models import DataSource, Binge
from accounts.models import User
from dataclasses import dataclass
from typing import Optional, Generator, Union, Dict
from django.db.models import Model, Q
from django.core.cache import caches
import hashlib
import pickle
from rest_framework.views import exception_handler
from rest_framework.exceptions import Throttled
from core.requester import GptSummary

logger = logging.getLogger(__name__)


def get_openai_client():
    """Get a fresh OpenAI client instance with the current API key"""
    return OpenAI(api_key=get_openai_api_key())

def get_cloudflare_requester():
    """Get a fresh CloudflareRequester instance"""
    return CloudflareRequester()

def get_openai_requester():
    """Get a fresh OpenAIRequester instance"""
    return OpenAIRequester()

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
        times, # Includes before_stream and summary
        reranked_scores, 
        trust_score, 
        processed_ctx_relevances, 
        ctx_rel_usage,
        enhanced_question,
        user=None,
        parent=None, 
        binge=None, 
        source=Question.Source.USER.value):
    
    start_total = time.perf_counter()
    times['total'] = 0
    times['stream_and_save'] = {
        'time_to_stream': 0,
        'processing_before_save': 0,
        'total': 0
    }
    
    start_stream = time.perf_counter()
    total_response = []
    chunks = []
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
    times['stream_and_save']['time_to_stream'] = time.perf_counter() - start_stream

    start_processing = time.perf_counter()
    prompt_tokens, completion_tokens, cached_prompt_tokens = get_tokens_from_openai_response(chunk)

    cost_dollars = get_llm_usage(settings.GPT_MODEL, prompt_tokens, completion_tokens, cached_prompt_tokens)
    
    guru_type_object = get_guru_type_object(guru_type)

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
    times['stream_and_save']['processing_before_save'] = time.perf_counter() - start_processing
    times['stream_and_save']['total'] = time.perf_counter() - start_total
    times['total'] = sum(time_dict.get('total', 0) for time_dict in times.values() if isinstance(time_dict, dict))

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
            question_obj.latency_sec = times['stream_and_save']['time_to_stream']
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
            question_obj.times = times
            question_obj.enhanced_question = enhanced_question
            question_obj.save()
            get_cloudflare_requester().purge_cache(guru_type, question_slug)
            
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
                latency_sec=times['stream_and_save']['time_to_stream'],
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
                llm_usages=llm_usages,
                times=times,
                enhanced_question=enhanced_question
            )
            question_obj.save()
    except Exception as e:
        logger.error(f'Error while saving question after stream. Arguments are: \nQuestion: {question}\nUser question: {user_question}\nSlug: {question_slug}\nGuru Type: {guru_type_object}\nBinge: {binge}', exc_info=True)
        raise e

    if binge:
        binge.save() # To update the last used field


class LLM_MODEL:
    OPENAI = 'openai'
    GEMINI = 'gemini'


def prepare_contexts(contexts, reranked_scores):
    references = {}
    formatted_contexts = []
    # The contexts are already sorted by their trust score
    
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

def merge_splits(milvus_client, text_embedding, code_embedding, fetched_doc, collection_name, link_key, link, code=False, merge_limit=None):
    # TODO: This does not have question / user question / enhanced question separation. It only uses the question.
    # Merge fetched doc with its other splits
    merged_text = {}
    used_indices = set()

    if merge_limit:
        # Get the closest vector's split_num (should be in fetched_doc)
        closest_split_num = fetched_doc['entity']['metadata'].get('split_num', 1)
        merged_text[closest_split_num] = fetched_doc['entity']['text']
        used_indices = {closest_split_num}

        # Determine potential adjacent indices
        adjacent_indices = [closest_split_num - 2, closest_split_num - 1, closest_split_num + 1, closest_split_num + 2]
        
        # Query for adjacent splits
        if adjacent_indices:
            adjacent_filter = " || ".join([f'metadata["split_num"] == {idx}' for idx in adjacent_indices if idx >= 0])
            if adjacent_filter:
                adjacent_results = milvus_client.search(
                    collection_name=collection_name,
                    data=[text_embedding if not code else code_embedding],
                    limit=4,  # Max number of adjacent splits we're looking for
                    output_fields=['text', 'metadata'],
                    filter=f'metadata["{link_key}"] == "{link}" && ({adjacent_filter})'
                )[0]

                adjacent_results.sort(key=lambda x: x['entity']['metadata'].get('split_num', 1))

                if len(adjacent_results) > 2:
                    adjacent_results = adjacent_results[1:3] # Get the middle to find the closest adjacents

                for result in adjacent_results:
                    split_num = result['entity']['metadata'].get('split_num', len(merged_text))
                    if split_num not in used_indices:
                        merged_text[split_num] = result['entity']['text']
                        used_indices.add(split_num)

        # Get additional non-adjacent splits (up to 3 more)
        exclude_filter = " && ".join([f'metadata["split_num"] != {idx}' for idx in used_indices])
        additional_results = milvus_client.search(
            collection_name=collection_name,
            data=[text_embedding if not code else code_embedding],
            limit=merge_limit - len(used_indices),
            output_fields=['text', 'metadata'],
            filter=f'metadata["{link_key}"] == "{link}" && ({exclude_filter})'
        )[0]

        for result in additional_results:
            split_num = result['entity']['metadata'].get('split_num', len(merged_text))
            if split_num not in used_indices:
                merged_text[split_num] = result['entity']['text']
                used_indices.add(split_num)
    else:
        results = milvus_client.search(
            collection_name=collection_name, 
            data=[text_embedding if not code else code_embedding], 
            limit=16384,
            output_fields=['text', 'metadata'], 
            filter=f'metadata["{link_key}"] == "{link}"'
        )[0]
        for result in results:
            split_num = result['entity']['metadata'].get('split_num', len(merged_text))
            merged_text[split_num] = result['entity']['text']
            used_indices.add(split_num)

    # Merge them in order with truncation indicators
    sorted_indices = sorted(merged_text.keys())
    merged_parts = []
    
    for i, idx in enumerate(sorted_indices):
        if i > 0 and sorted_indices[i] - sorted_indices[i-1] > 1:
            merged_parts.append("\n...truncated...\n")
        merged_parts.append(merged_text[idx])

    fetched_doc['entity']['text'] = '\n'.join(merged_parts)
    return fetched_doc


def vector_db_fetch(
    milvus_client, 
    collection_name, 
    question, 
    guru_type_slug, 
    user_question, 
    enhanced_question, 
    llm_eval=False):
    from core.models import GuruType
    guru_type = GuruType.objects.get(slug=guru_type_slug)

    times = {
        'total': 0,
        'embedding': 0,
        'stackoverflow': {
            'total': 0,
            'milvus_search': 0,
            'rerank': 0,
            'post_rerank': 0
        },
        'non_stackoverflow': {
            'total': 0,
            'milvus_search': 0,
            'rerank': 0,
            'post_rerank': 0
        },
        'github_repo': {
            'total': 0,
            'milvus_search': 0,
            'rerank': 0,
            'post_rerank': 0
        },
        'trust_score': 0
    }
    start_total = time.perf_counter()
    
    start_embedding = time.perf_counter()
    
    # Prepare texts to embed
    texts_to_embed = [question] # Assuming question is always present

    if user_question and len(user_question) < 300:
        texts_to_embed.append(user_question)
    else:
        text_embedding_user = None
        code_embedding_user = None

    if enhanced_question:
        texts_to_embed.append(enhanced_question)
    else:
        text_embedding_enhanced_question = None
        code_embedding_enhanced_question = None
    
    # Get all text and code embeddings in two batched calls
    embedding_start = time.perf_counter()
    text_embeddings = embed_texts_with_model(texts_to_embed, guru_type.text_embedding_model)

    embedding_start = time.perf_counter()
    code_embeddings = embed_texts_with_model(texts_to_embed, guru_type.code_embedding_model)

    times['embedding'] = time.perf_counter() - embedding_start
    
    # Unpack the embeddings
    text_embedding = text_embeddings[0]
    code_embedding = code_embeddings[0]
    
    # Get user question embeddings if available
    if user_question and len(user_question) < 300:
        text_embedding_user = text_embeddings[1]
        code_embedding_user = code_embeddings[1]

    # Get enhanced question embeddings if available
    if enhanced_question:
        text_embedding_enhanced_question = text_embeddings[-1]
        code_embedding_enhanced_question = code_embeddings[-1]

    times['embedding'] = time.perf_counter() - start_embedding

    # Get collection name and dimension for text embedding model
    _, text_dimension = get_embedding_model_config(guru_type.text_embedding_model)
    code_collection_name, code_dimension = get_embedding_model_config(guru_type.code_embedding_model)
    text_collection_name = guru_type.milvus_collection_name
    
    all_docs = {}
    search_params = None


    def fetch_and_merge_answers(question_id):
        # First, fetch only the first split of each answer
        answer_first_splits = milvus_client.search(
            collection_name=text_collection_name,
            data=[text_embedding],
            limit=16384,
            output_fields=['text', 'metadata'],
            filter=f'metadata["question_id"] == {question_id} and metadata["type"] == "answer" and metadata["split_num"] == 1'
        )[0]
        
        merged_answers = []
        for answer_first_split in answer_first_splits:
            link = answer_first_split['entity']['metadata']['link']
            merged_answer = merge_splits(milvus_client, text_embedding, code_embedding, answer_first_split, text_collection_name, 'link', link, code=False)
            merged_answers.append(merged_answer)
        
        return merged_answers

    def rerank_batch(batch, question, user_question, enhanced_question, llm_eval):
        if settings.ENV == 'selfhosted':
            # Do not rerank in selfhosted
            return [i for i in range(len(batch))], [1 for _ in range(len(batch))]
        batch_texts = [result['entity']['text'] for result in batch]
        
        # Rerank with question
        reranked_batch_question = rerank_texts(question, batch_texts)
        
        # Rerank with user_question if it's not too long
        reranked_batch_user_question = None
        if user_question and len(user_question) < 300:
            reranked_batch_user_question = rerank_texts(user_question, batch_texts)
        
        # Rerank with enhanced_question
        reranked_batch_enhanced_question = rerank_texts(enhanced_question, batch_texts)
        
        # If all reranking fails, use original order
        if reranked_batch_question is None and reranked_batch_user_question is None and reranked_batch_enhanced_question is None:
            logger.warning(f'All reranking methods failed for the batch. Using original order.')
            reranked_batch_indices = [i for i in range(len(batch_texts))]
            reranked_batch_scores = [0 for _ in range(len(batch_texts))]
        else:
            # Track indices and their highest scores
            index_to_score = {}
            
            # Process results in order of priority (user_question > enhanced_question > question)
            # For each reranking result, update the score if it's higher than what we've seen
            
            # 1. Process user_question results if available (highest priority)
            if reranked_batch_user_question:
                for result in reranked_batch_user_question:
                    idx = result['index']
                    score = result['score']
                    index_to_score[idx] = score  # Always take user_question score as it has highest priority
            
            # 2. Process enhanced_question results
            if reranked_batch_enhanced_question:
                for result in reranked_batch_enhanced_question:
                    idx = result['index']
                    score = result['score']
                    # Update score if it's higher than what we've seen
                    if idx not in index_to_score or score > index_to_score[idx]:
                        index_to_score[idx] = score
            
            # 3. Process question results
            if reranked_batch_question:
                for result in reranked_batch_question:
                    idx = result['index']
                    score = result['score']
                    # Update score if it's higher than what we've seen
                    if idx not in index_to_score or score > index_to_score[idx]:
                        index_to_score[idx] = score
            
            # Convert the map back to ordered lists
            # Sort by score in descending order to maintain priority
            sorted_items = sorted(index_to_score.items(), key=lambda x: x[1], reverse=True)
            reranked_batch_indices = [idx for idx, _ in sorted_items]
            reranked_batch_scores = [score for _, score in sorted_items]

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
            
        start_so = time.perf_counter()
        start_milvus = time.perf_counter()
        
        batch = milvus_client.search(
            collection_name=text_collection_name,
            data=[text_embedding],
            limit=20,
            output_fields=['id', 'text', 'metadata'],
            filter='metadata["type"] in ["question", "answer"]',
            search_params=search_params
        )[0]
        times['stackoverflow']['milvus_search'] = time.perf_counter() - start_milvus

        if text_embedding_user:
            user_question_batch = milvus_client.search(
                collection_name=text_collection_name,
                data=[text_embedding_user],
                limit=10,
                output_fields=['id', 'text', 'metadata'],
                filter='metadata["type"] in ["question", "answer"]',
                search_params=search_params
            )[0]
        else:
            user_question_batch = []

        # Add unique user question retrievals
        final_user_question_docs_without_duplicates = []
        for doc in user_question_batch:
            if doc["id"] not in [doc["id"] for doc in batch]:
                final_user_question_docs_without_duplicates.append(doc)

        batch = batch + final_user_question_docs_without_duplicates

        if text_embedding_enhanced_question:
            enhanced_question_batch = milvus_client.search(
                collection_name=text_collection_name,
                data=[text_embedding_enhanced_question],
                limit=10,
                output_fields=['id', 'text', 'metadata'],
                filter='metadata["type"] in ["question", "answer"]',
                search_params=search_params
            )[0]
        else:
            enhanced_question_batch = []

        for doc in enhanced_question_batch:
            if doc["id"] not in [doc["id"] for doc in batch]:
                batch.append(doc)

        times['stackoverflow']['milvus_search'] = time.perf_counter() - start_milvus

        start_rerank = time.perf_counter()
        reranked_batch_indices, reranked_batch_scores = rerank_batch(batch, question, user_question, enhanced_question, llm_eval)
        times['stackoverflow']['rerank'] = time.perf_counter() - start_rerank

        start_post_rerank = time.perf_counter()
        for index, score in zip(reranked_batch_indices, reranked_batch_scores):
            if len(stackoverflow_sources) >= 3:
                break
            
            try:
                question_title = batch[index]['entity']['metadata']['question']
                question_id = batch[index]['entity']['metadata']['question_id']
                if question_title not in stackoverflow_sources:
                    # Try to fetch the question
                    milvus_question = milvus_client.search(
                        collection_name=text_collection_name,
                        data=[text_embedding],
                        limit=1,
                        output_fields=['text', 'metadata'],
                        filter=f'metadata["question_id"] == {question_id} and metadata["type"] == "question"'
                    )[0]
                    
                    # Try to fetch the accepted answer
                    accepted_answer = milvus_client.search(
                        collection_name=text_collection_name,
                        data=[text_embedding],
                        limit=1,
                        output_fields=['text', 'metadata'],
                        filter=f'metadata["question_id"] == {question_id} and metadata["type"] == "answer" and metadata["is_accepted"] == True'
                    )[0]

                    if not accepted_answer:
                        # If accepted answer is not found with is_accepted key, try with accepted key for old collections. is_accepted is the new key.
                        accepted_answer = milvus_client.search(
                            collection_name=text_collection_name,
                            data=[text_embedding],
                            limit=1,
                            output_fields=['text', 'metadata'],
                            filter=f'metadata["question_id"] == {question_id} and metadata["type"] == "answer" and metadata["accepted"] == True'
                        )[0]
                    
                    # Only proceed if both question and accepted answer are found
                    if milvus_question and accepted_answer:
                        question_link = milvus_question[0]['entity']['metadata']['link']
                        accepted_answer_link = accepted_answer[0]['entity']['metadata']['link']
                        stackoverflow_sources[question_title] = {
                            "question": merge_splits(milvus_client, text_embedding, code_embedding, milvus_question[0], text_collection_name, 'link', question_link, code=False),
                            "accepted_answer": merge_splits(milvus_client, text_embedding, code_embedding, accepted_answer[0], text_collection_name, 'link', accepted_answer_link, code=False),
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
        times['stackoverflow']['post_rerank'] = time.perf_counter() - start_post_rerank
        times['stackoverflow']['total'] = time.perf_counter() - start_so
        return list(stackoverflow_sources.values()), reranked_scores

    def fetch_non_stackoverflow_sources():
        non_stackoverflow_sources = []
        reranked_scores = []
        question_milvus_limit = 20
        user_question_milvus_limit = 10
        enhanced_question_milvus_limit = 10
        if settings.ENV == 'selfhosted':
            question_milvus_limit = 3
            user_question_milvus_limit = 3
            enhanced_question_milvus_limit = 3
            
        start_non_so = time.perf_counter()
        start_milvus = time.perf_counter()
        
        batch = milvus_client.search(
            collection_name=text_collection_name,
            data=[text_embedding],
            limit=question_milvus_limit,
            output_fields=['id', 'text', 'metadata'],
            filter='metadata["type"] not in ["question", "answer", "comment"]',
            search_params=search_params
        )[0]
        times['non_stackoverflow']['milvus_search'] = time.perf_counter() - start_milvus
        

        if text_embedding_user:
            user_question_batch = milvus_client.search(
                collection_name=text_collection_name,
                data=[text_embedding_user],
                limit=user_question_milvus_limit,
                output_fields=['id', 'text', 'metadata'],
                filter='metadata["type"] not in ["question", "answer", "comment"]',
                search_params=search_params
            )[0]
        else:
            user_question_batch = []

        # Add unique user question retrievals
        final_user_question_docs_without_duplicates = []
        for doc in user_question_batch:
            if doc["id"] not in [doc["id"] for doc in batch]:
                final_user_question_docs_without_duplicates.append(doc)

        batch = batch + final_user_question_docs_without_duplicates

        if text_embedding_enhanced_question:
            enhanced_question_batch = milvus_client.search(
                collection_name=text_collection_name,
                data=[text_embedding_enhanced_question],
                limit=enhanced_question_milvus_limit,
                output_fields=['id', 'text', 'metadata'],
                filter='metadata["type"] not in ["question", "answer", "comment"]',
                search_params=search_params
            )[0]
        else:
            enhanced_question_batch = []

        for doc in enhanced_question_batch:
            if doc["id"] not in [doc["id"] for doc in batch]:
                batch.append(doc)

        times['non_stackoverflow']['milvus_search'] = time.perf_counter() - start_milvus

        start_rerank = time.perf_counter()
        reranked_batch_indices, reranked_batch_scores = rerank_batch(batch, question, user_question, enhanced_question, llm_eval)
        times['non_stackoverflow']['rerank'] = time.perf_counter() - start_rerank

        start_post_rerank = time.perf_counter()
        for index, score in zip(reranked_batch_indices, reranked_batch_scores):
            if len(non_stackoverflow_sources) >= 3:
                break
            
            try:
                link = batch[index]['entity']['metadata'].get('link') or batch[index]['entity']['metadata'].get('url')
                if link and link not in [doc['entity']['metadata'].get('link') or doc['entity']['metadata'].get('url') for doc in non_stackoverflow_sources]:
                    merged_doc = merge_splits(milvus_client, text_embedding, code_embedding, batch[index], text_collection_name, 'link' if 'link' in batch[index]['entity']['metadata'] else 'url', link, code=False, merge_limit=6)
                    non_stackoverflow_sources.append(merged_doc)
                    reranked_scores.append({'link': link, 'score': score})
            except Exception as e:
                logger.error(f'Error while fetching non stackoverflow sources: {e}', exc_info=True)
        times['non_stackoverflow']['post_rerank'] = time.perf_counter() - start_post_rerank
        times['non_stackoverflow']['total'] = time.perf_counter() - start_non_so
        return non_stackoverflow_sources, reranked_scores

    def fetch_github_repo_sources():
        github_repo_sources = []
        reranked_scores = []
        question_milvus_limit = 20
        user_question_milvus_limit = 10
        enhanced_question_milvus_limit = 10
        if settings.ENV == 'selfhosted':
            question_milvus_limit = 3
            user_question_milvus_limit = 3
            
        start_github = time.perf_counter()
        start_milvus = time.perf_counter()
        
        batch = milvus_client.search(
            collection_name=code_collection_name,
            data=[code_embedding],
            limit=question_milvus_limit,
            output_fields=['id', 'text', 'metadata'],
            filter=f'guru_slug == "{guru_type_slug}"',
            search_params=search_params
        )[0]
        times['github_repo']['milvus_search'] = time.perf_counter() - start_milvus
        
        if code_embedding_user:
            user_question_batch = milvus_client.search(
                collection_name=code_collection_name,
                data=[code_embedding_user],
                limit=user_question_milvus_limit,
                output_fields=['id', 'text', 'metadata'],
                filter=f'guru_slug == "{guru_type_slug}"',
                search_params=search_params
            )[0]
        else:
            user_question_batch = []

        # Add unique user question retrievals
        final_user_question_docs_without_duplicates = []
        for doc in user_question_batch:
            if doc["id"] not in [doc["id"] for doc in batch]:
                final_user_question_docs_without_duplicates.append(doc)

        batch = batch + final_user_question_docs_without_duplicates

        if text_embedding_enhanced_question:
            enhanced_question_batch = milvus_client.search(
                collection_name=code_collection_name,
                data=[code_embedding_enhanced_question],
                limit=enhanced_question_milvus_limit,
                output_fields=['id', 'text', 'metadata'],
                filter=f'guru_slug == "{guru_type_slug}"',
                search_params=search_params                
            )[0]
        else:
            enhanced_question_batch = []

        for doc in enhanced_question_batch:
            if doc["id"] not in [doc["id"] for doc in batch]:
                batch.append(doc)

        times['github_repo']['milvus_search'] = time.perf_counter() - start_milvus

        start_rerank = time.perf_counter()
        reranked_batch_indices, reranked_batch_scores = rerank_batch(batch, question, user_question, enhanced_question, llm_eval)
        times['github_repo']['rerank'] = time.perf_counter() - start_rerank

        start_post_rerank = time.perf_counter()
        for index, score in zip(reranked_batch_indices, reranked_batch_scores):
            if len(github_repo_sources) >= 5:
                break
            
            try:
                link = batch[index]['entity']['metadata'].get('link') or batch[index]['entity']['metadata'].get('url')
                if link and link not in [doc['entity']['metadata'].get('link') or doc['entity']['metadata'].get('url') for doc in github_repo_sources]:
                    merged_doc = merge_splits(milvus_client, text_embedding, code_embedding, batch[index], code_collection_name, 'link', link, code=True, merge_limit=6)
                    github_repo_sources.append(merged_doc)
                    reranked_scores.append({'link': link, 'score': score})
            except Exception as e:
                logger.error(f'Error while fetching non stackoverflow sources: {e}', exc_info=True)
        times['github_repo']['post_rerank'] = time.perf_counter() - start_post_rerank
        times['github_repo']['total'] = time.perf_counter() - start_github
        return github_repo_sources, reranked_scores        

    def filter_by_trust_score(contexts, reranked_scores, question, user_question, enhanced_question, guru_type_slug):
        context_relevance, ctx_rel_usage, prompt, user_prompt = get_openai_requester().get_context_relevance(question, user_question, enhanced_question, guru_type_slug, contexts, cot=False)
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
        
        # Create a list of tuples containing (context, reranked_score, trust_score) for sorting
        context_data = []
        for i, ctx in enumerate(context_relevance['contexts']):
            ctx['context'] = formatted_contexts[i]
            if ctx['score'] >= default_settings.trust_score_threshold:
                context_data.append((contexts[i], reranked_scores[i], ctx['score']))
                processed_ctx_relevances['kept'].append(ctx)
            else:
                processed_ctx_relevances['removed'].append(ctx)

        # Sort context_data by trust score in descending order
        context_data.sort(key=lambda x: x[2], reverse=True)

        # Unpack the sorted data
        for context, reranked_score, score in context_data:
            filtered_contexts.append(context)
            filtered_reranked_scores.append(reranked_score)
            trust_score += score

        trust_score = trust_score / len(filtered_contexts) if filtered_contexts else 0

        return filtered_contexts, filtered_reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage

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
    start_trust_score = time.perf_counter()
    filtered_contexts, filtered_reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage = filter_by_trust_score(contexts, reranked_scores, question, user_question, enhanced_question, guru_type_slug)
    times['trust_score'] = time.perf_counter() - start_trust_score
    
    return filtered_contexts, filtered_reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage, times


def get_contexts(
    milvus_client, 
    collection_name, 
    question, 
    guru_type_slug, 
    user_question, 
    enhanced_question):
    times = {
        'vector_db_fetch': {},
        'prepare_contexts': 0,
        'context_distances_processing': 0
    }
    
    try:
        contexts, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage, vector_db_times = vector_db_fetch(
            milvus_client, 
            collection_name, 
            question, 
            guru_type_slug, 
            user_question, 
            enhanced_question)
        times['vector_db_fetch'] = vector_db_times
    except Exception as e:
        logger.error(f'Error while fetching the context from the vector database: {e}', exc_info=True)
        contexts = []
        reranked_scores = []

    # if contexts == [] and settings.ENV == 'production':
    #     raise exceptions.InvalidRequestError({'msg': 'No context found for the question.'})

    logger.debug(f'Contexts: {contexts}')
    
    start_prepare_contexts = time.perf_counter()
    context_vals, links = prepare_contexts(contexts, reranked_scores)
    times['prepare_contexts'] = time.perf_counter() - start_prepare_contexts
    
    start_context_distances = time.perf_counter()
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
    times['context_distances_processing'] = time.perf_counter() - start_context_distances
    
    return context_vals, links, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage, times

    
def parse_summary_response(question, response):
    try:
        prompt_tokens, completion_tokens, cached_prompt_tokens = get_tokens_from_openai_response(response)
        if response.choices[0].message.refusal:
            answer = GptSummary(question=question, user_question=question, question_slug='', answer="An error occurred while processing the question. Please try again.", description="", valid_question=False, enhanced_question=[])
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
                'enhanced_question': '',
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
            'enhanced_question': '',
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
        'enhanced_question': gptSummary.enhanced_question,
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


def get_github_details_if_applicable(guru_type):
    guru_type_obj = get_guru_type_object(guru_type)
    response = ""
    if guru_type_obj and guru_type_obj.github_details:
        try:
            simplified_github_details = {}
            github_details = guru_type_obj.github_details
            simplified_github_details['name'] = github_details.get('name', '')
            simplified_github_details['description'] = github_details.get('description', '')
            simplified_github_details['topics'] = github_details.get('topics', [])
            simplified_github_details['language'] = github_details.get('language', '')
            simplified_github_details['size'] = github_details.get('size', 0)
            simplified_github_details['homepage'] = github_details.get('homepage', '')
            simplified_github_details['stargazers_count'] = github_details.get('stargazers_count', 0)
            simplified_github_details['forks_count'] = github_details.get('forks_count', 0)
            # Handle null license case
            license_info = github_details.get('license')
            simplified_github_details['license_name'] = license_info.get('name', '') if license_info else ''
            simplified_github_details['open_issues_count'] = github_details.get('open_issues_count', 0)
            simplified_github_details['pushed_at'] = github_details.get('pushed_at', '')
            simplified_github_details['created_at'] = github_details.get('created_at', '')
            owner = github_details.get('owner', {})
            simplified_github_details['owner_login'] = owner.get('login', '')
            response = f"Here is the GitHub details for {guru_type_obj.name}: {simplified_github_details}"
        except Exception as e:
            logger.error(f"Error while processing GitHub details for guru type {guru_type}: {str(e)}")
            response = ""
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


def ask_question_with_stream(
    milvus_client, 
    collection_name, 
    question, 
    guru_type, 
    user_intent, 
    answer_length, 
    user_question, 
    parent_question, 
    source,
    enhanced_question,
    user=None,
    github_comments: list | None = None):
    from core.prompts import github_context_template
    from core.github.app_handler import GithubAppHandler

    start_total = time.perf_counter()
    times = {
        'total': 0,
        'get_contexts': {},
        'get_question_history': 0,
        'prepare_chat_messages': 0,
        'chatgpt_completion': 0
    }

    default_settings = get_default_settings()
    start_get_contexts = time.perf_counter()
    context_vals, links, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage, get_contexts_times = get_contexts(milvus_client, collection_name, question, guru_type, user_question, enhanced_question)
    times['get_contexts'] = get_contexts_times
    times['get_contexts']['total'] = time.perf_counter() - start_get_contexts

    github_context = ""
    if github_comments:
        comment_contexts = GithubAppHandler().format_comments_for_prompt(github_comments)
        github_context = github_context_template.format(github_comments=comment_contexts)

    if not reranked_scores:
        OutOfContextQuestion.objects.create(
            question=question, 
            guru_type=get_guru_type_object(guru_type), 
            user_question=user_question, 
            rerank_threshold=default_settings.rerank_threshold, 
            trust_score_threshold=default_settings.trust_score_threshold, 
            processed_ctx_relevances=processed_ctx_relevances, 
            source=source,
            enhanced_question=enhanced_question
        )

        times['total'] = time.perf_counter() - start_total
        return None, None, None, None, None, None, None, None, None, times

    simplified_github_details = get_github_details_if_applicable(guru_type)

    guru_variables = get_guru_type_prompt_map(guru_type)
    guru_variables['streaming_type']='streaming'
    guru_variables['date'] = datetime.now().strftime("%Y-%m-%d")
    guru_variables['user_intent'] = user_intent
    guru_variables['answer_length'] = answer_length
    guru_variables['github_details_if_applicable'] = simplified_github_details
    guru_variables['github_context'] = github_context

    start_history = time.perf_counter()
    history = get_question_history(parent_question)
    times['get_question_history'] = time.perf_counter() - start_history

    start_prepare_messages = time.perf_counter()
    messages = prepare_chat_messages(user_question, question, guru_variables, context_vals, history)
    times['prepare_chat_messages'] = time.perf_counter() - start_prepare_messages
    
    used_prompt = messages[0]['content']

    start_chatgpt = time.perf_counter()
    response = get_openai_requester().ask_question_with_stream(messages)
    times['chatgpt_completion'] = time.perf_counter() - start_chatgpt
    times['total'] = time.perf_counter() - start_total

    if settings.LOG_STREAM_TIMES:
        logger.info(f'Times: {times}')

    return response, used_prompt, links, context_vals, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage, times

def get_summary(question, guru_type, short_answer=False, github_comments: list | None = None):
    times = {
        'total': 0,
        'prompt_prep': 0,
        'response_await': 0
    }
    start_total = time.perf_counter()
    start_prompt_prep = time.perf_counter()
    from core.prompts import summary_template, summary_short_answer_addition, summary_addition, github_context_template
    from core.github.app_handler import GithubAppHandler
    context_variables = get_guru_type_prompt_map(guru_type)
    context_variables['date'] = datetime.now().strftime("%Y-%m-%d")
    default_settings = get_default_settings()
    if short_answer:
        # Slack only
        summary_addition = summary_short_answer_addition.format(widget_answer_max_length=default_settings.widget_answer_max_length)
    else:
        summary_addition = summary_addition

    github_context = ""
    if github_comments:
        comment_contexts = GithubAppHandler().format_comments_for_prompt(github_comments)
        github_context = github_context_template.format(github_comments=comment_contexts)

    prompt = summary_template.format(
        **context_variables, 
        summary_addition=summary_addition,
        github_context=github_context
    )

    if guru_type.lower() not in question.lower():
        guru_type_obj = get_guru_type_object(guru_type)
        question = f"{guru_type_obj.name} - {question}"

    times['prompt_prep'] = time.perf_counter() - start_prompt_prep

    start_response_await = time.perf_counter()
    try:
        response = get_openai_requester().get_summary(prompt, question)
        times['response_await'] = time.perf_counter() - start_response_await
    except Exception as e:
        logger.error(f'Error while getting summary: {question}. Exception: {e}', exc_info=True)
        times['total'] = time.perf_counter() - start_total
        return None, times

    times['total'] = time.perf_counter() - start_total
    return response, times


def get_question_summary(question: str, guru_type: str, binge: Binge, short_answer: bool = False, github_comments: list | None = None):
    times = {
        'total': 0,
    }
    start_total = time.perf_counter()

    response, get_summary_times = get_summary(question, guru_type, short_answer, github_comments)
    times['get_summary'] = get_summary_times

    start_parse_summary_response = time.perf_counter()
    parsed_response = parse_summary_response(question, response)
    times['parse_summary_response'] = time.perf_counter() - start_parse_summary_response

    if binge:
        parsed_response['question_slug'] = f'{parsed_response["question_slug"]}-{uuid.uuid4()}'
    times['total'] = time.perf_counter() - start_total

    return parsed_response, times


def stream_question_answer(
        question, 
        guru_type, 
        user_intent, 
        answer_length, 
        user_question, 
        source,
        enhanced_question,
        parent_question=None,
        user=None,
        github_comments: list | None = None
    ):
    guru_type_obj = get_guru_type_object(guru_type)
    collection_name = guru_type_obj.milvus_collection_name
    milvus_client = get_milvus_client()

    response, prompt, links, context_vals, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage, times = ask_question_with_stream(
        milvus_client, 
        collection_name, 
        question, 
        guru_type, 
        user_intent, 
        answer_length, 
        user_question, 
        parent_question,
        source,
        enhanced_question,
        user,
        github_comments
    )
    if not response:
        return None, None, None, None, None, None, None, None, None, times

    return response, prompt, links, context_vals, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage, times

def validate_guru_type(guru_type, only_active=True):
    if guru_type not in get_guru_type_names(only_active=only_active):
        raise exceptions.InvalidRequestError({'msg': 'Guru type is invalid.'})


class SeoFriendlyTitleAnswer(BaseModel):
    seo_frienly_title: str

def get_more_seo_friendly_title(title):
    # Obsolete
    from core.prompts import seo_friendly_title_template
    prompt = seo_friendly_title_template.format(question=title)

    response = get_openai_client().beta.chat.completions.parse(
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


def embed_text(text):
    # Get default embedding model from Settings
    model_choice = Settings.get_default_embedding_model()
    return embed_text_with_model(text, model_choice)

def embed_texts(texts):
    # Get default embedding model from Settings
    model_choice = Settings.get_default_embedding_model()
    return embed_texts_with_model(texts, model_choice)


def rerank_texts(query, texts):
    # Using BAAI/bge-reranker-large model for reranking
    # This model's input size is limited to 512 tokens and batch size limited to 32
    # We will try to rerank the results in batches
    max_limits = [1300, 1200, 1000, 800, 500, 100]
    url = settings.RERANK_API_URL
    headers = {"Content-Type": "application/json"}
    if settings.RERANK_API_KEY:
        headers["Authorization"] = f"Bearer {settings.RERANK_API_KEY}"

    BATCH_SIZE = 32
    all_results = []
    
    # Process texts in batches of 32
    for batch_start in range(0, len(texts), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(texts))
        batch_texts = texts[batch_start:batch_end]
        batch_results = None
        
        # Try with original query first
        for limit in max_limits:
            truncated_texts = [text[:limit] for text in batch_texts]
            data = json.dumps({"query": query, "texts": truncated_texts})
            
            try:
                response = requests.post(url, headers=headers, data=data, timeout=30)
            except Exception as e:
                logger.error(f'Reranking: Error while reranking the batch {batch_start}-{batch_end}: {[text[:100] for text in batch_texts]}. Response: {e}. Url: {url}')
                continue  # Try with a smaller limit instead of returning None immediately
            
            if response.status_code == 200:
                batch_results = response.json()
                break
            
            if response.reason == "Payload Too Large" and response.status_code == 413:
                # '{"error":"Input validation error: `inputs` must have less than 512 tokens. Given: 565","error_type":"Validation"}'
                logger.warning(f'Reranking: Text is too long for limit {limit}. Trying again with new limit. Question: {query}')
                continue
        
        # If all limits failed with original query, try with shorter query
        if batch_results is None and len(query) > 200:
            short_query = query[:200]
            logger.warning(f'Reranking: Trying with shortened query for batch {batch_start}-{batch_end}. Original length: {len(query)}, new length: 200')
            
            for limit in max_limits:
                truncated_texts = [text[:limit] for text in batch_texts]
                data = json.dumps({"query": short_query, "texts": truncated_texts})
                
                try:
                    response = requests.post(url, headers=headers, data=data, timeout=30)
                except Exception as e:
                    logger.error(f'Reranking: Error while reranking with shortened query: {e}. Url: {url}')
                    continue
                
                if response.status_code == 200:
                    batch_results = response.json()
                    break
                
                if response.reason == "Payload Too Large" and response.status_code == 413:
                    logger.warning(f'Reranking: Text is too long for limit {limit} with shortened query. Trying again with new limit.')
                    continue
        
        if batch_results is None:
            logger.error(f'Reranking: Tried all the limits for batch {batch_start}-{batch_end}. Error while reranking the batch: {[text[:100] for text in batch_texts]}. Response: {response.text if "response" in locals() else "No response"}. Url: {url}')
            return None
        
        # Adjust indices to be relative to the full list
        for result in batch_results:
            result['index'] += batch_start
        
        all_results.extend(batch_results)
    
    # Sort results by score to maintain the same behavior as before
    all_results.sort(key=lambda x: x['score'], reverse=True)
    return all_results


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

def create_guru_type_object(slug, name, intro_text, domain_knowledge, icon_url, stackoverflow_tag, stackoverflow_source, github_repos, maintainer=None):
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
        github_repos=github_repos,
        active=active
    )
    if maintainer:
        guru_type.maintainers.add(maintainer)
    return guru_type

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

    summary_data, _ = get_question_summary(question, guru_type.slug, None, short_answer=False)
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
    enhanced_question = summary_data.get('enhanced_question', [])

    response, prompt, links, context_vals, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage, times = stream_question_answer(
        question, 
        guru_type.slug, 
        user_intent, 
        answer_length, 
        user_question,
        source,
        enhanced_question
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
        log_error_with_stack('No chunk is given to calculate the tokens. Will find the last one.')
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
            question_obj.times = times
            question_obj.enhanced_question = enhanced_question
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
                llm_usages=llm_usages,
                times=times,
                enhanced_question=enhanced_question
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
        return response.usage.prompt_tokens, response.usage.completion_tokens, response.usage.prompt_tokens_details.cached_tokens if response.usage.prompt_tokens_details else 0
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
        summary_response, usages = get_openai_requester().summarize_text(text, guru_type, model_name=model_name)
    elif llm_model == LLM_MODEL.GEMINI:
        summary_response, usages = GeminiRequester(model_name).summarize_text(text, guru_type)
        
    cleaned_summarization = re.sub(r'<METADATA>.*?</METADATA>', '', summary_response['summary'])
    return cleaned_summarization, model_name, usages, summary_response['summary_suitable'], summary_response['reasoning']

def generate_questions_from_summary(summary, guru_type):
    llm_model, model_name = get_summary_question_generation_model()
    if llm_model == LLM_MODEL.OPENAI:
        questions, usages = get_openai_requester().generate_questions_from_summary(summary, guru_type, model_name=model_name)
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
    return data_sources[0].url

def check_binge_auth(binge, user):
    if not binge:
        return True
    if settings.ENV == 'selfhosted':
        return True
    if user and user.is_authenticated and user.is_admin:
        return True
    
    # Allow access to SLACK, DISCORD, and GITHUB questions for everyone
    root_question = binge.root_question
    if root_question and root_question.source in [Question.Source.SLACK.value, Question.Source.DISCORD.value, Question.Source.GITHUB.value]:
        return True

    if not root_question:
        # Slack and Discord questions are being asked currently. Allow.
        return True
        
    # For other sources, check ownership
    if not user:
        return False

    # Allow if user is a maintainer
    if user in binge.guru_type.maintainers.all():
        return True

    return binge.owner == user

def search_question(
    user, 
    guru_type_object, 
    binge, 
    slug=None, 
    question=None, 
    will_check_binge_auth=True, 
    include_api=False, 
    only_widget=False, 
    allow_maintainer_access=False # Allows maintainer access to all questions
    ): 
    def get_source_conditions(user):
        """Helper function to get source conditions based on user"""
        if user is None:
            # For anonymous users
            # API requests are not allowed
            # Widget requests are allowed
            # SLACK, DISCORD, and GITHUB questions are allowed
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
            elif allow_maintainer_access and user in guru_type_object.maintainers.all():
                return Q()
            else:
                if include_api:
                    return (
                        ~Q(source__in=[Question.Source.API.value, Question.Source.WIDGET_QUESTION.value]) |
                        Q(source__in=[Question.Source.API.value], user=user) |
                        Q(source__in=[Question.Source.SLACK.value, Question.Source.DISCORD.value, Question.Source.GITHUB.value])
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
        
    # Check if question exists in db
    question_obj = Question.objects.filter(slug=question_slug, guru_type__slug=guru_type_slug, binge=None)
    if not question_obj.exists():
        return

    question_obj = question_obj.first()

    # Notify the guru type maintainer
    def_settings = get_default_settings()

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
    question: Optional[str]                   # Question text

    @classmethod
    def from_existing(cls, question_obj: Question) -> 'APIAskResponse':
        """Create response for existing question"""
        return cls(
            content=question_obj.content,
            error=None,
            question_obj=question_obj,
            is_existing=True,
            question=question_obj.question
        )

    @classmethod
    def from_stream(cls, stream_generator: Generator, question: str) -> 'APIAskResponse':
        """Create response for new streaming question"""
        return cls(
            content=stream_generator,
            error=None,
            question_obj=None,
            is_existing=False,
            question=question
        )

    @classmethod
    def from_error(cls, error_msg: str) -> 'APIAskResponse':
        """Create response for error case"""
        return cls(
            content=None,
            error=error_msg,
            question_obj=None,
            is_existing=False,
            question=None
        )

class APIType:
    API = 'API'
    WIDGET = 'WIDGET'
    DISCORD = 'DISCORD'
    SLACK = 'SLACK'
    GITHUB = 'GITHUB'

    @classmethod
    def is_api_type(cls, api_type: str) -> bool:
        return api_type in [cls.API, cls.DISCORD, cls.SLACK, cls.GITHUB]

    @classmethod
    def get_question_source(cls, api_type: str) -> str:
        return {
            cls.WIDGET: Question.Source.WIDGET_QUESTION.value,
            cls.API: Question.Source.API.value,
            cls.DISCORD: Question.Source.DISCORD.value,
            cls.SLACK: Question.Source.SLACK.value,
            cls.GITHUB: Question.Source.GITHUB.value,
        }[api_type]

def api_ask(question: str, 
            guru_type: GuruType, 
            binge: Binge | None, 
            parent: Question | None, 
            fetch_existing: bool, 
            api_type: APIType, 
            user: User | None,
            github_comments: list | None = None) -> APIAskResponse:
    """
    API ask endpoint.
    It either returns the existing answer or streams the new one
    
    Args:
        question (str): The question to simulate the summary and answer for.
        guru_type (GuruType): The guru type to simulate the summary and answer for.
        binge (Binge): The binge to simulate the summary and answer for.
        parent (Question): The parent question.
        fetch_existing (bool): Whether to fetch the existing question data.
        api_type (APIType): The type of API call (WIDGET, API, DISCORD, SLACK, GITHUB).
        user (User): The user making the request.
        github_comments (list): The comments for the GitHub issue.

    Returns:
        APIAskResponse: A dataclass containing all response information
    """

    is_api = APIType.is_api_type(api_type)

    if api_type == APIType.SLACK:
        short_answer = True
    else:
        short_answer = False

    include_api = is_api
    only_widget = api_type == APIType.WIDGET

    question_source = APIType.get_question_source(api_type)

    # Search the question with only the question text (this will return the last question with the same text)
    if fetch_existing:
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
        if existing_question:
            logger.info(f"Found existing question with slug for {question} in guru type {guru_type.slug}")
            return APIAskResponse.from_existing(existing_question)

    summary_data, summary_times = get_question_summary(question, guru_type.slug, binge, short_answer=short_answer, github_comments=github_comments)
    
    if 'valid_question' not in summary_data or not summary_data['valid_question']:
        return APIAskResponse.from_error(f"This question is not related to {guru_type.name}.")

    # Prepare summary data
    summary_prompt_tokens = summary_data.get('prompt_tokens', 0)
    summary_completion_tokens = summary_data.get('completion_tokens', 0)
    summary_cached_prompt_tokens = summary_data.get('cached_prompt_tokens', 0)
    user_intent = summary_data.get('user_intent', '')
    answer_length = summary_data.get('answer_length', '')
    enhanced_question = summary_data.get('enhanced_question', [])
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
        response, prompt, links, context_vals, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage, before_stream_times = stream_question_answer(
            question, 
            guru_type.slug, 
            user_intent, 
            answer_length, 
            user_question,
            question_source,
            enhanced_question,
            parent,
            user,
            github_comments
        )

        if not response:
            logger.error(f"No response from the LLM for question {question} and guru type {guru_type.slug}.")
            return APIAskResponse.from_error(f"{guru_type.name} Guru doesn't have enough data as a source to generate a reliable answer for this question.")

        times = {}
        times['before_stream'] = before_stream_times
        times['summary'] = summary_times

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
            enhanced_question=enhanced_question,
            times=times,
            source=question_source,
            parent=parent,
            binge=binge,
            user=user,
        )
    except Exception as e:
        logger.error(f"Error in api_ask: {str(e)}", exc_info=True)
        return APIAskResponse.from_error(f"There was an error in the stream. We are investigating the issue. Please try again later.")
    
    return APIAskResponse.from_stream(stream_generator, question)

def format_trust_score(trust_score: float) -> str:
    return int(trust_score * 100) if trust_score is not None else None

def format_date_updated(date_updated: datetime) -> str:
    return date_updated.strftime('%-d %B %Y') if date_updated else None

def format_references(references: list, api: bool = False) -> list:
    from core.gcp import replace_media_root_with_base_url
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
                for reference in processed_references:
                    if reference['link'] == pdf_data_source.url:
                        reference['link'] = replace_media_root_with_base_url(reference['link'])
                    


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

def prepare_prompt_for_context_relevance(cot: bool, guru_variables: dict, contexts: list) -> str:
    from core.prompts import (context_relevance_prompt, 
        context_relevance_cot_expected_output, 
        context_relevance_cot_output_format, 
        context_relevance_without_cot_expected_output, 
        context_relevance_without_cot_output_format,
        context_relevance_code_cot_expected_output,
        context_relevance_code_without_cot_expected_output,
        text_example_template,
        code_example_template)

    # Check if we have code or text contexts
    has_code = False
    has_text = False
    for context in contexts:
        if context['prefix'] == 'Code':
            has_code = True
        elif context['prefix'] == 'Text':
            has_text = True

    if cot:
        output_format = context_relevance_cot_output_format
        if has_code and not has_text:
            # Only code contexts
            example_template = f"Here is an example:\n\n{code_example_template}\n\nEXPECTED OUTPUT:\n{context_relevance_code_cot_expected_output}"
        elif has_text and not has_code:
            # Only text contexts
            example_template = f"Here is an example:\n\n{text_example_template}\n\nEXPECTED OUTPUT:\n{context_relevance_cot_expected_output}"
        else:
            # Both code and text contexts or neither
            example_template = f"Here is an example:\n\n{text_example_template}\n\nEXPECTED OUTPUT:\n{context_relevance_cot_expected_output}\n\nHere is another example with code contexts:\n\n{code_example_template}\n\nEXPECTED OUTPUT:\n\n{context_relevance_code_cot_expected_output}"
    else:
        output_format = context_relevance_without_cot_output_format
        if has_code and not has_text:
            # Only code contexts
            example_template = f"Here is an example:\n\n{code_example_template}\n\nEXPECTED OUTPUT:\n{context_relevance_code_without_cot_expected_output}"
        elif has_text and not has_code:
            # Only text contexts
            example_template = f"Here is an example:\n\n{text_example_template}\n\nEXPECTED OUTPUT:\n{context_relevance_without_cot_expected_output}"
        else:
            # Both code and text contexts or neither
            example_template = f"Here is an example:\n\n{text_example_template}\n\nEXPECTED OUTPUT:\n{context_relevance_without_cot_expected_output}\n\nHere is another example with code contexts:\n\n{code_example_template}\n\nEXPECTED OUTPUT:\n\n{context_relevance_code_without_cot_expected_output}"

    prompt = context_relevance_prompt.format(**guru_variables, example_with_output=example_template, output_format=output_format)
    return prompt

def string_to_boolean(value: str) -> bool:
    return value.lower() in ['true']

def format_github_repo_error(error: str, user_error: str = None) -> str:
    """Format GitHub repository error messages for user display.
    
    Args:
        error: The raw error message string
        user_error: Optional user-friendly error message
        
    Returns:
        A user-friendly formatted error message
    """
    # Return user_error if it exists
    if user_error:
        return user_error
        
    # Check if it's our custom error message format
    if "Technical details:" in error:
        # Return just the user-friendly part
        return error.split("Technical details:")[0].strip()
        
    # Handle specific error cases
    if error.startswith('No repository exists at this URL'):
        return error
    elif error.startswith('The codebase'):
        return error
    elif 'not found' in error.lower():
        return 'No repository exists at this URL.'
    else:
        return 'Something went wrong. The team has been notified about the issue. You can also contact us on Discord.'

def encode_guru_slug(guru_slug: str) -> str:
    return Signer(key=settings.SECRET_KEY).sign(guru_slug)

def decode_guru_slug(encoded_guru_slug: str) -> str:
    try:
        signer = Signer(key=settings.SECRET_KEY)
        decoded_slug = signer.unsign(encoded_guru_slug)
        return decoded_slug
    except BadSignature:
        # Handle invalid signature
        logger.error(f"Invalid signature for encoded guru slug: {encoded_guru_slug}")
        return None


def custom_exception_handler_throttled(exc, context):
    response = exception_handler(exc, context)
    
    if isinstance(exc, Throttled):
        custom_response_data = {
            'msg': 'Request was throttled. Expected available in %d seconds.' % exc.wait
        }
        response.data = custom_response_data
        
    return response

def get_embedder_and_model(model_choice, sync = True):
    """
    Returns a tuple of (embedder_instance, model_name) based on the model choice.
    
    Args:
        model_choice: The embedding model choice from GuruType.EmbeddingModel. Used only in cloud.
        
    Returns:
        tuple: (embedder_instance, model_name)
    """
    from core.requester import OpenAIRequester
    if settings.ENV == 'selfhosted':
        from core.models import Settings
        settings_obj = Settings.objects.first()
        if not sync:
            if model_choice == Settings.DefaultEmbeddingModel.SELFHOSTED.value:
                return (OpenAIRequester(), "text-embedding-3-small")
            else:
                return (OllamaRequester(settings_obj.ollama_url), model_choice)

        assert settings_obj, "Settings object not found"
        if settings_obj.ai_model_provider == Settings.AIProvider.OLLAMA:
            from core.requester import OllamaRequester
            # TODO: If text/code separation is needed, we need to get it as an arg to @get_embedder_and_model. Then use it to fetch from settings_obj and return. Nothing else is needed
            return (OllamaRequester(settings_obj.ollama_url), settings_obj.ollama_embedding_model)
        else:
            return (OpenAIRequester(), "text-embedding-3-small")
    
    # Cloud version logic
    model_map = {
        GuruType.EmbeddingModel.IN_HOUSE: (None, "in-house"),  # No embedder instance needed for in-house
        GuruType.EmbeddingModel.GEMINI_EMBEDDING_001: (GeminiEmbedder(), "embedding-001"),
        GuruType.EmbeddingModel.GEMINI_TEXT_EMBEDDING_004: (GeminiEmbedder(), "text-embedding-004"),
        GuruType.EmbeddingModel.OPENAI_TEXT_EMBEDDING_3_SMALL: (OpenAIRequester(), "text-embedding-3-small"),
        GuruType.EmbeddingModel.OPENAI_TEXT_EMBEDDING_3_LARGE: (OpenAIRequester(), "text-embedding-3-large"),
        GuruType.EmbeddingModel.OPENAI_TEXT_EMBEDDING_ADA_002: (OpenAIRequester(), "text-embedding-ada-002"),
    }
    # Default to in-house if model_choice is not found
    return model_map.get(model_choice, (None, "in-house"))

def get_embedding_model_config(model_choice, sync = True):
    """
    Returns a tuple of (collection_name, dimension) based on the GuruType.EmbeddingModel choice.
    
    Args:
        model_choice: The embedding model choice from GuruType.EmbeddingModel
        
    Returns:
        tuple: (collection_name, dimension)
        
    Example:
        >>> get_embedding_model_config(GuruType.EmbeddingModel.OPENAI_TEXT_EMBEDDING_ADA_002)
        ('github_repo_code_openai_ada_002', 1536)
    """
    if settings.ENV == 'selfhosted':
        from core.models import Settings
        settings_obj = Settings.objects.first()
        assert settings_obj, "Settings object not found"

        if not sync:
            if model_choice in ["text-embedding-3-small", "OPENAI_TEXT_EMBEDDING_3_SMALL"]:
                return "github_repo_code", 1536
            else:
                model_choice = model_choice.replace(':', '_').replace('.', '_').replace('-', '_')
                return f"github_repo_code_{model_choice}", settings_obj.ollama_embedding_model_dimension
        
        # TODO: If text/code separation is needed, we need to get it as an arg to @get_embedding_model_config. Then use it to fetch from settings_obj and return. Nothing else is needed
        if settings_obj.ai_model_provider == Settings.AIProvider.OLLAMA:
            # For Ollama, we use a single collection for all embeddings
            model_choice = settings_obj.ollama_embedding_model.replace(':', '_').replace('.', '_').replace('-', '_')
            return f"github_repo_code_{model_choice}", settings_obj.ollama_embedding_model_dimension
        else:
            # For OpenAI in selfhosted
            return "github_repo_code", 1536  # OpenAI text-embedding-3-small dimension

    # Get default settings
    try:
        settings_obj = get_default_settings()
        if settings_obj.embedding_model_configs and model_choice in settings_obj.embedding_model_configs:
            config = settings_obj.embedding_model_configs[model_choice]
            return config['collection_name'], config['dimension']
    except Exception as e:
        logger.warning(f"Failed to get embedding model config from settings: {e}")
    
    # Fallback to default configurations if not found in settings
    model_configs = {
        GuruType.EmbeddingModel.IN_HOUSE: {
            'collection_name': 'github_repo_code', # Default in cloud
            'dimension': 1024
        },
        GuruType.EmbeddingModel.GEMINI_EMBEDDING_001: {
            'collection_name': 'github_repo_code_gemini_embedding_001',
            'dimension': 768
        },
        GuruType.EmbeddingModel.GEMINI_TEXT_EMBEDDING_004: {
            'collection_name': 'github_repo_code_gemini_text_embedding_004',
            'dimension': 768
        },
        GuruType.EmbeddingModel.OPENAI_TEXT_EMBEDDING_3_SMALL: {
            'collection_name': 'github_repo_code' if settings.ENV == 'selfhosted' else 'github_repo_code_openai_text_embedding_3_small',  # Default in selfhosted
            'dimension': 1536
        },
        GuruType.EmbeddingModel.OPENAI_TEXT_EMBEDDING_3_LARGE: {
            'collection_name': 'github_repo_code_openai_text_embedding_3_large',
            'dimension': 3072
        },
        GuruType.EmbeddingModel.OPENAI_TEXT_EMBEDDING_ADA_002: {
            'collection_name': 'github_repo_code_openai_ada_002',
            'dimension': 1536
        }
    }
    
    # Store configurations in settings if not already stored
    try:
        settings_obj = get_default_settings()
        if not settings_obj.embedding_model_configs:
            settings_obj.embedding_model_configs = model_configs
            settings_obj.save()
    except Exception as e:
        logger.warning(f"Failed to store embedding model configs in settings: {e}")
    
    # Default to in-house if model_choice is not found
    default_config = {
        'collection_name': 'github_repo_code',
        'dimension': 1024
    }
    
    config = model_configs.get(model_choice, default_config)
    return config['collection_name'], config['dimension']

def embed_texts_with_model(texts, model_choice, batch_size=32):
    """
    Embeds texts using the specified model choice
    """
    embedder, model_name = get_embedder_and_model(model_choice)
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        if model_name == "in-house":
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
        else:
            if isinstance(embedder, OpenAIRequester):
                embeddings.extend(embedder.embed_texts(batch, model_name=model_name))
            elif isinstance(embedder, OllamaRequester):
                is_valid, response = embedder.embed_texts(batch, model_name=model_name)
                if is_valid:
                    embeddings.extend([r['embedding'] for r in response])
                else:
                    raise Exception(f'Error while embedding with Ollama: {response}')
            else:  # GeminiEmbedder
                embeddings.extend(embedder.embed_texts(batch))
    
    return embeddings

def embed_text_with_model(text, model_choice):
    """
    Embeds a single text using the specified model choice with caching
    """
    if text is None or text == '':
        logger.error(f'Empty or None text passed to embed_text_with_model')
        return None
    
    # Generate cache key using hash of text and model choice
    cache_key = f"embedding:{hashlib.sha256(f'{text}:{model_choice}'.encode()).hexdigest()}"
    
    # Try to get from cache
    try:
        cache = caches['alternate']
        cached_embedding = cache.get(cache_key)
        if cached_embedding:
            return pickle.loads(cached_embedding)
    except Exception as e:
        logger.error(f'Error while getting the embedding from the cache: {e}. Cache key: {cache_key}. Text: {text}')
    
    # Generate embedding if not in cache
    embedder, model_name = get_embedder_and_model(model_choice)
    
    if model_name == "in-house":
        url = settings.EMBED_API_URL
        headers = {"Content-Type": "application/json"}
        if settings.EMBED_API_KEY:
            headers["Authorization"] = f"Bearer {settings.EMBED_API_KEY}"
        response = requests.post(url, headers=headers, data=json.dumps({"inputs": [text]}), timeout=30)
        
        if response.status_code == 200:
            embedding = response.json()[0]
        else:
            logger.error(f'Error while embedding the text: {text}. Response: {response.text}. Url: {url}')
            raise Exception(f'Error while embedding the text. Response: {response.text}. Url: {url}')
    else:
        if isinstance(embedder, OpenAIRequester):
            embedding = embedder.embed_text(text, model_name=model_name)
        elif isinstance(embedder, OllamaRequester):
            is_valid, response = embedder.embed_text(text, model_name=model_name)
            if is_valid:
                embedding = response['embedding']
            else:
                raise Exception(f'Error while embedding with Ollama: {response}')
        else:  # GeminiEmbedder
            embedding = embedder.embed_texts(text)[0]

    if embedding:
        try:
            # Cache the embedding (8 weeks expiration)
            cache.set(cache_key, pickle.dumps(embedding), timeout=60*60*24*7*8)
        except Exception as e:
            logger.error(f'Error while caching the embedding: {e}. Cache key: {cache_key}. Text: {text}')
        
    return embedding

def get_default_embedding_dimensions():
    """
    Returns the default embedding dimensions for the default embedding model
    """
    model_choice = Settings.get_default_embedding_model()
    return get_embedding_model_config(model_choice)[1]
