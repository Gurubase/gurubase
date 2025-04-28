from datetime import datetime, UTC
from random import sample
from typing import List
from PIL import Image
import io
import logging
import traceback
from celery import shared_task
from django.db import models
import redis
import requests
from core.exceptions import WebsiteContentExtractionThrottleError, GithubInvalidRepoError, GithubRepoSizeLimitError, GithubRepoFileCountLimitError, YouTubeContentExtractionError
from core import milvus_utils
from core.data_sources import fetch_data_source_content, get_internal_links, process_website_data_sources_batch
from core.requester import FirecrawlScraper, GuruRequester, OpenAIRequester, get_web_scraper
from core.guru_types import get_guru_type_names, get_guru_type_object
from core.models import DataSource, Favicon, GuruType, Integration, LLMEval, LinkReference, LinkValidity, Question, Settings, Summarization, SummaryQuestionGeneration, LLMEvalResult, GuruType, GithubFile, CrawlState
from core.utils import finalize_data_source_summarizations, embed_texts, generate_questions_from_summary, get_default_embedding_dimensions, get_links, get_llm_usage, get_milvus_client, get_more_seo_friendly_title, get_most_similar_questions, guru_type_has_enough_generated_questions, create_guru_type_summarization, simulate_summary_and_answer, validate_guru_type, vector_db_fetch, with_redis_lock, generate_og_image, get_default_settings, send_question_request_for_cloudflare_cache, send_guru_type_request_for_cloudflare_cache, get_embedding_model_config
from django.conf import settings
import time
import re
from django.db.models import Q, Avg, StdDev, Count, Sum, Exists, OuterRef
from statistics import median, mean, stdev
from django.utils import timezone
from django.utils.timezone import now
from datetime import timedelta
from django.db import transaction


logger = logging.getLogger(__name__)
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    charset="utf-8",
    decode_responses=True,
)

guru_requester = GuruRequester()
openai_requester = OpenAIRequester()

@shared_task
def set_similarities():
    fetch_batch_size = settings.SIMILARITY_FETCH_BATCH_SIZE
    save_batch_size = settings.SIMILARITY_SAVE_BATCH_SIZE

    start_time = time.time()
    # Update similar_questions for all questions
    logger.info("Setting similar_questions for all questions")
    bulk_save = {}

    # Get the last processed question ID from Redis
    last_processed_id = redis_client.get('set_similar_questions_last_processed_id')
    last_processed_id = int(last_processed_id) if last_processed_id else 0
    
    # Get questions in batches, ordered by ID
    questions = Question.objects.filter(
        id__gt=last_processed_id
    ).order_by('id')[:fetch_batch_size]
    
    if not questions.exists():
        # If no questions found after last_processed_id, reset to start
        redis_client.delete('set_similar_questions_last_processed_id')
        questions = Question.objects.all().order_by('id')[:fetch_batch_size]
    
    for q in questions:
        q.similar_questions = get_most_similar_questions(
            q.slug, 
            q.question, 
            q.guru_type.slug, 
            column='title', 
            sitemap_constraint=True
        )
        bulk_save[q.id] = q
        
        # Save the last processed ID
        redis_client.set('set_similar_questions_last_processed_id', q.id)
        
        if len(bulk_save) >= save_batch_size:
            Question.objects.bulk_update(bulk_save.values(), ['similar_questions'])
            bulk_save = {}
    
    if len(bulk_save) > 0:
        Question.objects.bulk_update(bulk_save.values(), ['similar_questions'])
    
    processed_count = questions.count()
    logger.info(f'Similarities set for {processed_count} questions in {time.time() - start_time} seconds')
    

@shared_task
def rewrite_content_for_wrong_markdown_content():
    logger.info('Rewriting content for wrong markdown content')
    def correct_markdown_headings(content):
        lines = content.split('\n')

        corrected_lines = []
        h1_corrected = False
        in_code_block = False

        for line in lines:
            # Toggle in_code_block status when encountering ``` lines
            if re.match(r'^\s*```', line):
                corrected_lines.append(line)
                in_code_block = not in_code_block
                continue

            # Process lines outside code blocks
            if not in_code_block:
                # Check if the document starts with an H2 and correct it to H1
                if not h1_corrected and line.startswith('##'):
                    corrected_line = '#' + line[2:]
                    h1_corrected = True
                elif h1_corrected and re.match(r'^(##+)', line):
                    # Reduce the level of all other headings by one
                    corrected_line = re.sub(r'^(##+)', lambda m: '#' * (len(m.group(1)) - 1), line)
                else:
                    corrected_line = line
            else:
                corrected_line = line

            corrected_lines.append(corrected_line)

        corrected_content = '\n'.join(corrected_lines)
        return corrected_content

    # questions = Question.objects.filter(add_to_sitemap=True)
    questions = Question.objects.all()

    for question in questions:
        title = question.content.split("\n")[0]

        if title.startswith("# "):
            continue
        
        logger.fatal(f"Title not starting with '# ': {title}. ID: {question.id}")

        # if question.content first line is empty, remove it
        if title == "":
            question.content = question.content[1:]
            question.save()
            continue

        # if title is ```markdown, remove it. And remove the last line if it is ```
        if title.startswith("```"):
            question.content = question.content.split("\n")[1:-1]
            question.save()
            continue
        
        if title.startswith("## "):
            corrected_content = correct_markdown_headings(question.content)
            question.content = corrected_content
            question.save()
    logger.info('Rewritten content for wrong markdown content')

@shared_task
def fill_empty_og_images():
    logger.info('Filling empty og images')
    fetch_batch_size = settings.FILL_OG_IMAGES_FETCH_BATCH_SIZE
    # generate og images for questions that does not have them
    questions = Question.objects.filter(og_image_url='')
    for question in questions.iterator(chunk_size=fetch_batch_size):
        generate_og_image(question)
    logger.info('Filled empty og images')

@shared_task
def update_question_as_the_question_content_h1():
    logger.info('Updating question as the question content h1')
    questions = Question.objects.all()

    for question in questions:
        title = question.content.split("\n")[0]

        if not title.startswith("# "):
            logger.fatal(f"Title not starting with '# ': {title}. ID: {question.id}")
            continue

        title = title.replace("# ", "")

        # if title character length is greater than 150, log error and continue
        if len(title) > 150:
            # go to gpt and change
            new_title = get_more_seo_friendly_title(title)
            if new_title == "":
                logger.fatal(f"Title length greater than 150, shortening attempt failed: {title}. ID: {question.id}")
                continue
            question.content = question.content.replace(title, new_title)
            question.question = new_title
            question.save()
            return


        if question.question != title:
            logger.info(f"Updating question title: {question.question} to {title}")
            question.question = title
            question.save()
    logger.info('Updated question as the question content h1')


@shared_task
def find_duplicate_question_titles():
    logger.info('Finding duplicate question titles')
    questions = Question.objects.filter(add_to_sitemap=True)
    for question in questions:
        questions_with_same_title = Question.objects.filter(question=question.question, add_to_sitemap=True).exclude(id=question.id)
        if questions_with_same_title.exists():
            logger.fatal(f"Question has duplicate title: {question.question}. ID: {question.id}")
    logger.info('Found duplicate question titles')


@shared_task
@with_redis_lock(
    redis_client,
    settings.TITLE_PROCESS_LOCK,
    settings.TITLE_PROCESS_LOCK_DURATION_SECONDS,
)
def process_titles():
    logger.info('Processing titles')
    def process_title(title):
        # Go to gpt mini, get a more seo friendly title
        new_title = get_more_seo_friendly_title(title)
        if new_title == "":
            return title, False
        
        return new_title, True

    questions = Question.objects.filter(title_processed=False).filter(
        Q(question__icontains='can you') |
        Q(question__icontains='explain') |
        Q(question__icontains='describe') |
        Q(question__icontains='do you') |
        Q(question__icontains='can i')
    )

    for q in questions.iterator(chunk_size=100):
        old_title = q.question
        new_title, success = process_title(old_title)
        if not success:
            continue
        
        q.old_question = old_title
        q.question = new_title
        # update question content with new title
        q.content = q.content.replace(old_title, new_title)
        q.title_processed = True
        q.save()
        logger.info(f"Updated question: {q.id}")
    logger.info('Processed titles')

