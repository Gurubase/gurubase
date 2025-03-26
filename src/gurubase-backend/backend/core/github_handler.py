import os
import tempfile
import logging
from git import Repo
from pathlib import Path
from django.conf import settings
from core.utils import get_default_settings
from core.exceptions import GitHubRepoContentExtractionError, GithubInvalidRepoError, GithubRepoSizeLimitError, GithubRepoFileCountLimitError

logger = logging.getLogger(__name__)

code_file_extensions = {
    # General purpose languages
    '.py', '.pyi', '.pyx',  # Python
    '.js', '.jsx', '.mjs',  # JavaScript
    '.ts', '.tsx',          # TypeScript
    '.rb', '.rake', '.erb', # Ruby
    '.php',                 # PHP
    '.java',                # Java
    '.scala',               # Scala
    '.kt', '.kts',          # Kotlin
    '.go', '.mod',          # Go
    '.rs',                  # Rust
    '.cpp', '.cc', '.cxx',  # C++
    '.hpp', '.hh', '.hxx',  
    '.c', '.h',            # C
    '.cs',                  # C#
    '.fs', '.fsx',         # F#
    '.swift',              # Swift
    '.m', '.mm',           # Objective-C
    
    # Web technologies
    '.html', '.htm',       # HTML
    '.css', '.scss', '.sass', '.less',  # Stylesheets
    '.vue', '.svelte',     # Web frameworks
    
    # Shell and scripting
    '.sh', '.bash', '.zsh',  # Shell scripts
    '.ps1', '.psm1', '.psd1',  # PowerShell
    '.pl', '.pm',          # Perl
    '.lua',                # Lua
    
    # Functional languages
    '.hs', '.lhs',         # Haskell
    '.ex', '.exs',         # Elixir
    '.erl', '.hrl',        # Erlang
    '.clj', '.cljs',       # Clojure
    
    # Other languages
    '.r', '.R',            # R
    '.dart',               # Dart
    '.groovy',             # Groovy
    '.ml', '.mli',         # OCaml
    '.sol',                # Solidity
    '.cob', '.cbl',        # COBOL
    '.proto',              # Protocol Buffers
}

package_manifest_files = {
    # Python
    'requirements.txt',
    'setup.py',
    'pyproject.toml',
    'Pipfile',
    'poetry.toml',
    
    # JavaScript/TypeScript
    'package.json',
    'bower.json',
    
    # Ruby
    'Gemfile',
    
    # Java/Kotlin
    'pom.xml',
    'build.gradle',
    'build.gradle.kts',
    
    # Go
    'go.mod',
    
    # Rust
    'Cargo.toml',
    
    # PHP
    'composer.json',
    
    # .NET/C#
    '*.csproj',
    '*.fsproj',
    'packages.config',
    
    # Swift
    'Package.swift',
    
    # Scala
    'build.sbt',
    
    # Haskell
    'package.yaml',
    'cabal.project',
    
    # Elixir
    'mix.exs',
    
    # R
    'DESCRIPTION',
    
    # Perl
    'cpanfile',
    'Makefile.PL',
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
        elif 'No such device or address' in str(e):
            raise GithubInvalidRepoError(f"No repository exists at this URL.")
        logger.error(f"Error cloning repository {repo_url}: {str(e)}", exc_info=True)
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

    default_settings = get_default_settings()

    package_manifest_files = set(default_settings.package_manifest_files) # Turn into set to optimize existence check
    code_file_extensions = set(default_settings.code_file_extensions) # Turn into set to optimize existence check

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
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, repo_path)
            
            # Process only if it's a code file or package manifest
            _, ext = os.path.splitext(file.lower())
            if ext in code_file_extensions or file in package_manifest_files:
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

def save_repository(data_source, structure, default_branch):
    """Save the read repository structure and contents to the database."""
    from core.models import GithubFile
    bulk_save = []

    if settings.ENV != 'selfhosted':
        if len(structure) > data_source.guru_type.github_file_count_limit_per_repo_soft:
            raise GithubRepoFileCountLimitError(f"The codebase ({len(structure)}) exceeds the maximum file limit of {data_source.guru_type.github_file_count_limit_per_repo_soft} files supported")

        # Calculate total size of all files
        total_size = sum(file['size'] for file in structure)
        
        # Check if total size exceeds limit
        if total_size > data_source.guru_type.github_repo_size_limit_mb * 1024 * 1024:
            raise GithubRepoSizeLimitError(f"The codebase exceeds the maximum size limit of {data_source.guru_type.github_repo_size_limit_mb} MB supported")

    for file in structure:
        bulk_save.append(GithubFile(
            data_source=data_source,
            path=file['path'],
            content=file['content'],
            size=file['size'],
            link=f'{data_source.url}/tree/{default_branch}/{file["path"]}'
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

        save_repository(data_source, structure, default_branch)
        
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