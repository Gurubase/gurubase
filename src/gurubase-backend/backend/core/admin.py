from django.conf import settings
from django.contrib import admin
from core.models import (APIKey,
                         Binge, CrawlState, Integration, 
                         LLMEval, 
                         LinkReference, 
                         LinkValidity, 
                         Question, 
                         RawQuestion, 
                         RawQuestionGeneration, 
                         ContentPageStatistics, 
                         GuruType, 
                         DataSource, 
                         Favicon, 
                         FeaturedDataSource, 
                         OutOfContextQuestion, 
                         Summarization, 
                         SummaryQuestionGeneration, 
                         Settings, 
                         LLMEvalResult, 
                         Thread, 
                         WidgetId,
                         GithubFile,
                         GuruCreationForm)
from django.utils.html import format_html
import logging
from django.contrib.admin import SimpleListFilter

logger = logging.getLogger(__name__)

class RepositoryFilter(SimpleListFilter):
    title = 'Repository'  # Display name of the filter
    parameter_name = 'repository'  # URL parameter name

    def lookups(self, request, model_admin):
        # Get unique repositories from all GithubFile objects
        repositories = set()
        for obj in model_admin.model.objects.all():
            if obj.link:
                parts = obj.link.split('/')
                if len(parts) >= 5:
                    repositories.add((f"{parts[3]}/{parts[4]}", f"{parts[3]}/{parts[4]}"))
        return sorted(repositories)

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(link__contains=self.value())
        return queryset

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id',
                    'guru_type',
                    'link',
                    'slug',
                    'question',
                    'user_question',
                    'parent',
                    'binge_link',
                    'is_helpful',
                    'change_count',
                    'add_to_sitemap',
                    'sitemap_reason_link',
                    'sitemap_reason',
                    'sitemap_date',
                    'trust_score',
                    'llm_eval',
                    'default_question',
                    'cost_dollars',
                    'completion_tokens',
                    'prompt_tokens',
                    'cached_prompt_tokens',
                    'total_tokens',
                    'latency_sec',
                    'source',
                    'date_created',
                    'date_updated',
                    ]

    list_filter = ("add_to_sitemap", "default_question", "source", 'guru_type__custom', 'guru_type', 'llm_eval')
    readonly_fields = ("id",)
    search_fields = ['id', 'slug', 'question', 'content', 'description']
    ordering = ('-date_created',)
    actions = ['add_to_sitemap', 'remove_from_sitemap', 'set_default_question', 'set_llm_eval_question', 'unset_llm_eval_question']
    raw_id_fields = ('binge', 'parent')

    def sitemap_reason_link(self, obj):
        if obj.sitemap_reason:
            parts = obj.sitemap_reason.split(': ')
            if len(parts) > 1:
                question_id = parts[-1]
                return format_html(f'<a href="{settings.BACKEND_URL}/admin/core/question/{question_id}/change/" target="_blank">{obj.sitemap_reason}</a>')
        return obj.sitemap_reason
    
    def link(self, obj):
        if not obj.guru_type:
            return ""
        return format_html(f'<a href="{obj.frontend_url}" target="_blank">{obj.slug}</a>')
    
    def binge_link(self, obj):
        if obj.binge:
            return format_html(f'<a href="{settings.BACKEND_URL}/admin/core/binge/{obj.binge.id}/change/" target="_blank">{obj.binge.id}</a>')
        return None
    binge_link.short_description = 'Binge'
    
    def add_to_sitemap(self, request, queryset):
        for question in queryset:
            question.add_to_sitemap = True
            question.save()
        # queryset.update(add_to_sitemap=True)
    add_to_sitemap.short_description = "Add to sitemap"

    def remove_from_sitemap(self, request, queryset):
        for question in queryset:
            question.add_to_sitemap = False
            question.save()
    remove_from_sitemap.short_description = "Remove from sitemap"

    def set_default_question(self, request, queryset):
        queryset.update(default_question=True)
        
    def set_llm_eval_question(self, request, queryset):
        queryset.update(llm_eval=True)

    def unset_llm_eval_question(self, request, queryset):
        queryset.update(llm_eval=False)


