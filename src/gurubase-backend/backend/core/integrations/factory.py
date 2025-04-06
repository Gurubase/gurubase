from core.integrations.discord_strategy import DiscordStrategy
from core.integrations.github_strategy import GitHubStrategy
from core.integrations.slack_strategy import SlackStrategy
from core.integrations.strategy import IntegrationStrategy
from core.models import Integration


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
        else:
            raise ValueError(f'Invalid integration type: {integration_type}')

