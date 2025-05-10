import re


class NotEnoughData(Exception):
    pass

class NotRelated(Exception):
    pass

class IntegrationError(Exception):
    pass

def strip_first_header(content: str) -> str:
    """Remove the first header (starting with # and ending with newline) from content."""
    if content.startswith('#'):
        # Find the first newline
        newline_index = content.find('\n')
        if newline_index != -1:
            # Return content after the newline
            return content[newline_index + 1:].lstrip()
    return content

def get_trust_score_emoji(trust_score: int) -> str:
    if trust_score >= 80:
        return "🟢"
    elif trust_score >= 60:
        return "🟡"
    elif trust_score >= 40:
        return "🟡"
    elif trust_score >= 20:
        return "🟠"
    else:
        return "🔴"

def cleanup_title(title: str) -> str:
    """Clean up the title of a repository"""
    clean_title = re.sub(r'\s*:[a-zA-Z0-9_+-]+:\s*', ' ', title)
    clean_title = re.sub(
        r'\s*(?:[\u2600-\u26FF\u2700-\u27BF\U0001F300-\U0001F9FF\U0001FA70-\U0001FAFF]'
        r'[\uFE00-\uFE0F\U0001F3FB-\U0001F3FF]?\s*)+',
        ' ',
        clean_title
    ).strip()

    clean_title = ' '.join(clean_title.split())
    clean_title = clean_title.replace('_', '-')

    return clean_title