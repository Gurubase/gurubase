from typing import List, Dict, Any
from django.core.files.uploadedfile import UploadedFile

from core.models import DataSource, GuruType
from core.data_sources import PDFStrategy, YouTubeStrategy, WebsiteStrategy
from core.utils import clean_data_source_urls
from core.tasks import data_source_retrieval


class DataSourceService:
    """Service layer for data source CRUD operations"""
    
    def __init__(self, guru_type_object: GuruType, user):
        self.guru_type_object = guru_type_object
        self.user = user
        self.strategies = {
            'pdf': PDFStrategy(),
            'youtube': YouTubeStrategy(),
            'website': WebsiteStrategy()
        }

    def validate_pdf_files(self, pdf_files: List[UploadedFile], pdf_privacies: List[bool]) -> None:
        """
        Validates PDF files and their privacy settings
        
        Args:
            pdf_files: List of uploaded PDF files
            pdf_privacies: List of privacy settings corresponding to each PDF file
            
        Raises:
            ValueError: If validation fails
        """
        if len(pdf_privacies) != len(pdf_files):
            raise ValueError('Number of privacy settings must match number of PDF files')
        
        for pdf_file in pdf_files:
            is_allowed, error_msg = self.guru_type_object.check_datasource_limits(self.user, file=pdf_file)
            if not is_allowed:
                raise ValueError(error_msg)

    def validate_url_limits(self, urls: List[str], url_type: str) -> None:
        """
        Validates URL count limits
        
        Args:
            urls: List of URLs to validate
            url_type: Type of URLs ('website' or 'youtube')
            
        Raises:
            ValueError: If validation fails
        """
        if urls:
            is_allowed, error_msg = self.guru_type_object.check_datasource_limits(
                self.user, 
                website_urls_count=len(urls) if url_type == 'website' else 0,
                youtube_urls_count=len(urls) if url_type == 'youtube' else 0
            )
            if not is_allowed:
                raise ValueError(error_msg)

    def create_data_sources(
        self, 
        pdf_files: List[UploadedFile], 
        pdf_privacies: List[bool], 
        youtube_urls: List[str], 
        website_urls: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Creates data sources of different types
        
        Args:
            pdf_files: List of uploaded PDF files
            pdf_privacies: List of privacy settings for PDF files
            youtube_urls: List of YouTube URLs
            website_urls: List of website URLs
            
        Returns:
            List of created data source results
        """
        results = []
        
        # Process PDF files
        for i, pdf_file in enumerate(pdf_files):
            results.append(self.strategies['pdf'].create(self.guru_type_object, pdf_file, pdf_privacies[i]))

        # Process YouTube URLs
        clean_youtube_urls = clean_data_source_urls(youtube_urls)
        for url in clean_youtube_urls:
            results.append(self.strategies['youtube'].create(self.guru_type_object, url))

        # Process website URLs
        clean_website_urls = clean_data_source_urls(website_urls)
        for url in clean_website_urls:
            results.append(self.strategies['website'].create(self.guru_type_object, url))

        # Trigger background task
        data_source_retrieval.delay(guru_type_slug=self.guru_type_object.slug)
        
        return results

    def update_privacy_settings(self, data_sources: List[Dict[str, Any]]) -> None:
        """
        Updates privacy settings for data sources
        
        Args:
            data_sources: List of data source objects with privacy settings
            
        Raises:
            ValueError: If no data sources provided
        """
        if not data_sources:
            raise ValueError('No data sources provided')

        # Group data sources by private value
        private_ids = [ds['id'] for ds in data_sources if ds.get('private', False)]
        non_private_ids = [ds['id'] for ds in data_sources if not ds.get('private', False)]

        # Perform bulk updates
        if private_ids:
            data_sources = DataSource.objects.filter(
                id__in=private_ids,
                guru_type=self.guru_type_object,
                type=DataSource.Type.PDF
            )
            if len(data_sources) == 0:
                raise ValueError('No PDF data sources found to update')
            data_sources.update(private=True)

        if non_private_ids:
            data_sources = DataSource.objects.filter(
                id__in=non_private_ids,
                guru_type=self.guru_type_object,
                type=DataSource.Type.PDF
            )
            if len(data_sources) == 0:
                raise ValueError('No PDF data sources found to update')
            data_sources.update(private=False)

    def reindex_data_sources(self, datasource_ids: List[str]) -> None:
        """
        Reindexes specified data sources
        
        Args:
            datasource_ids: List of data source IDs to reindex
            
        Raises:
            ValueError: If no valid data sources found
        """
        if not datasource_ids:
            raise ValueError('No data sources provided')
        
        datasources = DataSource.objects.filter(id__in=datasource_ids, guru_type=self.guru_type_object)
        if not datasources:
            raise ValueError('No data sources found to reindex')
        
        for datasource in datasources:
            datasource.reindex()

        data_source_retrieval.delay(guru_type_slug=self.guru_type_object.slug)

    def delete_data_sources(self, datasource_ids: List[str]) -> None:
        """
        Deletes specified data sources
        
        Args:
            datasource_ids: List of data source IDs to delete
            
        Raises:
            ValueError: If no valid data sources found
        """
        if not datasource_ids:
            raise ValueError('No data sources provided')
        
        data_sources = DataSource.objects.filter(guru_type=self.guru_type_object, id__in=datasource_ids)
        if not data_sources:
            raise ValueError('No data sources found to delete')
        
        data_sources.delete() 