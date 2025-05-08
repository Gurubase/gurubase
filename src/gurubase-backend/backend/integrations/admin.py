from django.contrib import admin

from integrations.models import Integration, Thread, WidgetId

# Register your models here.

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


@admin.register(WidgetId)
class WidgetIdAdmin(admin.ModelAdmin):
    list_display = ['id', 'guru_type', 'key', 'domain_url', 'domain', 'date_created']
    search_fields = ['id', 'guru_type__slug', 'key', 'domain_url']
    list_filter = ('guru_type__slug', )
    ordering = ('-id',)
    raw_id_fields = ('guru_type',)