# Create jira issues in Done status

import os
import sys
import time
import django

# Set up Django environment
sys.path.append('/workspaces/gurubase/src/gurubase-backend/backend')
sys.path.append('/workspace/backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from core.models import Integration, GuruType
from core.requester import JiraRequester

def throttle_request(func):
    """Decorator to throttle API requests"""
    last_request_time = 0
    min_interval = 1.0  # Minimum seconds between requests
    
    def wrapper(*args, **kwargs):
        nonlocal last_request_time
        current_time = time.time()
        time_since_last = current_time - last_request_time
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            time.sleep(sleep_time)
        
        result = func(*args, **kwargs)
        last_request_time = time.time()
        return result
    
    return wrapper

class ThrottledJiraRequester(JiraRequester):
    """Extended JiraRequester with throttling"""
    
    @throttle_request
    def create_issue(self, project_key, summary, description, issue_type="Task", priority="Medium"):
        """Create a Jira issue with throttling"""
        fields = {
            'project': {'key': project_key},
            'summary': summary,
            'description': description,
            'issuetype': {'name': issue_type},
        }
        
        return self.jira.create_issue(fields=fields)
    
    @throttle_request
    def add_comment(self, issue_key, comment):
        """Add a comment to a Jira issue with throttling"""
        return self.jira.issue_add_comment(issue_key, comment)

    @throttle_request
    def transitions(self, issue_key):
        """Get available transitions for an issue"""
        return self.jira.get_issue_transitions(issue_key)


def create_jira_content():
    # Get the Jira integration
    integration = Integration.objects.get(
        type=Integration.Type.JIRA,
        guru_type=GuruType.objects.get(slug='gurubase')
    )

    # Initialize Jira requester
    jira = ThrottledJiraRequester(integration)

    # Get available projects
    try:
        projects = jira.jira.projects()
        if not projects:
            print("No projects found in Jira. Please create at least one project first.")
            return
        
        project_keys = [project['key'] for project in projects]
        print(f"Found projects: {', '.join(project_keys)}")
    except Exception as e:
        print(f"Error fetching projects: {e}")
        return

    # Create 100 issues
    print("Creating Jira issues...")
    for i in range(500):
        try:
            # Create issue
            issue = jira.create_issue(
                project_key=project_keys[0],  # Use first project
                summary=f"Test Issue {i+1}",
                description="Test description",
                issue_type="Task"
            )
            
            # Transition to Done
            transitions = jira.transitions(issue['key'])
            for transition in transitions:
                if transition['to'].lower() == 'done':
                    jira.jira.issue_transition(issue['key'], 'done')
                    break
            
            print(f"Created issue {i+1}/100: {issue['key']}")
            
        except Exception as e:
            print(f"Error creating issue {i+1}: {e}")
            continue

if __name__ == '__main__':
    create_jira_content()