@shared_task
def data_source_retrieval(guru_type_slug=None, countdown=0):
    logger.info('Data source retrieval')

    @with_redis_lock(
        redis_client,
        lambda guru_type_slug, is_github: f'data_source_retrieval_lock_{guru_type_slug}_{"github" if is_github else "other"}',
        settings.DATA_SOURCE_RETRIEVAL_LOCK_DURATION_SECONDS,
    )
    def process_guru_type_data_sources(guru_type_slug, is_github=False):
        if not is_github and countdown > 0:
            # Wait for a bit for the data sources to be synced
            time.sleep(countdown)

        guru_type_object = get_guru_type_object(guru_type_slug)
        if is_github:
            data_sources = DataSource.objects.filter(
                status=DataSource.Status.NOT_PROCESSED,
                guru_type=guru_type_object,
                type=DataSource.Type.GITHUB_REPO
            )[:settings.DATA_SOURCE_FETCH_BATCH_SIZE]
        else:
            data_sources = DataSource.objects.exclude(
                type=DataSource.Type.GITHUB_REPO
            ).filter(
                status=DataSource.Status.NOT_PROCESSED,
                guru_type=guru_type_object
            )[:settings.DATA_SOURCE_FETCH_BATCH_SIZE]

        # Get the web scraper type
        scraper, scrape_tool = get_web_scraper()
        is_firecrawl = isinstance(scraper, FirecrawlScraper)

        # Group data sources by type
        website_sources = []
        other_sources = []
        for data_source in data_sources:
            if data_source.type == DataSource.Type.WEBSITE:
                website_sources.append(data_source)
            else:
                other_sources.append(data_source)

        # Process website sources in batches if using Firecrawl
        if website_sources and is_firecrawl:
            batch_size = settings.FIRECRAWL_BATCH_SIZE
            
            for i in range(0, len(website_sources), batch_size):
                batch = website_sources[i:i + batch_size]
                try:
                    processed_sources = process_website_data_sources_batch(batch)
                    
                    # Group sources by status for bulk updates
                    success_sources = []
                    failed_sources = []
                    
                    with transaction.atomic():
                        for data_source in processed_sources:
                            if data_source.status == DataSource.Status.NOT_PROCESSED:
                                raise WebsiteContentExtractionThrottleError(f'Throttle in batch. Stopping all subsequent extraction for guru type {guru_type_slug}')
                            elif not data_source.error:
                                data_source.status = DataSource.Status.SUCCESS
                                success_sources.append(data_source)
                            else:
                                data_source.status = DataSource.Status.FAIL
                                failed_sources.append(data_source)
                        
                        # Bulk update sources
                        if success_sources:
                            DataSource.objects.bulk_update(
                                success_sources,
                                ['status', 'error', 'user_error', 'title', 'content', 'scrape_tool']
                            )
                        if failed_sources:
                            DataSource.objects.bulk_update(
                                failed_sources,
                                ['status', 'error', 'user_error']
                            )
                        
                        # Write successful sources to Milvus
                        for data_source in success_sources:
                            try:
                                data_source.write_to_milvus()
                            except Exception as e:
                                logger.error(f"Error writing to Milvus for data source {data_source.id}: {e}", exc_info=True)
                                data_source.status = DataSource.Status.FAIL
                                data_source.error = str(e)
                                data_source.save()
                                
                except WebsiteContentExtractionThrottleError as e:
                    logger.warning(f"Throttled for batch Website URLs. Error: {e}")
                    # Mark all sources in batch as NOT_PROCESSED and stop processing
                    with transaction.atomic():
                        for data_source in batch:
                            data_source.status = DataSource.Status.NOT_PROCESSED
                            data_source.error = str(e)
                            data_source.user_error = str(e)
                        DataSource.objects.bulk_update(
                            batch,
                            ['status', 'error', 'user_error']
                        )
                    # Stop processing remaining batches if we hit rate limit
                    break
                        
                except Exception as e:
                    logger.error(f"Error while processing batch website sources: {e}", exc_info=True)
                    with transaction.atomic():
                        for data_source in batch:
                            data_source.status = DataSource.Status.FAIL
                            data_source.error = str(e)
                            data_source.user_error = str(e)
                        DataSource.objects.bulk_update(
                            batch,
                            ['status', 'error', 'user_error']
                        )

        # Process other sources (and website sources if not using Firecrawl) individually
        sources_to_process = other_sources + (website_sources if not is_firecrawl else [])
        jira_integration = Integration.objects.filter(type=Integration.Type.JIRA, guru_type=guru_type_object).first()
        zendesk_integration = Integration.objects.filter(type=Integration.Type.ZENDESK, guru_type=guru_type_object).first()
        confluence_integration = Integration.objects.filter(type=Integration.Type.CONFLUENCE, guru_type=guru_type_object).first()
        for data_source in sources_to_process:
            try:
                if data_source.type == DataSource.Type.JIRA:
                    data_source = fetch_data_source_content(jira_integration, data_source)
                elif data_source.type == DataSource.Type.ZENDESK:
                    data_source = fetch_data_source_content(zendesk_integration, data_source)
                elif data_source.type == DataSource.Type.CONFLUENCE:
                    data_source = fetch_data_source_content(confluence_integration, data_source)
                else:
                    data_source = fetch_data_source_content(None, data_source)
                data_source.status = DataSource.Status.SUCCESS
            except WebsiteContentExtractionThrottleError as e:
                logger.warning(f"Throttled for URL {data_source.url}. Error: {e}")
                data_source.status = DataSource.Status.NOT_PROCESSED
                data_source.error = str(e)
                data_source.user_error = str(e)
                data_source.save()
                continue
            except YouTubeContentExtractionError as e:
                logger.warning(f"Error while fetching YouTube data source: {e}")
                data_source.status = DataSource.Status.FAIL
                data_source.error = str(e)
                data_source.user_error = str(e)
                data_source.save()
                continue
            except (GithubRepoFileCountLimitError, GithubRepoSizeLimitError) as e:
                logger.warning(f"Error while fetching GitHub data source: {e}")
                data_source.status = DataSource.Status.FAIL
                data_source.error = str(e)
                data_source.user_error = str(e)
                data_source.save()
                continue
            except Exception as e:
                logger.error(f"Error while fetching data source: {traceback.format_exc()}")
                data_source.status = DataSource.Status.FAIL
                data_source.error = str(e)
                data_source.user_error = "Error while fetching data source"
                data_source.save()
                continue
            
            data_source.status = DataSource.Status.SUCCESS
            data_source.error = ''
            data_source.user_error = ''
            data_source.last_successful_index_date = datetime.now()
            data_source.save()
            try:
                data_source.write_to_milvus()
            except Exception as e:
                logger.error(f"Error while writing to milvus: {e}", exc_info=True)
                data_source.status = DataSource.Status.FAIL
                data_source.error = str(e)
                data_source.save()

    if settings.ENV == 'selfhosted':
        default_settings = get_default_settings()
        if default_settings.ai_model_provider == Settings.AIProvider.OPENAI:
            if not default_settings.is_openai_key_valid:
                return
        else:
            if not default_settings.is_ollama_url_valid:
                return
            if not default_settings.is_ollama_embedding_model_valid:
                return

    # Main func
    if guru_type_slug:
        # Process both GitHub and non-GitHub sources in parallel
        process_guru_type_data_sources(guru_type_slug=guru_type_slug, is_github=True)
        process_guru_type_data_sources(guru_type_slug=guru_type_slug, is_github=False)
    else:
        guru_type_slugs = get_guru_type_names()
        for guru_type_slug in guru_type_slugs:
            # Process both GitHub and non-GitHub sources in parallel
            process_guru_type_data_sources(guru_type_slug=guru_type_slug, is_github=True)
            process_guru_type_data_sources(guru_type_slug=guru_type_slug, is_github=False)

    logger.info("Data source retrieval completed for all guru types")


