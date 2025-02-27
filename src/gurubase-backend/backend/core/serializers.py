from rest_framework import serializers
from core.models import WidgetId, Binge, DataSource, GuruType, Question, FeaturedDataSource, APIKey, Settings, CrawlState
from core.gcp import replace_media_root_with_nginx_base_url

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'


class QuestionCopySerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        exclude = ['id', 'similar_questions']
        
    def to_representation(self, instance):
        repr = super().to_representation(instance)
        repr['guru_type'] = instance.guru_type.name
        return repr
        
    def create(self, validated_data):
        guru_type_obj = GuruType.objects.get(slug=validated_data.pop('guru_type'), active=True)
        validated_data['guru_type'] = guru_type_obj
        return Question.objects.create(**validated_data)


class FeaturedDataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeaturedDataSource
        fields = '__all__'

        
class GuruTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuruType
        exclude = ['date_created', 'date_updated', 'id', 'milvus_collection_name', 'typesense_collection_name']

    def to_representation(self, instance):
        instance.icon_url = replace_media_root_with_nginx_base_url(instance.icon_url)
        repr = super().to_representation(instance)
        repr['ready'] = instance.ready
        return repr

        
class GuruTypeInternalSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuruType
        fields = ['slug', 'name', 'colors', 'icon_url']

    def to_representation(self, instance):
        if not instance.name:
            instance.name = instance.slug
            instance.save()
        instance.icon_url = replace_media_root_with_nginx_base_url(instance.icon_url)
        repr = super().to_representation(instance)
        
        colors = repr.pop('colors') or {}
        repr['colors'] = [
            colors.get('base_color', '#FF0000'),
            colors.get('light_color', '#FAFAFA')
        ]
        
        return repr
    
class WidgetIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = WidgetId
        fields = ['key', 'domain_url']



class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        exclude = ['file', 'doc_ids', 'content', 'guru_type']

    def to_representation(self, instance):
        from core.utils import format_github_repo_error
        repr = super().to_representation(instance)
        if instance.type == DataSource.Type.PDF:
            del repr['url']

        if instance.type == DataSource.Type.GITHUB_REPO:
            if instance.error:
                repr['error'] = format_github_repo_error(instance.error, instance.user_error)
        return repr

class DataSourceAPISerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = ['id', 'type', 'url', 'title', 'status', 'error', 'date_created', 'private', 'last_reindex_date', 'reindex_count']

    def to_representation(self, instance):
        from core.utils import format_github_repo_error
        repr = super().to_representation(instance)
        if instance.type == DataSource.Type.PDF:
            del repr['url']

        if instance.type == DataSource.Type.GITHUB_REPO:
            if instance.error:
                repr['error'] = format_github_repo_error(instance.error, instance.user_error)
        return repr


class BingeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Binge
        fields = ['last_used', 'id']

    def to_representation(self, instance):
        if not instance.root_question:
            return None
            
        repr = super().to_representation(instance)
        repr['guru_type_slug'] = instance.guru_type.slug
        repr['root_question_name'] = instance.root_question.question
        repr['root_question_slug'] = instance.root_question.slug
        return repr
        
    @classmethod
    def serialize_binges(cls, binges, many=True):
        # Filter out binges with null root_question
        valid_binges = [binge for binge in binges if binge.root_question]
        return cls(valid_binges, many=many).data

class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ['id', 'key', 'name', 'date_created']

class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settings
        fields = ['openai_api_key', 'is_openai_key_valid', 'firecrawl_api_key', 'is_firecrawl_key_valid', 'scrape_type']
        extra_kwargs = {
            'openai_api_key': {'write_only': True},  # Ensure API key is write-only for security
            'is_openai_key_valid': {'read_only': True},  # This field is computed on save
            'firecrawl_api_key': {'write_only': True},
            'is_firecrawl_key_valid': {'read_only': True}
        }

    def to_representation(self, instance):
        repr = super().to_representation(instance)
        
        # Mask API keys if they exist with fixed 10 asterisks
        if instance.openai_api_key:
            key = instance.openai_api_key
            repr['openai_api_key'] = f"{key[:3]}{'.' * 10}{key[-4:]}"
            
        if instance.firecrawl_api_key:
            key = instance.firecrawl_api_key
            repr['firecrawl_api_key'] = f"{key[:3]}{'.' * 10}{key[-4:]}"
            
        return repr


class CrawlStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrawlState
        fields = ['id', 'url', 'status', 'guru_type', 'discovered_urls', 'start_time', 'end_time']

    def to_representation(self, instance):
        repr = super().to_representation(instance)
        repr['guru_type'] = instance.guru_type.slug
        return repr
