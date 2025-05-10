# Create confluence spaces and pages
import os
import django
import random
import string
from datetime import datetime
import sys
import time  # Add time module for throttling
# Set up Django environment
sys.path.append('/workspaces/gurubase/src/gurubase-backend/backend')
sys.path.append('/workspaces/gurubase-backend/backend')
sys.path.append('/workspace/backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import GuruType
from integrations.models import Integration
from core.requester import ConfluenceRequester
from django.contrib.auth import get_user_model

User = get_user_model()

def generate_random_text(length=1000):
    """Generate random text for page content"""
    words = ['lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 'adipiscing', 'elit']
    return ' '.join(random.choices(words, k=length))

def create_confluence_spaces_and_pages():
    # Get or create a Confluence integration
    integration = Integration.objects.get(
        type=Integration.Type.CONFLUENCE,
        guru_type=GuruType.objects.get(slug='gurubase')
    )

    # Initialize Confluence requester
    confluence = ConfluenceRequester(integration)

    # Create 5 spaces
    space_names = [
        'Engineering Documentation',
        'Product Requirements',
        'Design Guidelines',
        'Development Standards',
        'Project Management'
    ]

    for space_name in space_names:
        try:
            # Generate space key
            space_key = ''.join(random.choices(string.ascii_uppercase, k=3))
            
            # Check if space exists
            try:
                existing_space = confluence.confluence.get_space(space_key)
                print(f"Space {space_name} ({space_key}) already exists, skipping creation")
                space = existing_space
            except Exception:
                # Space doesn't exist, create it
                space = confluence.confluence.create_space(
                    space_key=space_key,
                    space_name=space_name,
                )
                print(f"Created space: {space_name} ({space_key})")

            # Create 500 pages in each space
            for i in range(300):
                page_title = f"Page {i+1} - {space_name}"
                page_content = f"""
                # {page_title}
                
                Created on: {datetime.now().isoformat()}
                
                {generate_random_text()}
                """
                
                # Create page
                page = confluence.confluence.create_page(
                    space=space_key,
                    title=page_title,
                    body=page_content,
                    type='page'
                )
                
                # Add throttling between page creation and comments
                time.sleep(1)  # Wait 1 second between page creation and comments
                
                # Add some comments to the page
                for j in range(3):  # Add 3 comments per page
                    comment_content = f"Comment {j+1} on {page_title}\n\n{generate_random_text(100)}"
                    confluence.confluence.add_comment(
                        page_id=page['id'],
                        text=comment_content
                    )
                    time.sleep(0.5)  # Wait 0.5 seconds between comment additions
                
                print(f"Created page {i+1}/500 in space {space_name}")
                time.sleep(2)  # Wait 2 seconds between page creations
                
        except Exception as e:
            print(f"Error creating space {space_name}: {str(e)}")
            continue

if __name__ == '__main__':
    create_confluence_spaces_and_pages()