@shared_task
@with_redis_lock(
    redis_client,
    'llm_eval_lock',
    1800
)
def llm_eval(guru_types, check_answer_relevance=True, check_context_relevance=True, check_groundedness=True):
    logger.info(f"Evaluating {guru_types}")
    # guru_types is a list of strings

    model_names = [settings.GPT_MODEL]
    requester = OpenAIRequester()
    milvus_client = get_milvus_client()

    pairs = []
    for guru_type in guru_types:
        # Get the last version for the current guru type
        last_version = LLMEval.objects.filter(question__guru_type__slug=guru_type).order_by('-version').first()
        if last_version:
            try:
                version = last_version.version
                # If the number of the marked questions is smaller than the version, finish the current version. Else, use the next version
                marked_questions_count = Question.objects.filter(llm_eval=True, guru_type__slug=guru_type).count()
                eval_count = LLMEval.objects.filter(version=version, question__guru_type__slug=guru_type).count()

                if eval_count < marked_questions_count:
                    version = int(version)
                else:
                    version = int(version) + 1
            except Exception:
                version = 1
        else:
            version = 1
            
        pairs.append((guru_type, version))

        questions = Question.objects.filter(llm_eval=True, guru_type__slug=guru_type).order_by('-date_created')
        
        logger.info(f'Will evaluate {questions.count()} questions for guru type {guru_type}')
        guru_type_obj = get_guru_type_object(guru_type)
        collection_name = guru_type_obj.milvus_collection_name

        for q in questions:
            # contexts = vector_db_fetch(milvus_client, collection_name, q.question)
            contexts = None
            reranked_scores = None
            for model_name in model_names:
                # Check existence
                if LLMEval.objects.filter(question=q, model=model_name, version=version).exists():
                    print(f"LLM eval already exists for question {q.id} with model {model_name}")
                    continue
                
                context_relevance_user_prompt = None
                # Fetch previous version if exists
                previous_version = LLMEval.objects.filter(question=q, model=model_name).order_by('-version').first()

                if contexts is None and (check_context_relevance or check_groundedness):
                    contexts, reranked_scores, trust_score, processed_ctx_relevances, fetch_ctx_rel_usage, vector_db_times = vector_db_fetch(milvus_client, collection_name, q.question, q.guru_type.slug, q.user_question, q.enhanced_question, llm_eval=True)

                total_prompt_tokens = fetch_ctx_rel_usage['prompt_tokens']
                total_completion_tokens = fetch_ctx_rel_usage['completion_tokens']
                total_cached_prompt_tokens = fetch_ctx_rel_usage['cached_prompt_tokens']
                
                if check_context_relevance:
                    ctx_relevance, ctx_rel_usage, ctx_rel_prompt, context_relevance_user_prompt = requester.get_context_relevance(q.question, q.user_question, q.enhanced_question, guru_type, contexts, model_name)
                    ctx_rel_total_score = 0
                    
                    total_prompt_tokens += ctx_rel_usage['prompt_tokens']
                    total_completion_tokens += ctx_rel_usage['completion_tokens']
                    total_cached_prompt_tokens += ctx_rel_usage['cached_prompt_tokens']
                    ctx_relevance_result = []
                    if len(contexts) != len(ctx_relevance['contexts']):
                        logger.error(f"Contexts count mismatch for question {q.id}")
                        continue
                    
                    for claim in ctx_relevance['contexts']:
                        ctx_relevance_result.append(f'Context {claim["context_num"]}:\nScore: {claim["score"]}\nExplanation: {claim["explanation"]}\n\n')
                        ctx_rel_total_score += claim['score']

                    if len(ctx_relevance['contexts']) == 0:
                        ctx_relevance_avg_score = 0
                    else:
                        ctx_relevance_avg_score = ctx_rel_total_score / len(ctx_relevance['contexts'])

                    ctx_relevance_cot = ''.join(ctx_relevance_result)
                else:
                    if previous_version:
                        ctx_relevance_avg_score = previous_version.context_relevance
                        ctx_relevance_cot = previous_version.context_relevance_cot
                        ctx_rel_prompt = previous_version.context_relevance_prompt
                    else:
                        ctx_relevance_avg_score = 0
                        ctx_relevance_cot = 'No previous version exists and context relevance is not set to be checked'
                        ctx_rel_prompt = ''

                if check_groundedness:
                    groundedness, gr_usage, gr_prompt = requester.get_groundedness(q, contexts, model_name)
                
                    total_prompt_tokens += gr_usage['prompt_tokens']
                    total_completion_tokens += gr_usage['completion_tokens']
                    total_cached_prompt_tokens += gr_usage['cached_prompt_tokens']

                    groundedness_result = []    
                    claim_num = 1
                    groundedness_total_score = 0
                    for claim in groundedness['claims']:
                        groundedness_result.append(f'Claim {claim_num}: {claim["claim"]}\nScore: {claim["score"]}\nExplanation: {claim["explanation"]}\n\n')
                        groundedness_total_score += claim['score']
                        claim_num += 1
                        
                    if len(groundedness['claims']) == 0:
                        groundedness_avg_score = 0
                    else:
                        groundedness_avg_score = groundedness_total_score / len(groundedness['claims'])

                    groundedness_cot = ''.join(groundedness_result)
                else:
                    if previous_version:
                        groundedness_avg_score = previous_version.groundedness
                        groundedness_cot = previous_version.groundedness_cot
                        gr_prompt = previous_version.groundedness_prompt
                    else:
                        groundedness_avg_score = 0
                        groundedness_cot = 'No previous version exists and groundedness is not set to be checked'
                        gr_prompt = ''

                if check_answer_relevance:
                    # Get the answer
                    answer, answer_error, answer_usages, _ = simulate_summary_and_answer(q.question, guru_type_obj, check_existence=False, save=False, source=None) # source is unused if save=False
                    if answer_error:
                        logger.error(f"Error while simulating answer relevance: {answer_error}")
                        continue

                    # Usages of the answer
                    total_prompt_tokens += answer_usages['prompt_tokens']
                    total_completion_tokens += answer_usages['completion_tokens']
                    total_cached_prompt_tokens += answer_usages['cached_prompt_tokens']
                    
                    # Evaluate the answer
                    answer_relevance, ar_usage, ar_prompt = requester.get_answer_relevance(q, answer, model_name)
                    answer_relevance_score = answer_relevance['score']
                    answer_relevance_cot = answer_relevance['overall_explanation']
                    
                    # Usages of the answer relevance check
                    total_prompt_tokens += ar_usage['prompt_tokens']
                    total_completion_tokens += ar_usage['completion_tokens']
                    total_cached_prompt_tokens += ar_usage['cached_prompt_tokens']
                else:
                    if previous_version:
                        answer_relevance_score = previous_version.answer_relevance
                        answer_relevance_cot = previous_version.answer_relevance_cot
                        ar_prompt = previous_version.answer_relevance_prompt
                        answer = previous_version.answer
                    else:
                        answer_relevance_score = 0
                        answer_relevance_cot = 'No previous version exists and answer relevance is not set to be checked'
                        ar_prompt = ''
                        answer = ''
                
                default_settings = get_default_settings()
                llmeval_settings = {
                    "rerank_threshold": default_settings.rerank_threshold,
                    "rerank_threshold_llm_eval": default_settings.rerank_threshold_llm_eval,
                    "model_names": model_names,
                    "embed_api_url": settings.EMBED_API_URL,
                    "rerank_api_url": settings.RERANK_API_URL
                }       
                cost = get_llm_usage(model_name, total_prompt_tokens, total_completion_tokens, total_cached_prompt_tokens)
                LLMEval.objects.create(
                    question=q,
                    model=model_name,
                    version=version,
                    context_relevance_prompt=ctx_rel_prompt,
                    context_relevance_user_prompt=context_relevance_user_prompt,
                    groundedness_prompt=gr_prompt,
                    answer_relevance_prompt=ar_prompt,
                    contexts=contexts or '',
                    reranked_scores=reranked_scores or [],
                    cost_dollars=cost,
                    prompt_tokens=total_prompt_tokens,
                    completion_tokens=total_completion_tokens,
                    cached_prompt_tokens=total_cached_prompt_tokens,
                    context_relevance=ctx_relevance_avg_score,
                    context_relevance_cot=ctx_relevance_cot,
                    groundedness=groundedness_avg_score,
                    groundedness_cot=groundedness_cot,
                    answer_relevance=answer_relevance_score,
                    answer_relevance_cot=answer_relevance_cot,
                    answer=answer,
                    settings=llmeval_settings,
                    processed_ctx_relevances=processed_ctx_relevances
                )

    # After the evaluation is done for all guru types
    llm_eval_result.delay(pairs)
    logger.info('LLM eval result')


