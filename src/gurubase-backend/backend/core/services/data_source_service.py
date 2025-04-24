from typing import List, Dict, Any
from django.core.files.uploadedfile import UploadedFile

from core.models import DataSource, GuruType, Integration
from core.data_sources import JiraStrategy, PDFStrategy, YouTubeStrategy, WebsiteStrategy, ZendeskStrategy, GitHubStrategy, ConfluenceStrategy
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
            'website': WebsiteStrategy(),
            'jira': JiraStrategy(),
            'zendesk': ZendeskStrategy(),
            'github': GitHubStrategy(),
            'confluence': ConfluenceStrategy()
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

    def validate_url_limits(self, youtube_urls=None, website_urls=None, jira_urls=None, zendesk_urls=None, confluence_urls=None) -> None:
        """
        Validates URL count limits for multiple URL types
        
        Args:
            youtube_urls: List of YouTube URLs to validate
            website_urls: List of website URLs to validate
            jira_urls: List of Jira URLs to validate
            zendesk_urls: List of Zendesk URLs to validate
            confluence_urls: List of Confluence URLs to validate
        Raises:
            ValueError: If validation fails
        """
        youtube_urls = youtube_urls or []
        website_urls = website_urls or []
        jira_urls = jira_urls or []
        zendesk_urls = zendesk_urls or []
        confluence_urls = confluence_urls or []
        if any([youtube_urls, website_urls, jira_urls, zendesk_urls, confluence_urls]):
            is_allowed, error_msg = self.guru_type_object.check_datasource_limits(
                self.user, 
                website_urls_count=len(website_urls),
                youtube_urls_count=len(youtube_urls),
                jira_urls_count=len(jira_urls),
                zendesk_urls_count=len(zendesk_urls),
                confluence_urls_count=len(confluence_urls)
            )
            if not is_allowed:
                raise ValueError(error_msg)

    def validate_integration(self, type: str) -> None:
        """
        Validates integration
        
        Args:
            type: Type of integration ('jira' or 'zendesk' or 'confluence')
            
        """
        if type == 'jira':
            jira_integration = Integration.objects.filter(guru_type=self.guru_type_object, type=Integration.Type.JIRA).first()
            if not jira_integration:
                raise ValueError('Jira integration not found')
        elif type == 'zendesk':
            zendesk_integration = Integration.objects.filter(guru_type=self.guru_type_object, type=Integration.Type.ZENDESK).first()
            if not zendesk_integration:
                raise ValueError('Zendesk integration not found')
        elif type == 'confluence':
            confluence_integration = Integration.objects.filter(guru_type=self.guru_type_object, type=Integration.Type.CONFLUENCE).first()
            if not confluence_integration:
                raise ValueError('Confluence integration not found')

    def validate_github_repos_limits(self, github_repos: List[Dict[str, Any]]) -> None:
        """
        Validates GitHub repos count limits for new repos only
        
        Args:
            github_repos: List of GitHub repos to validate - should only contain new repos
            
        Raises:
            ValueError: If validation fails
        """
        if github_repos:
            is_allowed, error_msg = self.guru_type_object.check_datasource_limits(
                self.user,
                github_repos_count=len(github_repos)
            )
            if not is_allowed:
                raise ValueError(error_msg)

    def identify_new_github_repos(self, github_repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify GitHub repos that don't exist in the system yet
        
        Args:
            github_repos: List of GitHub repo dictionaries
            
        Returns:
            List of GitHub repos that don't exist and need to be created
        """
        new_repos = []
        
        for repo in github_repos:
            repo_url = repo.get('url', '')
            
            # Check if this repo already exists in this guru type
            existing_repo = DataSource.objects.filter(
                guru_type=self.guru_type_object, 
                type=DataSource.Type.GITHUB_REPO,
                url=repo_url
            ).exists()
            
            if not existing_repo:
                # Add to list of new repos to create
                new_repos.append(repo)
                
        return new_repos
        
    def update_existing_github_repos(self, github_repos: List[Dict[str, Any]]) -> None:
        """
        Update glob patterns for existing GitHub repos
        
        Args:
            github_repos: List of GitHub repo dictionaries with 'url' and 'glob_patterns' fields
        """
        updated_repos = []
        for repo in github_repos:
            repo_url = repo.get('url', '')
            
            # Check if this repo already exists in this guru type
            existing_repo = DataSource.objects.filter(
                guru_type=self.guru_type_object, 
                type=DataSource.Type.GITHUB_REPO,
                url=repo_url
            ).first()
            
            if existing_repo:
                # Update glob patterns
                existing_repo.github_glob_pattern = repo['glob_pattern']
                existing_repo.github_glob_include = repo['include_glob']
                existing_repo.save()
                updated_repos.append(existing_repo)

        return updated_repos

    def process_github_repos(self, github_repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process GitHub repos, updating existing ones and returning new ones to be created
        
        Args:
            github_repos: List of GitHub repo dictionaries with 'url' and 'glob_patterns' fields
            
        Returns:
            List of GitHub repos that need to be created (didn't exist before)
        """
        # Identify new repos
        new_repos = self.identify_new_github_repos(github_repos)
        
        # Update existing repos
        self.update_existing_github_repos(github_repos)
                
        return new_repos

    def validate_github_repos_limits(self, github_repos: List[Dict[str, Any]]) -> None:
        """
        Validates GitHub repos count limits for new repos only
        
        Args:
            github_repos: List of GitHub repos to validate - should only contain new repos
            
        Raises:
            ValueError: If validation fails
        """
        if github_repos:
            is_allowed, error_msg = self.guru_type_object.check_datasource_limits(
                self.user,
                github_repos_count=len(github_repos)
            )
            if not is_allowed:
                raise ValueError(error_msg)

    def identify_new_github_repos(self, github_repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify GitHub repos that don't exist in the system yet
        
        Args:
            github_repos: List of GitHub repo dictionaries
            
        Returns:
            List of GitHub repos that don't exist and need to be created
        """
        new_repos = []
        
        for repo in github_repos:
            repo_url = repo.get('url', '')
            
            # Check if this repo already exists in this guru type
            existing_repo = DataSource.objects.filter(
                guru_type=self.guru_type_object, 
                type=DataSource.Type.GITHUB_REPO,
                url=repo_url
            ).exists()
            
            if not existing_repo:
                # Add to list of new repos to create
                new_repos.append(repo)
                
        return new_repos
        
    def update_existing_github_repos(self, github_repos: List[Dict[str, Any]]) -> None:
        """
        Update glob patterns for existing GitHub repos
        
        Args:
            github_repos: List of GitHub repo dictionaries with 'url' and 'glob_patterns' fields
        """
        updated_repos = []
        for repo in github_repos:
            repo_url = repo.get('url', '')
            
            # Check if this repo already exists in this guru type
            existing_repo = DataSource.objects.filter(
                guru_type=self.guru_type_object, 
                type=DataSource.Type.GITHUB_REPO,
                url=repo_url
            ).first()
            
            if existing_repo:
                # Update glob patterns
                existing_repo.github_glob_pattern = repo['glob_pattern']
                existing_repo.github_glob_include = repo['include_glob']
                existing_repo.save()
                updated_repos.append(existing_repo)

        return updated_repos

    def process_github_repos(self, github_repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process GitHub repos, updating existing ones and returning new ones to be created
        
        Args:
            github_repos: List of GitHub repo dictionaries with 'url' and 'glob_patterns' fields
            
        Returns:
            List of GitHub repos that need to be created (didn't exist before)
        """
        # Identify new repos
        new_repos = self.identify_new_github_repos(github_repos)
        
        # Update existing repos
        self.update_existing_github_repos(github_repos)
                
        return new_repos

    def create_data_sources(
        self, 
        pdf_files: List[UploadedFile], 
        pdf_privacies: List[bool], 
        youtube_urls: List[str], 
        website_urls: List[str],
        jira_urls: List[str],
        zendesk_urls: List[str],
        github_repos: List[Dict[str, Any]],
        confluence_urls: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Creates data sources of different types
        
        Args:
            pdf_files: List of uploaded PDF files
            pdf_privacies: List of privacy settings for PDF files
            youtube_urls: List of YouTube URLs
            website_urls: List of website URLs
            jira_urls: List of Jira URLs
            zendesk_urls: List of Zendesk URLs
            github_repos: List of GitHub repos
            confluence_urls: List of Confluence URLs
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

        # Process Jira URLs
        clean_jira_urls = clean_data_source_urls(jira_urls)
        for url in clean_jira_urls:
            results.append(self.strategies['jira'].create(self.guru_type_object, url))

        # Process Zendesk URLs
        clean_zendesk_urls = clean_data_source_urls(zendesk_urls)
        for url in clean_zendesk_urls:
            results.append(self.strategies['zendesk'].create(self.guru_type_object, url))
            
        # Process Confluence URLs
        if confluence_urls:
            clean_confluence_urls = clean_data_source_urls(confluence_urls)
            for url in clean_confluence_urls:
                results.append(self.strategies['confluence'].create(self.guru_type_object, url))

        # Process GitHub repos
        for repo in github_repos:
            results.append(self.strategies['github'].create(self.guru_type_object, repo))

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