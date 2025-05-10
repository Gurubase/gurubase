# Create zendesk tickets and articles
import os
import django
import random
import string
import sys
import time
from datetime import datetime, timedelta

import requests

# Set up Django environment
sys.path.append('/workspaces/gurubase/src/gurubase-backend/backend')
sys.path.append('/workspace/backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from integrations.models import Integration
from core.models import GuruType
from core.requester import ZendeskRequester

# Throttling settings
TICKET_THROTTLE_SECONDS = 1  # 1 second between ticket requests
ARTICLE_THROTTLE_SECONDS = 2  # 2 seconds between article requests

def generate_random_text(length=1000):
    """Generate random text for content"""
    words = ['lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 'adipiscing', 'elit']
    return ' '.join(random.choices(words, k=length))

def create_zendesk_content():
    # Get the Zendesk integration
    integration = Integration.objects.get(
        type=Integration.Type.ZENDESK,
        guru_type=GuruType.objects.get(slug='gurubase')
    )

    # Initialize Zendesk requester
    zendesk = ZendeskRequester(integration)

    # Create 100 tickets
    ticket_subjects = [
        "Bug Report: Application Crash",
        "Feature Request: New Dashboard",
        "Support: Login Issues",
        "Question: API Documentation",
        "Feedback: User Interface",
        "Issue: Performance Problems",
        "Request: Account Access",
        "Problem: Data Synchronization",
        "Inquiry: Pricing Plans",
        "Report: Security Concern"
    ]

    ticket_priorities = ['urgent', 'high', 'normal', 'low']

    print("Creating tickets...")
    for i in range(200):
        try:
            # Create ticket with random subject and priority
            subject = f"{random.choice(ticket_subjects)} #{i+1}"
            description = f"""
            Issue Description:
            {generate_random_text(5)}
            """
            
            # Create ticket using Zendesk API
            ticket_data = {
                'ticket': {
                    'subject': subject,
                    'comment': {
                        'body': description
                    },
                    'priority': random.choice(ticket_priorities),
                    'status': 'solved'
                }
            }
            
            # Add ticket using requests since ZendeskRequester doesn't have create method
            response = requests.post(
                f"https://{integration.zendesk_domain}/api/v2/tickets.json",
                json=ticket_data,
                auth=(f"{integration.zendesk_user_email}/token", integration.zendesk_api_token)
            )
            response.raise_for_status()
            
            # # Add 3 comments to the ticket
            # ticket_id = response.json()['ticket']['id']
            # for j in range(3):
            #     comment_data = {
            #         'ticket': {
            #             'comment': {
            #                 'body': f"Comment {j+1} on ticket {subject}\n\n{generate_random_text(200)}",
            #                 'public': True
            #             }
            #         }
            #     }
                
            #     requests.put(
            #         f"https://{integration.zendesk_domain}/api/v2/tickets/{ticket_id}.json",
            #         json=comment_data,
            #         auth=(f"{integration.zendesk_user_email}/token", integration.zendesk_api_token)
            #     )
            #     time.sleep(TICKET_THROTTLE_SECONDS)  # Throttle comment creation
            
            print(f"Created ticket {i+1}/100: {subject}")
            time.sleep(TICKET_THROTTLE_SECONDS)  # Throttle ticket creation
            
        except Exception as e:
            print(f"Error creating ticket {i+1}: {str(e)}")
            continue

    # Create 50 help center articles
    article_categories = [
        "Getting Started",
        "User Guide",
        "API Documentation",
        "Troubleshooting",
        "Best Practices"
    ]

    print("\nFetching available sections...")
    try:
        # Get available sections
        response = requests.get(
            f"https://{integration.zendesk_domain}/api/v2/help_center/sections.json",
            auth=(f"{integration.zendesk_user_email}/token", integration.zendesk_api_token)
        )
        response.raise_for_status()
        sections = response.json()['sections']
        if not sections:
            print("No sections found!")
            return
            
        print(f"Found {len(sections)} sections")
    except Exception as e:
        print(f"Error fetching sections: {str(e)}. It may be the case that you have not initiated articles yet. Please check https://<domain>.zendesk.com/knowledge/lists")
        return

    print("\nCreating help center articles...")
    for i in range(200):
        try:
            # Select a random section
            section = random.choice(sections)
            section_id = section['id']
            
            # Create article with random category
            title = f"Article {i+1}: {random.choice(article_categories)} Guide"
            body = f"""
            <h1>{title}</h1>
            
            <h2>Overview</h2>
            <p>{generate_random_text(5)}</p>
            """
            
            # Create article using Zendesk API
            article_data = {
                'article': {
                    'title': title,
                    'body': body,
                    'locale': 'en-us',
                    'user_segment_id': None,
                    'permission_group_id': 27246575367197 # Get this from the curl:
                    # curl https://<domain>.zendesk.com/api/v2/guide/permission_groups.json \
                    # -u <email>/token:<api_token>
                }
            }
            
            # Add article using requests with proper headers
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"https://{integration.zendesk_domain}/api/v2/help_center/sections/{section_id}/articles.json",
                json=article_data,
                headers=headers,
                auth=(f"{integration.zendesk_user_email}/token", integration.zendesk_api_token)
            )
            response.raise_for_status()
            
            # # Add 2 comments to the article
            # article_id = response.json()['article']['id']
            # for j in range(2):
            #     comment_data = {
            #         'comment': {
            #             'body': f"Comment {j+1} on article {title}\n\n{generate_random_text(100)}",
            #             'public': True
            #         }
            #     }
                
            #     requests.post(
            #         f"https://{integration.zendesk_domain}/api/v2/help_center/articles/{article_id}/comments.json",
            #         json=comment_data,
            #         headers=headers,
            #         auth=(f"{integration.zendesk_user_email}/token", integration.zendesk_api_token)
            #     )
            #     time.sleep(ARTICLE_THROTTLE_SECONDS)  # Throttle comment creation
            
            print(f"Created article {i+1}/50: {title} in section {section['name']}")
            time.sleep(ARTICLE_THROTTLE_SECONDS)  # Throttle article creation
            
        except Exception as e:
            print(f"Error creating article {i+1}: {str(e)}")
            continue

if __name__ == '__main__':
    create_zendesk_content()