@admin.register(RawQuestionGeneration)
class RawQuestionGenerationAdmin(admin.ModelAdmin):
    list_display = ['id', 'guru_type', 'sort', 'page_num', 'page_size', 'generate_count', 'model', 'date_created', 'date_updated']
    list_filter = ('guru_type__slug', "sort", 'model')
    search_fields = ['id', 'guru_type__slug', 'sort']
    ordering = ('-date_created',)


@admin.register(RawQuestion)
class RawQuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'guru_type', 'processed', 'date_created', 'date_updated']
    list_filter = ('guru_type__slug', 'processed')
    search_fields = ['id', 'guru_type__slug']
    ordering = ('-date_created',)


@admin.register(ContentPageStatistics)
class ContentPageStatisticsAdmin(admin.ModelAdmin):
    list_display = ['id', 'question_link', 'view_count', 'upvotes', 'downvotes', 'guru_type']
    search_fields = ['id', 'question__slug']
    ordering = ('-id',)
    list_filter = ('question__guru_type__slug',)
    raw_id_fields = ('question',)

    def question_link(self, obj):
        return format_html(f'<a href="{settings.BACKEND_URL}/admin/core/question/{obj.question.id}/change/" target="_blank">{obj.question.slug}</a>')
    question_link.short_description = 'Question'

    def guru_type(self, obj):
        return obj.question.guru_type
    guru_type.short_description = 'Guru Type'

  
@admin.register(GuruType)
class GuruTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'slug', 'active', 'has_sitemap_added_questions', 'icon_url', 'stackoverflow_tag', 'domain_knowledge', 'colors', 'custom', 'maintainers_list', 'github_repos', 'text_embedding_model', 'code_embedding_model', 'date_created', 'date_updated', 'github_details_updated_date']
    search_fields = ['id', 'slug', 'icon_url', 'stackoverflow_tag', 'domain_knowledge', 'date_created', 'date_updated', 'maintainers__email']
    list_filter = ('active', 'custom', 'has_sitemap_added_questions', 'text_embedding_model', 'code_embedding_model')
    ordering = ('-id',)
    readonly_fields = ('id', 'slug', 'milvus_collection_name', 'typesense_collection_name')
    filter_horizontal = ('maintainers',)

    def maintainers_list(self, obj):
        maintainers = obj.maintainers.all()[:3]  # Limit to first 3
        maintainer_list = ", ".join([user.email for user in maintainers])
        if obj.maintainers.count() > 3:
            maintainer_list += f" (+{obj.maintainers.count() - 3} more)"
        return maintainer_list
    maintainers_list.short_description = 'Maintainers'