@shared_task
@with_redis_lock(
    redis_client,
    'content_links_lock',
    1800
)
def get_content_links():
    logger.info("Getting content links")
    # Get the last question id 
    try:
        last_question_id = LinkReference.objects.all().order_by('-question__id').first().question.id
    except:
        last_question_id = 0

    if not last_question_id:
        last_question_id = 0

    questions = Question.objects.filter(id__gt=last_question_id).order_by('-id')[:settings.TASK_FETCH_LIMIT]
    bulk_save = []
    for q in questions.iterator(chunk_size=100):
        links = get_links(q.content)
        for link in links:
            bulk_save.append(LinkReference(question=q, url=link))

        if len(bulk_save) >= 100:
            LinkReference.objects.bulk_create(bulk_save)
            bulk_save = []

    if len(bulk_save) > 0:
        LinkReference.objects.bulk_create(bulk_save)
    logger.info('Got content links')


@shared_task
@with_redis_lock(
    redis_client,
    'link_validity_lock',
    1800
)
def check_link_validity():
    logger.info("Checking link validity")
    link_refs = LinkReference.objects.filter(validity=None)[:settings.TASK_FETCH_LIMIT]
    bulk_update = []
    for link_ref in link_refs.iterator(chunk_size=100):
        try:
            existing_validity = LinkValidity.objects.filter(link=link_ref.link)
            if existing_validity.exists():
                link_ref.validity = existing_validity.first()
            else:
                try:
                    response = requests.get(link_ref.link, timeout=15)
                    status_code = response.status_code
                    valid = status_code == 200
                except Exception as e:
                    logger.warning(f"Error accessing {link_ref.link}: {str(e)}")
                    valid = False
                    status_code = 0
                link_ref.validity = LinkValidity.objects.create(link=link_ref, valid=valid, response_code=status_code)

            bulk_update.append(link_ref)

            if len(bulk_update) >= 100:
                LinkReference.objects.bulk_update(bulk_update, ['validity'])
                bulk_update = []
        except Exception as e:
            logger.error(f"Unexpected error while checking link validity: {traceback.format_exc()}")

        # Sleep for 1 second to avoid being flagged as bot
        time.sleep(1)

    if len(bulk_update) > 0:
        LinkReference.objects.bulk_update(bulk_update, ['validity'])
    logger.info('Checked link validity')

@shared_task
def check_favicon_validity():
    logger.info("Checking favicon validity")
    for favicon in Favicon.objects.iterator(chunk_size=100):
        try:
            response = requests.get(favicon.favicon_url, timeout=30)
            if response.content:
                try:
                    with io.BytesIO(response.content) as image_file:
                        im = Image.open(image_file)
                        im.verify()
                        im.close()
                    favicon.valid = response.status_code == 200
                except Exception as img_error:
                    logger.warning(f"Invalid image for favicon {favicon.favicon_url}: {str(img_error)}")
                    favicon.valid = False
            else:
                favicon.valid = False
            
            favicon.save()
        except Exception as e:
            logger.error(f"Error while checking favicon validity: {traceback.format_exc()}")
            favicon.valid = False
            favicon.save()
    logger.info("Checked favicon validity")

@shared_task
def summarize_data_sources(guru_type_slugs=["*"]):
    """
    Generate summarizes from data sources up until the final summarization for each guru type is created.

    Args:
        guru_type_slugs: A list of guru type slugs to summarize. If None, all guru types are summarized.
            If None: process all guru types
            If ["kubernetes", "javascript"]: process only these two guru types
            If ["*"]: process all guru types
    """
    logger.info("Summarizing data sources")

    @with_redis_lock(
        redis_client,
        lambda guru_type_slug: f'summarize_data_sources_lock_{guru_type_slug}',
        1800
    )
    def summarize_data_sources_for_guru_type(guru_type_slug, guru_type):
        """
        Generate initial and final summarizations for data sources for a guru type.
        A lock for each guru type is used to avoid race conditions.
        
        Args:
            guru_type_slug: The slug of the guru type
            guru_type: The guru type object
        """
        # logger.info(f"Summarizing data sources for guru type: {guru_type_slug}")
        data_sources = DataSource.objects.filter(status=DataSource.Status.SUCCESS, initial_summarizations_created=False, guru_type=guru_type)[:settings.TASK_FETCH_LIMIT]
        for data_source in data_sources.iterator(chunk_size=100):
            if len(data_source.content) > 1000:
                data_source.create_initial_summarizations()
            else:
                logger.info(f"Data source {data_source.id} has less than 1000 characters, skipping")

            try:
                data_source.create_initial_summarizations()
            except Exception as e:
                logger.error(f"Error while creating initial summarizations for data source {data_source.id}: {str(e)}")
                continue


        data_sources = DataSource.objects.filter(initial_summarizations_created=True, status=DataSource.Status.SUCCESS, final_summarization_created=False, guru_type=guru_type)[:settings.TASK_FETCH_LIMIT]
        for data_source in data_sources.iterator(chunk_size=100):
            finalize_data_source_summarizations(data_source)

        create_guru_type_summarization(guru_type)

    if guru_type_slugs and guru_type_slugs != ["*"]:
        for guru_type_slug in guru_type_slugs:
            try:
                guru_type = GuruType.objects.get(slug=guru_type_slug)
            except GuruType.DoesNotExist:
                logger.error(f"Guru type with slug {guru_type_slug} does not exist")
                continue
            summarize_data_sources_for_guru_type(guru_type_slug=guru_type_slug, guru_type=guru_type)
    else:
        for guru_type in GuruType.objects.all():
            summarize_data_sources_for_guru_type(guru_type_slug=guru_type.slug, guru_type=guru_type)

    logger.info("Summarized data sources")
        

@shared_task
def generate_questions_from_summaries(guru_type_slugs=["*"]):
    """
    For all initial data source summarizations, generate questions and save them as SummaryQuestionGeneration objects.

    Args:
        guru_type_slugs: A list of guru type slugs to summarize. If None, all guru types are summarized.
            If None: process all guru types
            If ["kubernetes", "javascript"]: process only these two guru types
            If ["*"]: process all guru types
    """
    logger.info(f"Generating questions from summaries for guru types: {guru_type_slugs}")

    @with_redis_lock(
        redis_client,
        lambda guru_type_slug: f'generate_questions_from_summaries_lock_{guru_type_slug}',
        1800
    )
    def generate_questions_from_summaries_for_guru_type(guru_type_slug, guru_type):
        """
        Generate questions from initial data source summarizations for a guru type.
        A lock for each guru type is used to avoid race conditions.

        Args:
            guru_type_slug: The slug of the guru type
            guru_type: The guru type object
        """
        enough_generated, total_generated = guru_type_has_enough_generated_questions(guru_type)
        if enough_generated:
            logger.info(f"Guru type {guru_type_slug} has enough generated questions, skipping")
            return
        
        # Get total count of eligible summarizations
        total_count = Summarization.objects.filter(
            is_data_source_summarization=True,
            initial=True,
            question_generation_ref=None,
            guru_type=guru_type,
            summary_suitable=True
        ).count()

        # Calculate how many random records we want
        required_question_count = settings.GENERATED_QUESTION_PER_GURU_LIMIT - total_generated
        expected_sample_size = int(required_question_count / settings.QUESTION_GENERATION_COUNT)
        sample_size = min(total_count, expected_sample_size)
        
        # Get random IDs
        summarization_ids = Summarization.objects.filter(
            is_data_source_summarization=True,
            initial=True,
            question_generation_ref=None,
            guru_type=guru_type,
            summary_suitable=True
        ).values_list('id', flat=True)
        
        random_ids = sample(list(summarization_ids), sample_size)
        
        # Get the random summarizations
        summarizations = Summarization.objects.filter(id__in=random_ids)

        for summarization in summarizations.iterator(chunk_size=100):
            if not summarization.guru_type:
                logger.error(f"Summarization {summarization.id} has no guru type")
                continue
            
            questions, model_name, usages = generate_questions_from_summary(
                summarization.result_content, 
                summarization.guru_type)
            
            summary_sufficient = questions['summary_sufficient']
            questions = questions['questions']
            question_generation = SummaryQuestionGeneration.objects.create(
                summarization_ref=summarization, 
                guru_type=summarization.guru_type, 
                questions=questions,
                summary_sufficient=summary_sufficient,
                model=model_name,
                usages=usages
            )
            
            summarization.question_generation_ref = question_generation
            summarization.save()
            
            total_generated += len(questions)
            if total_generated >= settings.GENERATED_QUESTION_PER_GURU_LIMIT:
                logger.info(f"Guru type {guru_type_slug} has reached the limit of {settings.GENERATED_QUESTION_PER_GURU_LIMIT} generated questions, stopping")
                break
    
    if guru_type_slugs and guru_type_slugs != ["*"]:
        for guru_type_slug in guru_type_slugs:
            try:
                guru_type = GuruType.objects.get(slug=guru_type_slug)
            except GuruType.DoesNotExist:
                logger.error(f"Guru type with slug {guru_type_slug} does not exist")
                continue
            generate_questions_from_summaries_for_guru_type(guru_type_slug=guru_type_slug, guru_type=guru_type)
    else:
        for guru_type in GuruType.objects.all():
            generate_questions_from_summaries_for_guru_type(guru_type_slug=guru_type.slug, guru_type=guru_type)
    
    logger.info("Generated questions from summaries")

