import os
import tempfile
import logging
from git import Repo
from pathlib import Path
from django.conf import settings
from core.exceptions import GitHubRepoContentExtractionError, GithubInvalidRepoError, GithubRepoSizeLimitError, GithubRepoFileCountLimitError

logger = logging.getLogger(__name__)

non_code_extensions = {
    # Documentation
    '.md', '.rst', '.txt', '.pdf', '.doc', '.docx',
    # Data files
    '.json', '.yaml', '.yml', '.xml', '.csv', '.tsv',
    # Config files
    '.env', '.ini', '.cfg', '.conf', '.config',
    # Lock files
    '.lock', '.sum',
    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico',
    # Other assets
    '.ttf', '.woff', '.woff2', '.eot',
    # Package files
    'package.json', 'package-lock.json', 'composer.json',
    'requirements.txt', 'Pipfile', 'Pipfile.lock',
    # Git files
    '.gitignore', '.gitattributes',
}

def extract_repo_name(repo_url):
    """Extract repository name from GitHub URL."""
    try:
        # Handle both HTTPS and SSH URLs
        if repo_url.endswith('.git'):
            repo_url = repo_url[:-4]
        return repo_url.split('/')[-2:]
    except Exception as e:
        raise GitHubRepoContentExtractionError(f"Invalid GitHub repository URL: {repo_url}")

def clone_repository(repo_url):
    """Clone a GitHub repository to a temporary directory."""
    try:
        logger.info(f"Cloning repository {repo_url}")
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Clone the repository
        repo = Repo.clone_from(repo_url, temp_dir)
        
        logger.info(f"Cloned repository {repo_url}")
        return temp_dir, repo
    except Exception as e:
        # Check if the error message indicates repository not found
        if "repository" in str(e).lower() and "not found" in str(e).lower():
            # Extract repo URL from error message using regex
            import re
            match = re.search(r"repository '([^']+)' not found", str(e))
            if match:
                repo_url = match.group(1)
                logger.error(f"Repository not found: {repo_url}")
                raise GithubInvalidRepoError(f"No repository exists at this URL.")
        logger.error(f"Error cloning repository {repo_url}: {str(e)}")
        raise GitHubRepoContentExtractionError(f"Failed to clone repository: {str(e)}")

def get_file_content(file_path):
    """Read and return the content of a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Skip binary files
        return None
    except Exception as e:
        logger.warning(f"Error reading file {file_path}: {str(e)}")
        return None
    
def read_repository(repo_path):
    """Get the directory structure and file contents of the repository."""
    structure = []
    logger.info(f"Reading repository {repo_path}")
    
    for root, dirs, files in os.walk(repo_path):
        # Skip .git directory
        if '.git' in dirs:
            dirs.remove('.git')
        
        # Skip common build directories and cache
        dirs[:] = [d for d in dirs if d not in [
            '.git', 'node_modules', '__pycache__', 'build', 'dist',
            'venv', 'env', '.venv', '.env',  # Python virtual environments
            'target', 'out',  # Java/Maven/Gradle build directories
            'bin', 'obj',  # .NET build directories
            'vendor',  # PHP/Go dependencies
            'coverage', '.coverage',  # Test coverage reports
            '.idea', '.vscode',  # IDE directories
            'tmp', 'temp',  # Temporary directories
            '.next', '.nuxt',  # Next.js/Nuxt.js build directories
            'logs', 'log'  # Log directories
        ]]
        
        # Add files at current level
        for file in sorted(files):
            # Skip non-code files and common file types that aren't code
            
            if file.lower().endswith(tuple(non_code_extensions)):
                continue
                
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, repo_path)
            
            # Skip files larger than 10MB
            if os.path.getsize(file_path) > 1024 * 1024 * 10:
                continue
            
            content = get_file_content(file_path)
            structure.append({
                'path': relative_path,
                'content': content,
                'size': os.path.getsize(file_path)
            })

    logger.info(f"Repository structure and contents read")
    return structure

def save_repository(data_source, structure):
    """Save the read repository structure and contents to the database."""
    from core.models import GithubFile
    bulk_save = []

    if settings.ENV != 'selfhosted':
        if len(structure) > settings.DATA_SOURCES_GITHUB_FILE_COUNT_LIMIT_PER_REPO_HARD_LIMIT:
            raise GithubRepoFileCountLimitError(f"The codebase exceeds the maximum file limit of {settings.DATA_SOURCES_GITHUB_FILE_COUNT_LIMIT_PER_REPO_HARD_LIMIT} files supported")

        # Calculate total size of all files
        total_size = sum(file['size'] for file in structure)
        
        # Check if total size exceeds limit (e.g. 100MB)
        if total_size > settings.DATA_SOURCES_GITHUB_REPO_SIZE_LIMIT_MB * 1024 * 1024:
            raise GithubRepoSizeLimitError(f"The codebase exceeds the maximum size limit of {settings.DATA_SOURCES_GITHUB_REPO_SIZE_LIMIT_MB} MB supported")

    for file in structure:
        bulk_save.append(GithubFile(
            data_source=data_source,
            path=file['path'],
            content=file['content'],
            size=file['size']
        ))

        if len(bulk_save) >= 100:
            try:
                GithubFile.objects.bulk_create(bulk_save)
            except Exception as e:
                for file in bulk_save:
                    try:
                        file.save()
                    except Exception as e:
                        logger.error(f"Error saving GitHub file {file.path}: {e}")
            bulk_save = []

    if bulk_save:
        try:
            GithubFile.objects.bulk_create(bulk_save)
        except Exception as e:
            for file in bulk_save:
                try:
                    file.save()
                except Exception as e:
                    logger.error(f"Error saving GitHub file {file.path}: {e}")


def process_github_repository(data_source):
    """Main function to process a GitHub repository."""
    try:
        repo_url = data_source.url
        # Clone the repository
        temp_dir, repo = clone_repository(repo_url)
        
        # Check default branch name
        default_branch = repo.active_branch.name
        logger.info(f"Default branch name: {default_branch}")
        
        # Get repository structure and contents
        structure = read_repository(temp_dir)

        save_repository(data_source, structure)
        
        # Clean up temporary directory
        repo.close()
        os.system(f"rm -rf {temp_dir}")
        
        return default_branch 
    except GithubInvalidRepoError as e:
        raise e
    except GithubRepoSizeLimitError as e:
        raise e
    except GithubRepoFileCountLimitError as e:
        raise e
    except Exception as e:
        raise GitHubRepoContentExtractionError(f"Error processing GitHub repository: {str(e)}")