@admin.register(LLMEval)
class LLMEvalAdmin(admin.ModelAdmin):
    list_display = ['id', 'question_link', 'question_id', 'model', 'guru_type', 'version', 'context_relevance', 'groundedness', 'answer_relevance', 'cost_dollars', 'prompt_tokens', 'completion_tokens', 'cached_prompt_tokens', 'total_tokens', 'date_created', 'date_updated']
    search_fields = ['id', 'question__slug', 'question__id']
    list_filter = ('model', 'version', 'question__guru_type__slug')
    raw_id_fields = ('question',)
    ordering = ('-id',)
    
    def question_link(self, obj):
        return format_html(f'<a href="{settings.BACKEND_URL}/admin/core/question/{obj.question.id}/change/" target="_blank">{obj.question.slug}</a>')
    question_link.short_description = 'Question'

    def guru_type(self, obj):
        return obj.question.guru_type
    guru_type.short_description = 'Guru Type'

    def question_id(self, obj):
        return format_html(f'<a href="{settings.BACKEND_URL}/admin/core/question/{obj.question.id}/change/" target="_blank">{obj.question.id}</a>')
    question_id.short_description = 'Question ID'


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'url', 'guru_type', 'type', 'status', 'in_milvus', 'private', 'reindex_count', 'initial_summarizations_created', 'final_summarization_created', 'date_created', 'date_updated']
    list_filter = ('type', 'status', 'in_milvus', 'content_rewritten', 'initial_summarizations_created', 'final_summarization_created', 'guru_type__slug', 'reindex_count', 'private')
    search_fields = ['id', 'title', 'guru_type__slug', 'type', 'url']
    ordering = ('-id',)
    actions = ['write_to_milvus', 'delete_from_milvus', 'change_status_to_not_processed', 'reset_initial_summarizations_created', 'reset_final_summarization_created', 'scrape_main_content']

    def write_to_milvus(self, request, queryset):
        for obj in queryset:
            if obj.status == DataSource.Status.NOT_PROCESSED:
                try:
                    obj.write_to_milvus()
                except Exception as e:
                    logger.error(f"Error while writing to milvus: {e}", exc_info=True)

    write_to_milvus.short_description = "Write to Milvus"

    def delete_from_milvus(self, request, queryset):
        for obj in queryset:
            if obj.in_milvus:
                obj.delete_from_milvus()

    delete_from_milvus.short_description = "Delete from Milvus"

    def change_status_to_not_processed(self, request, queryset):
        queryset.update(status=DataSource.Status.NOT_PROCESSED)
    change_status_to_not_processed.short_description = "Change status to not processed"

    def reset_initial_summarizations_created(self, request, queryset):
        queryset.update(initial_summarizations_created=False)
    reset_initial_summarizations_created.short_description = "Reset initial summarizations created"
    
    def reset_final_summarization_created(self, request, queryset):
        queryset.update(final_summarization_created=False)
    reset_final_summarization_created.short_description = "Reset final summarization created"

    def scrape_main_content(self, request, queryset):
        from core.tasks import scrape_main_content
        data_source_ids = list(queryset.values_list('id', flat=True))
        scrape_main_content.delay(data_source_ids)
    scrape_main_content.short_description = "Scrape main content"


@admin.register(Favicon)
class FaviconAdmin(admin.ModelAdmin):
    list_display = ['id', 'domain', 'favicon_url', 'valid']
    search_fields = ['id', 'domain', 'favicon_url', 'valid']
    ordering = ('-id',)


@admin.register(FeaturedDataSource)
class FeaturedDataSourceAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'guru_type', 'type', 'icon_url']
    list_filter = ('guru_type__slug', 'type')
    search_fields = ['id', 'title', 'guru_type__slug', 'type', 'icon_url']
    ordering = ('-id',)


@admin.register(LinkReference)
class LinkReferenceAdmin(admin.ModelAdmin):
    list_display = ['id', 'question_link', 'link', 'valid', 'validity_link']
    search_fields = ['id', 'question__slug', 'url']
    list_filter = ('validity__valid',)
    ordering = ('-question__id',)
    raw_id_fields = ('question',)

    def valid(self, obj):
        if obj.validity:
            return obj.validity.valid
        return None
    valid.short_description = 'Valid'
    
    def question_link(self, obj):
        return format_html(f'<a href="{settings.BACKEND_URL}/admin/core/question/{obj.question.id}/change/" target="_blank">{obj.question.id}-{obj.question.slug}</a>')
    question_link.short_description = 'Question'

    def validity_link(self, obj):
        return format_html(f'<a href="{settings.BACKEND_URL}/admin/core/linkvalidity/{obj.validity.id}/change/" target="_blank">{obj.validity.id}</a>')
    validity_link.short_description = 'Validity'


@admin.register(LinkValidity)
class LinkValidityAdmin(admin.ModelAdmin):
    list_display = ['id', 'link', 'valid', 'response_code']
    search_fields = ['id', 'link', 'valid', 'response_code']
    list_filter = ('valid',)
    ordering = ('-id',)


@admin.register(OutOfContextQuestion)
class OutOfContextQuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'question', 'user_question', 'guru_type', 'source', 'rerank_threshold', 'trust_score_threshold']
    search_fields = ['id', 'question', 'guru_type__name', 'user_question']
    list_filter = ('guru_type__name',)
    ordering = ('-id',)


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ['id', 'rerank_threshold', 'rerank_threshold_llm_eval', 'trust_score_threshold', 'widget_answer_max_length']
    readonly_fields = ('default_embedding_model', )
    ordering = ('-id',)