@shared_task
# def llm_eval_result(guru_types, version):
def llm_eval_result(pairs):
    logger.info(f"Calculating LLM eval metrics for pairs: {pairs}")
    for guru_type_slug, version in pairs:
        guru_type = GuruType.objects.get(slug=guru_type_slug)
        model = settings.GPT_MODEL
        
        evals = LLMEval.objects.filter(
            question__guru_type=guru_type,
            version=version,
            model=model
        )
            
        if not evals.exists():
            logger.warning(f"No LLMEval entries found for guru_type: {guru_type_slug}, version: {version}, model: {model}")
            continue
        
        # Metrics including zeros
        metrics = evals.aggregate(
            context_relevance_avg=Avg('context_relevance'),
            groundedness_avg=Avg('groundedness'),
            answer_relevance_avg=Avg('answer_relevance'),
            context_relevance_std=StdDev('context_relevance'),
            groundedness_std=StdDev('groundedness'),
            answer_relevance_std=StdDev('answer_relevance'),
            total_questions=Count('id'),
            total_cost=Sum('cost_dollars')
        )
        
        # Calculate medians manually
        context_relevance_values = list(evals.values_list('context_relevance', flat=True))
        groundedness_values = list(evals.values_list('groundedness', flat=True))
        answer_relevance_values = list(evals.values_list('answer_relevance', flat=True))
        
        metrics['context_relevance_median'] = median(context_relevance_values)
        metrics['groundedness_median'] = median(groundedness_values)
        metrics['answer_relevance_median'] = median(answer_relevance_values)
        
        # Metrics excluding zeros
        def calc_non_zero_metrics(values):
            non_zero_values = [v for v in values if v != 0]
            return {
                'avg': mean(non_zero_values) if non_zero_values else None,
                'median': median(non_zero_values) if non_zero_values else None,
                'std': stdev(non_zero_values) if len(non_zero_values) > 1 else None,
                'count': len(non_zero_values)
            }
        
        context_relevance_non_zero = calc_non_zero_metrics(context_relevance_values)
        groundedness_non_zero = calc_non_zero_metrics(groundedness_values)
        answer_relevance_non_zero = calc_non_zero_metrics(answer_relevance_values)
        
        metrics.update({
            'context_relevance_non_zero_avg': context_relevance_non_zero['avg'],
            'context_relevance_non_zero_median': context_relevance_non_zero['median'],
            'context_relevance_non_zero_std': context_relevance_non_zero['std'],
            'context_relevance_non_zero_count': context_relevance_non_zero['count'],
            
            'groundedness_non_zero_avg': groundedness_non_zero['avg'],
            'groundedness_non_zero_median': groundedness_non_zero['median'],
            'groundedness_non_zero_std': groundedness_non_zero['std'],
            'groundedness_non_zero_count': groundedness_non_zero['count'],
            
            'answer_relevance_non_zero_avg': answer_relevance_non_zero['avg'],
            'answer_relevance_non_zero_median': answer_relevance_non_zero['median'],
            'answer_relevance_non_zero_std': answer_relevance_non_zero['std'],
            'answer_relevance_non_zero_count': answer_relevance_non_zero['count'],
        })
        
        # Get settings from the first eval (assuming all evals in a run have the same settings)
        first_eval = evals.first()
        eval_settings = first_eval.settings if first_eval else {}
        
        logger.info(f"Settings for guru_type: {guru_type_slug}, version: {version}, model: {model}: {eval_settings}")
        
        LLMEvalResult.objects.update_or_create(
            guru_type=guru_type,
            version=version,
            model=model,
            defaults={**metrics, 'settings': eval_settings}
        )
    
    logger.info(f"Calculated LLM eval metrics for pairs: {pairs}")


@shared_task
@with_redis_lock(
    redis_client,
    'process_summary_questions_lock',
    5400  # 90 minutes
)
def process_summary_questions():
    """
    Process the questions generated from summaries that are not processed yet.
    """
    logger.info("Processing summary questions")
    summary_questions = SummaryQuestionGeneration.objects.filter(processed=False)
    for summary_question in summary_questions.iterator(chunk_size=100):
        for question in summary_question.questions:
            _, _, _, question_obj = simulate_summary_and_answer(
                question,
                summary_question.guru_type,
                check_existence=True,
                save=True,
                source=Question.Source.SUMMARY_QUESTION
            )
        summary_question.processed = True
        summary_question.question = question_obj
        summary_question.save()
    logger.info("Processed summary questions")

@shared_task
@with_redis_lock(
    redis_client,
    'move_questions_to_milvus_lock',
    1800
)
def move_questions_to_milvus():
    """
    Move the questions to Milvus for similarity search
    Does the embedding and the milvus insert in batches 
    """

    questions = Question.objects.filter(similarity_written_to_milvus=False, source=Question.Source.SUMMARY_QUESTION, binge=None)[:settings.TASK_FETCH_LIMIT]
    questions_collection_name = settings.MILVUS_QUESTIONS_COLLECTION_NAME
    if not milvus_utils.collection_exists(collection_name=questions_collection_name):
        milvus_utils.create_similarity_collection(questions_collection_name)

    batch = []
    embed_batch = []
    questions_batch = []
    for q in questions.iterator(chunk_size=100):
        # Check existence
        if milvus_utils.fetch_vectors(questions_collection_name, f'id=={q.id}'):
            q.similarity_written_to_milvus = True
            questions_batch.append(q)
            logger.warning(f'Question {q.id} already exists in Milvus. Skipping...')
            continue

        if q.question == '':
            q.similarity_written_to_milvus = True
            questions_batch.append(q)
            logger.warning(f'Question {q.id} has an empty question. Skipping...')
            continue
        
        # if q.description == '':
        #     q.similarity_written_to_milvus = True
        #     questions_batch.append(q)
        #     logger.warning(f'Question {q.id} has an empty description. Skipping...')
        #     continue
        
        if q.content == '':
            q.similarity_written_to_milvus = True
            questions_batch.append(q)
            logger.warning(f'Question {q.id} has an empty content. Skipping...')
            continue

        doc = {
            'title': q.question,
            'slug': q.slug,
            'id': q.id,
            'on_sitemap': q.add_to_sitemap,
            'guru_type': q.guru_type.name,
        }
        batch.append(doc)
        q.similarity_written_to_milvus = True
        questions_batch.append(q)
        # embed_batch.append({'title': q.question, 'description': q.description, 'content': q.content})
        embed_batch.append({'title': q.question, 'description': '', 'content': q.content})
    
        # if len(batch) == 32:
        if len(batch) > 1:
            title_embeddings = embed_texts(list(map(lambda x: x['title'], embed_batch)))
            # description_embeddings = embed_texts(list(map(lambda x: x['description'], embed_batch)))
            content_embeddings = embed_texts(list(map(lambda x: x['content'], embed_batch)))

            dimension = get_default_embedding_dimensions()
            for i, doc in enumerate(batch):
                # doc['description_vector'] = description_embeddings[i]
                doc['description_vector'] = [0] * dimension
                doc['title_vector'] = title_embeddings[i]
                doc['content_vector'] = content_embeddings[i]
            milvus_utils.insert_vectors(
                collection_name=questions_collection_name,
                docs=batch,
                dimension=dimension
            )
            batch = []
            embed_batch = []
            
            Question.objects.bulk_update(questions_batch, ['similarity_written_to_milvus'])
            questions_batch = []
            
    if len(batch) > 0:
        title_embeddings = embed_texts(list(map(lambda x: x['title'], embed_batch)))
        # description_embeddings = embed_texts(list(map(lambda x: x['description'], embed_batch)))
        content_embeddings = embed_texts(list(map(lambda x: x['content'], embed_batch)))

        dimension = get_default_embedding_dimensions()
        for i, doc in enumerate(batch):
            # doc['description_vector'] = description_embeddings[i]
            doc['description_vector'] = [0] * dimension
            doc['title_vector'] = title_embeddings[i]
            doc['content_vector'] = content_embeddings[i]
        milvus_utils.insert_vectors(
            collection_name=questions_collection_name,
            docs=batch,
            dimension=dimension
        )
        Question.objects.bulk_update(questions_batch, ['similarity_written_to_milvus'])

