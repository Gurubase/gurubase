import os
import sys
import django


sys.path.append('/workspaces/gurubase-backend/backend')
sys.path.append('/workspace/backend')
sys.path.append('/workspaces/gurubase/src/gurubase-backend/backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

django.setup()
from core.utils import get_default_settings
from core.models import Settings
from django.conf import settings as django_settings

pricings = {
    'gpt-4o-2024-08-06': {
        'prompt': 2.5 / 1_000_000,
        'cached_prompt': 1.25 / 1_000_000,
        'completion': 10 / 1_000_000
    },
    'gpt-4o-mini-2024-07-18': {
        'prompt': 0.15 / 1_000_000,
        'cached_prompt': 0.075 / 1_000_000,
        'completion': 0.6 / 1_000_000
    },
    'gemini-1.5-flash': {
        'prompt': 0.075 / 1_000_000,
        'completion': 0.3 / 1_000_000
    },
    'gemini-1.5-flash-002': {
        'prompt': 0.075 / 1_000_000,
        'completion': 0.3 / 1_000_000
    }
}

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

    # XML and related formats
    '.xml', '.xsd', '.xslt', '.xsl', '.rss', '.atom', '.svg', '.pom', '.config', '.resx', '.nuspec',
    
    # Markdown and documentation
    '.md', '.mdx', '.markdown', '.rst', '.adoc', '.asciidoc', '.txt', '.text',
    
    # JSON and related formats
    '.json', '.json5', '.jsonc', '.jsonl', '.jsonnet', '.hjson', '.yaml', '.yml', '.yaml-tmlanguage',
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

embedding_model_configs = {
    'IN_HOUSE': {
        'collection_name': 'github_repo_code',  # Default in cloud
        'dimension': 1024
    },
    'GEMINI_EMBEDDING_001': {
        'collection_name': 'github_repo_code_gemini_embedding_001',
        'dimension': 768
    },
    'GEMINI_TEXT_EMBEDDING_004': {
        'collection_name': 'github_repo_code_gemini_text_embedding_004',
        'dimension': 768
    },
    'OPENAI_TEXT_EMBEDDING_3_SMALL': {
        'collection_name': 'github_repo_code' if getattr(django_settings, 'ENV', '') == 'selfhosted' else 'github_repo_code_openai_text_embedding_3_small',  # Default in selfhosted
        'dimension': 1536
    },
    'OPENAI_TEXT_EMBEDDING_3_LARGE': {
        'collection_name': 'github_repo_code_openai_text_embedding_3_large',
        'dimension': 3072
    },
    'OPENAI_TEXT_EMBEDDING_ADA_002': {
        'collection_name': 'github_repo_code_openai_ada_002',
        'dimension': 1536
    }
}

default_settings = get_default_settings()

Settings.objects.update_or_create(
    id=default_settings.id,
    defaults={
        'pricings': pricings,
        'embedding_model_configs': embedding_model_configs,
        'code_file_extensions': list(code_file_extensions),
        'package_manifest_files': list(package_manifest_files),
        'trust_score_threshold': 0.5
    }
)
