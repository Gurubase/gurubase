# Create zendesk tickets and articles
import os
import django
import random
import string
import sys
from datetime import datetime, timedelta

import requests

# Set up Django environment
sys.path.append('/workspaces/gurubase/src/gurubase-backend/backend')
sys.path.append('/workspace/backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from core.models import Integration, GuruType
from core.requester import ZendeskRequester

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
    ticket_statuses = ['new', 'open', 'pending', 'solved']

    # print("Creating tickets...")
    # for i in range(100):
    #     try:
    #         # Create ticket with random subject and priority
    #         subject = f"{random.choice(ticket_subjects)} #{i+1}"
    #         description = f"""
    #         Issue Description:
    #         {generate_random_text()}
            
    #         Steps to Reproduce:
    #         1. {generate_random_text(50)}
    #         2. {generate_random_text(50)}
    #         3. {generate_random_text(50)}
            
    #         Expected Behavior:
    #         {generate_random_text()}
            
    #         Actual Behavior:
    #         {generate_random_text()}
    #         """
            
    #         # Create ticket using Zendesk API
    #         ticket_data = {
    #             'ticket': {
    #                 'subject': subject,
    #                 'comment': {
    #                     'body': description
    #                 },
    #                 'priority': random.choice(ticket_priorities),
    #                 'status': random.choice(ticket_statuses)
    #             }
    #         }
            
    #         # Add ticket using requests since ZendeskRequester doesn't have create method
    #         import requests
    #         response = requests.post(
    #             f"https://{integration.zendesk_domain}/api/v2/tickets.json",
    #             json=ticket_data,
    #             auth=(f"{integration.zendesk_user_email}/token", integration.zendesk_api_token)
    #         )
    #         response.raise_for_status()
            
    #         # Add 3 comments to the ticket
    #         ticket_id = response.json()['ticket']['id']
    #         for j in range(3):
    #             comment_data = {
    #                 'ticket': {
    #                     'comment': {
    #                         'body': f"Comment {j+1} on ticket {subject}\n\n{generate_random_text(200)}",
    #                         'public': True
    #                     }
    #                 }
    #             }
                
    #             requests.put(
    #                 f"https://{integration.zendesk_domain}/api/v2/tickets/{ticket_id}.json",
    #                 json=comment_data,
    #                 auth=(f"{integration.zendesk_user_email}/token", integration.zendesk_api_token)
    #             )
            
    #         print(f"Created ticket {i+1}/100: {subject}")
            
    #     except Exception as e:
    #         print(f"Error creating ticket {i+1}: {str(e)}")
    #         continue

    # Create 50 help center articles
    article_categories = [
        "Getting Started",
        "User Guide",
        "API Documentation",
        "Troubleshooting",
        "Best Practices"
    ]

    print("\nCreating help center section...")
    try:
        # First create a section
        section_data = {
            'section': {
                'name': 'General Documentation',
                'locale': 'en-us'
            }
        }
        
        response = requests.get(
            f"https://{integration.zendesk_domain}/api/v2/help_center/en-us/sections.json",
            auth=(f"{integration.zendesk_user_email}/token", integration.zendesk_api_token)
        )
        response.raise_for_status()
        section_id = response.json()['sections'][0]['id']
        print(f"Created section with ID: {section_id}")
    except Exception as e:
        print(f"Error creating section: {str(e)}")
        return

    print("\nCreating help center articles...")
    for i in range(50):
        try:
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
                    'section_id': 78910,  # Replace with your actual section ID
                    'label_names': ['documentation', 'guide'],
                    'comments_disabled': False
                }
            }
            
            # Add article using requests with proper headers
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"https://{integration.zendesk_domain}/api/v2/help_center/articles.json",
                json=article_data,
                headers=headers,
                auth=(f"{integration.zendesk_user_email}/token", integration.zendesk_api_token)
            )
            response.raise_for_status()
            
            # Add 2 comments to the article
            article_id = response.json()['article']['id']
            for j in range(2):
                comment_data = {
                    'comment': {
                        'body': f"Comment {j+1} on article {title}\n\n{generate_random_text(100)}",
                        'public': True
                    }
                }
                
                requests.post(
                    f"https://{integration.zendesk_domain}/api/v2/help_center/articles/{article_id}/comments.json",
                    json=comment_data,
                    headers=headers,
                    auth=(f"{integration.zendesk_user_email}/token", integration.zendesk_api_token)
                )
            
            print(f"Created article {i+1}/50: {title}")
            
        except Exception as e:
            print(f"Error creating article {i+1}: {str(e)}")
            continue

if __name__ == '__main__':
    create_zendesk_content()
    create_zendesk_content()