@shared_task
@with_redis_lock(
        redis_client,
        'process_sitemap_lock',
        1800
    )
def process_sitemap():
    """
    Processes questions across all guru types to add to sitemap,
    with a gradual increase over time based on previous day's additions.
    """
    
    logger.info('Processing sitemap for all guru types')
    
    # Get yesterday's sitemap additions count
    today = timezone.now().date()
    yesterday = today - timezone.timedelta(days=1)
    yesterday_start = timezone.make_aware(datetime.combine(yesterday, datetime.min.time()))
    yesterday_end = timezone.make_aware(datetime.combine(yesterday, datetime.max.time()))
    logger.info(f'Yesterday start: {yesterday_start}, Yesterday end: {yesterday_end}')
    yesterday_additions = Question.objects.filter(
        add_to_sitemap=True,
        sitemap_date__range=(yesterday_start, yesterday_end)
    ).count()

    # Get today's additions so far
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    logger.info(f'Today start: {today_start}, Today end: {today_end}')
    today_additions = Question.objects.filter(
        add_to_sitemap=True,
        sitemap_date__range=(today_start, today_end)
    ).count()
    
    # If no questions were added yesterday, start with initial batch
    # if yesterday_additions == 0:
    #     daily_target = 100  # Day 1 target
    # else:
    #     # Calculate increase (10-20% random) based on yesterday's count
    #     increase_percent = random.uniform(10, 20)
    #     daily_target = int(yesterday_additions * (1 + (increase_percent/100)))

    daily_target = 100
        
    logger.info(f'Yesterday additions: {yesterday_additions}, Daily target: {daily_target}, Added today: {today_additions}')
    
    # Calculate remaining questions for today
    questions_to_add = max(0, daily_target - today_additions)
    if questions_to_add <= 0:
        logger.info("Daily sitemap quota reached")
        return
        
    # Get random questions from all guru types
    questions = Question.objects.filter(
        id__gt=45000,
        # guru_type__custom=True,
        guru_type__active=True,
        add_to_sitemap=False,
        sitemap_reason="",
        source__in=[Question.Source.SUMMARY_QUESTION.value, Question.Source.RAW_QUESTION.value]
    ).order_by('?')[:questions_to_add * 2]  # Get 2x to ensure we have enough after filtering
    
    # Process questions
    selected_questions = []
    for q in questions:
        add_to_sitemap, sitemap_reason = q.is_on_sitemap()
        if add_to_sitemap:
            selected_questions.append(q)
            if len(selected_questions) >= questions_to_add:
                break
        q.add_to_sitemap = add_to_sitemap
        q.sitemap_date = timezone.now()
        q.sitemap_reason = sitemap_reason
        q.save()
    
    logger.info('Processed sitemap for all guru types')

@shared_task
@with_redis_lock(
    redis_client,
    'update_guru_type_details_lock',
    1800
)
def update_guru_type_details():
    """
    Updates GuruType details:
    1. Adds github details if missing (only for the first GitHub repo)
    2. Updates domain knowledge if it's the default value
    """
    logger.info("Updating guru type details")
    
    from core.utils import get_root_summarization_of_guru_type
    from core.requester import GitHubRequester
    
    github_requester = GitHubRequester()

    guru_types = GuruType.objects.filter(custom=True, active=True)

    for guru_type in guru_types:
        # Update GitHub details if missing
        if not guru_type.github_details:
            github_repos = guru_type.github_repos
            if github_repos:
                try:
                    # Only fetch details for the first GitHub repo
                    first_repo = github_repos[0]
                    if not first_repo:
                        continue
                    try:
                        github_details = github_requester.get_github_repo_details(first_repo)
                        guru_type.github_details = github_details
                        guru_type.save()
                        logger.info(f'Updated github details for {guru_type.slug} (repo: {first_repo})')
                    except Exception as e:
                        logger.error(f"Error getting github details for repo {first_repo} in {guru_type.slug}: {traceback.format_exc()}")
                except Exception as e:
                    logger.error(f"Error getting github details for {guru_type.slug}: {traceback.format_exc()}")
                    continue

        # Update domain knowledge if it's default
        if settings.ENV != 'selfhosted' and guru_type.domain_knowledge == settings.DEFAULT_DOMAIN_KNOWLEDGE:
            from core.requester import GeminiRequester
            gemini_requester = GeminiRequester(model_name="gemini-1.5-pro-002")
            root_summarization = get_root_summarization_of_guru_type(guru_type.slug)
            if not root_summarization:
                logger.info(f'No root summarization found for {guru_type.slug}')
                continue

            try:
                # Get topics and description from github_details
                github_topics = []
                github_description = ""
                
                if guru_type.github_details:
                    github_topics = guru_type.github_details.get('topics', [])
                    github_description = guru_type.github_details.get('description', '')
                
                gemini_response = gemini_requester.generate_topics_from_summary(
                    root_summarization.result_content, 
                    guru_type.name,
                    github_topics,
                    github_description
                )
                
                new_topics = gemini_response.get('topics', [])
                if new_topics:
                    guru_type.domain_knowledge = ', '.join(new_topics)
                    guru_type.save()
                    logger.info(f'Updated domain knowledge for {guru_type.slug}')
            except Exception as e:
                logger.error(f"Error updating domain knowledge for {guru_type.slug}: {traceback.format_exc()}")
                continue

    logger.info("Updated guru type details")

@shared_task
def check_datasource_in_milvus_false_and_success():
    # This should not be happened. During deployment times, some datasources can not be updated because of pod deletion.
    logger.info('Checking datasources that are not in Milvus and have status SUCCESS')
    datasources = DataSource.objects.filter(in_milvus=False, status=DataSource.Status.SUCCESS)
    for ds in datasources:
        logger.error(f'DataSource {ds.id} is not in Milvus and has status SUCCESS. Change the Data Source status to Not Processed.')
    logger.info('Checked datasources that are not in Milvus and have status SUCCESS')


@shared_task
def send_request_to_questions_for_cloudflare_cache():
    logger.info('Sending request to questions for Cloudflare cache')
    sitemap_questions = Question.objects.filter(add_to_sitemap=True).order_by('cache_request_count')[:100]
    default_questions = Question.objects.filter(default_question=True).order_by('cache_request_count')[:100]
    guru_types = GuruType.objects.filter(active=True)
    for q in sitemap_questions:
        if not q.guru_type.active:
            continue
        send_question_request_for_cloudflare_cache(q)
        q.cache_request_count += 1
        q.save()
    for q in default_questions:
        if not q.guru_type.active:
            continue
        send_question_request_for_cloudflare_cache(q)
        q.cache_request_count += 1
        q.save()
    
    for guru_type in guru_types:
        send_guru_type_request_for_cloudflare_cache(guru_type)
    logger.info('Sent request to questions for Cloudflare cache')

@shared_task
@with_redis_lock(
    redis_client,
    'update_github_details_lock',
    1800
)
def update_github_details():
    """
    Updates GitHub details for guru types that haven't been updated in the last 24 hours.
    Processes at most 200 guru types per hour to avoid overwhelming the GitHub API.
    """
    logger.info("Updating GitHub details for guru types")
    
    from core.requester import GitHubRequester
    from django.utils import timezone
    from datetime import timedelta
    
    github_requester = GitHubRequester()
    
    # Get guru types that haven't been updated in the last 24 hours
    # Order by github_details_updated_date to prioritize oldest updates
    cutoff_time = timezone.now() - timedelta(days=1)
    guru_types = GuruType.objects.filter(
        models.Q(github_details_updated_date__isnull=True) | 
        models.Q(github_details_updated_date__lt=cutoff_time),
        github_repos__isnull=False,
        github_repos__len__gt=0,  # Has at least one repo
        active=True
    ).order_by('github_details_updated_date')[:200]
    logger.info(f'Guru types to update: {guru_types.count()} with cutoff time: {cutoff_time}')
    
    updated_count = 0
    for guru_type in guru_types:
        try:
            # Get details for all repos
            all_details = []
            for repo_url in guru_type.github_repos:
                try:
                    details = github_requester.get_github_repo_details(repo_url)
                    all_details.append(details)
                except Exception as e:
                    logger.error(f"Error getting GitHub details for {repo_url}: {traceback.format_exc()}")
                    continue
            
            if all_details:  # Only update if we got at least one repo's details
                guru_type.github_details = all_details
                guru_type.github_details_updated_date = timezone.now()
                guru_type.save()
                updated_count += 1
                logger.info(f'Updated GitHub details for {guru_type.slug}')
        except Exception as e:
            logger.error(f"Error updating GitHub details for {guru_type.slug}: {traceback.format_exc()}")
            # Still update the timestamp to avoid repeatedly trying failed updates
            guru_type.github_details_updated_date = timezone.now()
            guru_type.save()
            continue
            
    logger.info(f'Updated GitHub details for {updated_count} guru types')

