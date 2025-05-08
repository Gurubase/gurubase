from integrations.bots.discord.discord_strategy import DiscordStrategy
from integrations.bots.slack.slack_strategy import SlackStrategy
from integrations.bots.github.github_strategy import GitHubStrategy
from integrations.ingestion.jira.jira_strategy import JiraStrategy
from integrations.ingestion.zendesk.zendesk_strategy import ZendeskStrategy
from integrations.ingestion.confluence.confluence_strategy import ConfluenceStrategy
from integrations.strategy import IntegrationStrategy
from integrations.models import Integration


class IntegrationFactory:
    @staticmethod
    def get_strategy(integration_type: str, integration: 'Integration' = None) -> IntegrationStrategy:
        integration_type = integration_type.upper()
        if integration_type == 'DISCORD':
            return DiscordStrategy(integration)
        elif integration_type == 'SLACK':
            return SlackStrategy(integration)
        elif integration_type == 'GITHUB':
            return GitHubStrategy(integration)
        elif integration_type == 'JIRA':
            return JiraStrategy(integration)
        elif integration_type == 'ZENDESK':
            return ZendeskStrategy(integration)
        elif integration_type == 'CONFLUENCE':
            return ConfluenceStrategy(integration)
        else:
            raise ValueError(f'Invalid integration type: {integration_type}')