@admin.register(LLMEvalResult)
class LLMEvalResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'plot_link', 'guru_type', 'version', 'notes', 'context_relevance_avg', 'context_relevance_non_zero_avg', 'context_relevance_non_zero_count', 'groundedness_avg', 'groundedness_non_zero_avg', 'groundedness_non_zero_count', 'answer_relevance_avg', 'answer_relevance_non_zero_avg', 'answer_relevance_non_zero_count', 'total_questions', 'total_cost', 'date_created']
    list_filter = ('guru_type__slug', 'version', 'model')
    search_fields = ['id', 'guru_type__slug', 'version', 'model', 'notes']
    ordering = ('-id',)

    def plot_link(self, obj):
        if obj.plot_url:  # Ensure the URL is not None or empty
            return format_html(f'<a href="{obj.plot_url}" target="_blank">View Plot</a>')
        return "No Plot Available"
    plot_link.short_description = 'Plot'


@admin.register(Summarization)
class SummarizationAdmin(admin.ModelAdmin):
    list_display = ['id', 'data_source_link', 'guru_type_slug_link', 'is_data_source_summarization', 'summary_suitable', 'processed', 'split_num', 'initial', 'is_root', 'ref_list', 'question_generation_link', 'model']
    search_fields = ['id', 'data_source_ref__title', 'is_data_source_summarization', 'processed', 'guru_type__name']
    list_filter = ('summary_suitable', 'is_data_source_summarization', 'processed', 'initial', 'is_root', 'guru_type__slug')
    ordering = ('-id',)
    raw_id_fields = ('data_source_ref', 'guru_type', 'summarization_refs')
    
    actions = ['set_as_not_processed', 'set_as_processed']

    def set_as_not_processed(self, request, queryset):
        queryset.update(processed=False)
    set_as_not_processed.short_description = "Set as not processed"
    
    def set_as_processed(self, request, queryset):
        queryset.update(processed=True)
    set_as_processed.short_description = "Set as processed"

    def ref_list(self, obj):
        # Return summarization_refs as a comma separated list
        return ', '.join([str(ref) for ref in obj.summarization_refs.all()])
    ref_list.short_description = 'Summarization Refs'

    def guru_type_slug_link(self, obj):
        return format_html(f'<a href="{settings.BACKEND_URL}/admin/core/gurutype/{obj.guru_type.id}/change/" target="_blank">{obj.guru_type.slug}</a>')
    guru_type_slug_link.short_description = 'Guru Type Slug'

    def data_source_link(self, obj):
        if obj.data_source_ref:
            return format_html(f'<a href="{settings.BACKEND_URL}/admin/core/datasource/{obj.data_source_ref.id}/change/" target="_blank">{obj.data_source_ref.id} - {obj.data_source_ref.title} </a>')
        return None
    data_source_link.short_description = 'Data Source'
    
    def question_generation_link(self, obj):
        if obj.question_generation_ref:
            return format_html(f'<a href="{settings.BACKEND_URL}/admin/core/summaryquestiongeneration/{obj.question_generation_ref.id}/change/" target="_blank">{obj.question_generation_ref.id}</a>')
        return None
    question_generation_link.short_description = 'Question Generation'


@admin.register(SummaryQuestionGeneration)
class SummaryQuestionGenerationAdmin(admin.ModelAdmin):
    list_display = ['id', 'summarization_link', 'question_link', 'guru_type', 'summary_sufficient', 'processed', 'questions', 'model']
    search_fields = ['id', 'summarization_ref__id', 'guru_type__name']
    list_filter = ('guru_type__name', 'summary_sufficient', 'processed')
    ordering = ('-id',)
    actions = ['set_as_not_processed', 'set_as_processed']
    raw_id_fields = ('question', 'guru_type', 'summarization_ref',)

    def set_as_not_processed(self, request, queryset):
        queryset.update(processed=False)
    set_as_not_processed.short_description = "Set as not processed"
    
    def set_as_processed(self, request, queryset):
        queryset.update(processed=True)
    set_as_processed.short_description = "Set as processed"

    def summarization_link(self, obj):
        if obj.summarization_ref:
            return format_html(f'<a href="{settings.BACKEND_URL}/admin/core/summarization/{obj.summarization_ref.id}/change/" target="_blank">{obj.summarization_ref.id}</a>')
        return None

    def question_link(self, obj):
        if obj.question:
            return format_html(f'<a href="{settings.BACKEND_URL}/admin/core/question/{obj.question.id}/change/" target="_blank">{obj.question.id}</a>')
        return None
    question_link.short_description = 'Question'