@shared_task
@with_redis_lock(
    redis_client,
    'update_guru_type_sitemap_status_lock',
    1800
)
def update_guru_type_sitemap_status():
    """
    Updates has_sitemap_added_questions field for all GuruTypes based on whether they have
    any questions with add_to_sitemap=True. Uses efficient batch processing to handle large datasets.
    """
    logger.info("Updating GuruType sitemap status")
    
    # Create a subquery to check for questions with add_to_sitemap=True
    questions_subquery = Question.objects.filter(
        guru_type=OuterRef('pk'),
        add_to_sitemap=True
    )
    
    # Annotate GuruTypes with whether they have sitemap questions
    guru_types = GuruType.objects.annotate(
        has_sitemap_questions=Exists(questions_subquery)
    )
    
    # Prepare bulk updates
    to_update = []
    batch_size = 1000
    
    for guru_type in guru_types.iterator(chunk_size=100):
        if guru_type.has_sitemap_added_questions != guru_type.has_sitemap_questions:
            guru_type.has_sitemap_added_questions = guru_type.has_sitemap_questions
            to_update.append(guru_type)
            
            # Process in batches to avoid memory issues
            if len(to_update) >= batch_size:
                GuruType.objects.bulk_update(to_update, ['has_sitemap_added_questions'])
                to_update = []
    
    # Update any remaining records
    if to_update:
        GuruType.objects.bulk_update(to_update, ['has_sitemap_added_questions'])
    
    logger.info("Completed updating GuruType sitemap status")

@shared_task
def update_github_repositories(successful_repos=True):
    """
    Periodic task to update GitHub repositories:
    1. For each successfully synced GitHub repo data source, clone the repo again
    2. Check each file's modification date against the data source's last update
    3. Update modified files in both DB and Milvus
    
    Uses per-guru-type locking to allow parallel processing of different guru types.
    """

    def process_guru_type(guru_type):
        from core.github.data_source_handler import clone_repository, read_repository
        from django.db import transaction
        import os
        from datetime import datetime        
        logger.info(f"Processing GitHub repositories for guru type: {guru_type.slug}")
        
        # Get all GitHub repo data sources for this guru type
        status = DataSource.Status.SUCCESS if successful_repos else DataSource.Status.FAIL
        data_sources = DataSource.objects.filter(
            type=DataSource.Type.GITHUB_REPO,
            status=status,
            guru_type=guru_type
        )
        
        for data_source in data_sources:
            try:
                # Clone the repository
                temp_dir, repo = clone_repository(data_source.url)
                
                try:
                    # Read the repository structure
                    structure = read_repository(
                        temp_dir, 
                        data_source.github_glob_include, 
                        data_source.github_glob_pattern)

                    if len(structure) > data_source.guru_type.github_file_count_limit_per_repo_hard:
                        raise GithubRepoFileCountLimitError(
                            f"The codebase ({len(structure)}) exceeds the maximum file limit of {data_source.guru_type.github_file_count_limit_per_repo_hard} files supported."
                        )

                    # Calculate total size
                    total_size = sum(file['size'] for file in structure)
                    if total_size > data_source.guru_type.github_repo_size_limit_mb * 1024 * 1024:
                        raise GithubRepoSizeLimitError(
                            f"The codebase ({total_size / (1024 * 1024):.2f} MB) exceeds the maximum size limit of {data_source.guru_type.github_repo_size_limit_mb} MB supported."
                        )
                    
                    # Get existing files for this data source
                    existing_files = {
                        f.path: f for f in GithubFile.objects.filter(data_source=data_source)
                    }
                    
                    # Track current files in repo
                    current_paths = {file_info['path'] for file_info in structure}
                    
                    files_to_delete = []
                    files_to_create = []
                    
                    # Find deleted files
                    deleted_files = [
                        existing_files[path] for path in existing_files.keys() 
                        if path not in current_paths
                    ]
                    files_to_delete.extend(deleted_files)
                    
                    # Process each file in the new structure
                    for file_info in structure:
                        path = file_info['path']
                        content = file_info['content']
                        size = file_info['size']
                        
                        # Get the file's last modification timestamp from git
                        file_path = os.path.join(temp_dir, path)
                        try:
                            # Get the last commit that modified this file
                            last_commit = next(repo.iter_commits(paths=path))
                            last_modified = datetime.fromtimestamp(last_commit.committed_date, tz=UTC)
                        except Exception as e:
                            logger.warning(f"Could not get last commit for {path}: {str(e)}")
                            continue
                        
                        if path in existing_files:
                            existing_file = existing_files[path]
                            # Check if file was modified after our last update
                            if last_modified > existing_file.date_updated:
                                # Mark for deletion and recreation
                                files_to_delete.append(existing_file)
                                files_to_create.append(
                                    GithubFile(
                                        data_source=data_source,
                                        path=path,
                                        content=content,
                                        size=size,
                                        link=f'{data_source.url}/tree/{data_source.default_branch}/{path}'
                                    )
                                )
                        else:
                            # New file, just create it
                            files_to_create.append(
                                GithubFile(
                                    data_source=data_source,
                                    path=path,
                                    content=content,
                                    size=size,
                                    link=f'{data_source.url}/tree/{data_source.default_branch}/{path}'
                                )
                            )
                    
                    # Bulk process the changes in a transaction
                    if files_to_delete or files_to_create:
                        with transaction.atomic():
                            # Delete from DB (no need to delete from Milvus as it is handled by signals)
                            if files_to_delete:
                                deleted_count = GithubFile.objects.filter(
                                    id__in=[f.id for f in files_to_delete]
                                ).delete()
                                logger.info(f"Deleted {deleted_count} files for data source {data_source.id}")
                            
                            # Create new files in DB
                            if files_to_create:
                                created_files = GithubFile.objects.bulk_create(files_to_create)
                                logger.info(f"Created {len(created_files)} files for data source {str(data_source)}")
                        
                        # Update data source timestamp
                        data_source.doc_ids = DataSource.objects.get(id=data_source.id).doc_ids # Reflect the latest doc_ids updated by the signals
                        data_source.save()  # This will update date_updated

                    data_source.in_milvus = False
                    data_source.error = ""
                    data_source.user_error = ""
                    data_source.status = DataSource.Status.SUCCESS
                    data_source.last_successful_index_date = datetime.now()
                    data_source.save()
                    data_source.write_to_milvus()

                finally:
                    # Clean up
                    repo.close()
                    os.system(f"rm -rf {temp_dir}")
                    
            except GithubInvalidRepoError as e:
                error_msg = f"Error processing repository {data_source.url}: {traceback.format_exc()}"
                logger.error(error_msg)
                data_source.error = error_msg
                data_source.status = DataSource.Status.FAIL
                if data_source.last_successful_index_date:
                    user_error = f"An issue occurred while reindexing the codebase. The repository may have been deleted, made private, or renamed. Please verify that the repository still exists and is public. No worries though - this guru still uses the codebase indexed on {data_source.last_successful_index_date.strftime('%B %d')}. Reindexing will be attempted again later."
                else:
                    user_error = str(e)
                data_source.user_error = user_error
                data_source.error = error_msg
                data_source.save()
                continue
            except GithubRepoSizeLimitError as e:
                error_msg = f"Error processing repository {data_source.url}: {traceback.format_exc()}"
                logger.error(error_msg)
                data_source.error = error_msg
                data_source.status = DataSource.Status.FAIL
                if data_source.last_successful_index_date:
                    user_error = f"An issue occurred while reindexing the codebase. The repository size ({total_size / (1024 * 1024):.2f} MB) has grown beyond our size limit of {data_source.guru_type.github_repo_size_limit_mb} MB. No worries though - this guru still uses the codebase indexed on {data_source.last_successful_index_date.strftime('%B %d')}. Reindexing will be attempted again later."
                else:
                    user_error = str(e)
                data_source.user_error = user_error
                data_source.error = error_msg
                data_source.save()
                continue
            except GithubRepoFileCountLimitError as e:
                error_msg = f"Error processing repository {data_source.url}: {traceback.format_exc()}"
                logger.error(error_msg)
                data_source.error = error_msg
                data_source.status = DataSource.Status.FAIL
                if data_source.last_successful_index_date:
                    user_error = f"An issue occurred while reindexing the codebase. The repository has grown to {len(structure)} files, which exceeds our file count limit of {data_source.guru_type.github_file_count_limit_per_repo_hard} files. No worries though - this guru still uses the codebase indexed on {data_source.last_successful_index_date.strftime('%B %d')}. Reindexing will be attempted again later."
                else:
                    user_error = str(e)
                data_source.user_error = user_error
                data_source.error = error_msg
                data_source.save()
                continue
            except Exception as e:
                error_msg = f"Error processing repository {data_source.url}: {traceback.format_exc()}"
                logger.error(error_msg)
                data_source.error = error_msg
                data_source.status = DataSource.Status.FAIL
                if data_source.last_successful_index_date:
                    user_error = f"An issue occurred while reindexing the codebase. No worries though - this guru still uses the codebase indexed on {data_source.last_successful_index_date.strftime('%B %d')}. Reindexing will be attempted again later."
                else:
                    user_error = "Failed to index the repository. Please try again or contact support if the issue persists."
                data_source.user_error = user_error
                data_source.error = error_msg
                data_source.save()
                continue
        
        logger.info(f"Completed processing GitHub repositories for guru type: {guru_type.slug}")

    logger.info("Starting GitHub repositories update task")
    
    # Get unique guru types that have GitHub repo data sources
    guru_types = GuruType.objects.filter(
        datasource__type=DataSource.Type.GITHUB_REPO,
        # datasource__status=DataSource.Status.SUCCESS,
    ).distinct()

    for guru_type in guru_types:
        try:
            process_guru_type(guru_type=guru_type)
        except Exception as e:
            logger.error(f"Error processing guru type {guru_type.slug}: {traceback.format_exc()}")
            continue
    
    logger.info("Completed GitHub repositories update task")