@admin.register(Binge)
class BingeAdmin(admin.ModelAdmin):
    list_display = ['id', 'guru_type', 'root_question_link', 'owner_link', 'question_count', 'date_created', 'last_used']
    search_fields = ['id', 'root_question__slug', 'guru_type__name', 'owner__email']
    ordering = ('-date_created',)
    raw_id_fields = ('root_question', 'owner')
    readonly_fields = ('date_created', 'last_used')

    def question_count(self, obj):
        return Question.objects.filter(binge=obj).count()
    question_count.short_description = 'Question Count'

    def root_question_link(self, obj):
        if obj.root_question:
            return format_html(f'<a href="{settings.BACKEND_URL}/admin/core/question/{obj.root_question.id}/change/" target="_blank">{obj.root_question.id}-{obj.root_question.slug}</a>')
        return None
    root_question_link.short_description = 'Root Question'
    
    def owner_link(self, obj):
        if obj.owner:
            return format_html(f'<a href="{settings.BACKEND_URL}/admin/accounts/user/{obj.owner.id}/change/" target="_blank">{obj.owner.email}</a>')
        return None
    owner_link.short_description = 'Owner'

@admin.register(WidgetId)
class WidgetIdAdmin(admin.ModelAdmin):
    list_display = ['id', 'guru_type', 'key', 'domain_url', 'domain', 'date_created']
    search_fields = ['id', 'guru_type__slug', 'key', 'domain_url']
    list_filter = ('guru_type__slug', )
    ordering = ('-id',)
    raw_id_fields = ('guru_type',)


@admin.register(GithubFile)
class GitHubFileAdmin(admin.ModelAdmin):
    list_display = ['id', 'repository_link', 'link_to_file', 'size', 'in_milvus', 'doc_ids']
    list_filter = ('in_milvus', RepositoryFilter, 'data_source__guru_type__slug')
    search_fields = ['id', 'path']
    ordering = ('-id',)

    def repository_link(self, obj):
        return format_html(f'<a href="{obj.repository_link}" target="_blank">{obj.repo_title}</a>')
    repository_link.short_description = 'Repository'

    def link_to_file(self, obj):
        return format_html(f'<a href="{obj.link}" target="_blank">{obj.path}</a>')
    link_to_file.short_description = 'File'


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'integration', 'key', 'date_created', 'date_updated']
    search_fields = ['id', 'user__email', 'key']
    list_filter = ('user__email', 'integration')
    ordering = ('-id',)
    raw_id_fields = ('user',)


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ['id', 'guru_type', 'type', 'workspace_name', 'date_created', 'date_updated']
    list_filter = ('guru_type__slug', 'type')
    search_fields = ['id', 'guru_type__slug', 'type']
    ordering = ('-id',)
    raw_id_fields = ('guru_type',)


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ['id', 'binge', 'integration', 'thread_id', 'date_created', 'date_updated']
    search_fields = ['id', 'binge__id', 'integration__id', 'thread_id']
    list_filter = ('binge__guru_type__slug', 'integration')
    ordering = ('-id',)
    raw_id_fields = ('binge', 'integration')

@admin.register(CrawlState)
class CrawlStateAdmin(admin.ModelAdmin):
    list_display = ['id', 'url', 'guru_type', 'user', 'status', 'start_time', 'end_time', 'error_message']
    list_filter = ('status',)
    search_fields = ['id', 'url']
    ordering = ('-id',)

@admin.register(GuruCreationForm)
class GuruCreationFormAdmin(admin.ModelAdmin):
    list_display = ['id', 'notified', 'source', 'name', 'email', 'github_repo', 'docs_url', 'date_created', 'date_updated']
    search_fields = ['id', 'name', 'email', 'github_repo', 'docs_url', 'use_case']
    list_filter = ('notified', 'source')
    ordering = ('-id',)