@shared_task
def crawl_website(url: str, crawl_state_id: int, link_limit: int, language_code: str):
    """
    Celery task to crawl a website and collect internal links.
    
    Args:
        url (str): The URL to crawl
        crawl_state_id (int): ID of the CrawlState object to update during crawling
        link_limit (int): Maximum number of links to collect
    """
    try:
        get_internal_links(url, crawl_state_id=crawl_state_id, link_limit=link_limit, language_code=language_code)
    except Exception as e:
        logger.error(f"Error in crawl_website task: {str(e)}", exc_info=True)
        # Update crawl state to failed
        from core.models import CrawlState
        try:
            crawl_state = CrawlState.objects.get(id=crawl_state_id)
            crawl_state.status = CrawlState.Status.FAILED
            crawl_state.error_message = str(e)
            crawl_state.end_time = timezone.now()
            crawl_state.save()
        except Exception as e:
            logger.error(f"Error updating crawl state: {str(e)}", exc_info=True)

@shared_task(ignore_result=True, task_track_started=False)
def stop_inactive_ui_crawls():
    """
    Periodic task to stop UI crawls that haven't been polled for more than 10 seconds
    """
    threshold_seconds = settings.CRAWL_INACTIVE_THRESHOLD_SECONDS
    inactivity_threshold = now() - timedelta(seconds=threshold_seconds)
    
    inactive_crawls = CrawlState.objects.filter(
        source=CrawlState.Source.UI,
        status=CrawlState.Status.RUNNING,
        last_polled_at__lt=inactivity_threshold
    )
    
    for crawl in inactive_crawls:
        crawl.status = CrawlState.Status.STOPPED
        crawl.end_time = now()
        crawl.error_message = f"Crawl automatically stopped due to inactivity (no status checks for over {threshold_seconds} seconds)"
        crawl.save()
        
    # return f"Stopped {inactive_crawls.count()} inactive UI crawls"

@shared_task
def reindex_text_embedding_model(guru_type_id: int, old_model: str, new_model: str, old_dimension: int | None = None, new_dimension: int | None = None):
    """
    Task to reindex non-Github data sources when text_embedding_model changes.
    
    Args:
        guru_type_id: ID of the GuruType being updated
        old_model: Previous text embedding model name
        new_model: New text embedding model name
    """
    logger.info(f"Starting text embedding model reindexing for guru type {guru_type_id}")
    try:
        guru_type = GuruType.objects.get(id=guru_type_id)
        
        # Get all non-Github data sources for this guru type
        non_github_data_sources = DataSource.objects.filter(
            guru_type=guru_type
        ).exclude(type=DataSource.Type.GITHUB_REPO)

        non_github_data_sources.update(status=DataSource.Status.NOT_PROCESSED)
        
        if old_dimension is None:
            _, old_dimension = get_embedding_model_config(old_model, sync=False)
        if new_dimension is None:
            _, new_dimension = get_embedding_model_config(new_model, sync=False)

        if old_dimension != new_dimension:
            milvus_utils.drop_collection(guru_type.milvus_collection_name)
        
        # First delete from old collection
        for ds in non_github_data_sources:
            # Trigger delete from milvus anyways even if we drop the collection, to set their in_milvus = False and doc_ids = []
            ds.delete_from_milvus(overridden_model=old_model)

        if old_dimension != new_dimension:
            milvus_utils.create_context_collection(guru_type.milvus_collection_name, new_dimension)
        
        # Then write to new collection
        for ds in non_github_data_sources:
            ds.write_to_milvus(overridden_model=new_model)  # This will use the new model's collection

        non_github_data_sources.update(status=DataSource.Status.SUCCESS)
            
        logger.info(f"Completed text embedding model reindexing for guru type {guru_type_id}")
    except Exception as e:
        logger.error(f"Error during text embedding model reindexing for guru type {guru_type_id}: {traceback.format_exc()}")
        if non_github_data_sources.exists():
            non_github_data_sources.update(status=DataSource.Status.FAIL)
        raise


@shared_task
def reindex_code_embedding_model(guru_type_id: int, old_model: str, new_model: str):
    """
    Task to reindex GitHub repos when code_embedding_model changes.
    
    Args:
        guru_type_id: ID of the GuruType being updated
        old_model: Previous code embedding model name
        new_model: New code embedding model name
    """
    logger.info(f"Starting code embedding model reindexing for guru type {guru_type_id}")
    try:
        guru_type = GuruType.objects.get(id=guru_type_id)
        
        # Get all GitHub repos for this guru type
        github_repos = DataSource.objects.filter(
            guru_type=guru_type,
            type=DataSource.Type.GITHUB_REPO
        )

        github_repos.update(status=DataSource.Status.NOT_PROCESSED)
        
        # First delete from old collection
        for repo in github_repos:
            repo.delete_from_milvus(overridden_model=old_model)  # This will use the old model's collection
        
        # Then write to new collection
        for repo in github_repos:
            repo.write_to_milvus(overridden_model=new_model)  # This will use the new model's collection

        github_repos.update(status=DataSource.Status.SUCCESS)

        logger.info(f"Completed code embedding model reindexing for guru type {guru_type_id}")
    except Exception as e:
        logger.error(f"Error during code embedding model reindexing for guru type {guru_type_id}: {traceback.format_exc()}")
        if github_repos.exists():
            github_repos.update(status=DataSource.Status.FAIL)
        raise


@shared_task
@with_redis_lock(
    redis_client,
    'scrape_main_content_lock',
    1800
)
def scrape_main_content(data_source_ids: List[int]):
    """
    Scrape the main content of a list of data sources using Gemini to extract the main content from HTML.
    Updates Milvus immediately after processing each data source.
    Skips data sources that have already been rewritten or are not in a success status.
    
    Args:
        data_source_ids: List of DataSource IDs to process
    """
    logger.info(f"Starting to scrape main content for {len(data_source_ids)} data sources")
    
    from core.models import DataSource
    data_sources = DataSource.objects.filter(id__in=data_source_ids)
    
    for data_source in data_sources:
        data_source.scrape_main_content()
    
    logger.info("Completed scraping main content for all data sources")
