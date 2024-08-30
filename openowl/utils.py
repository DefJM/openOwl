import re

from openowl.logger_config import setup_logger

logger = setup_logger(__name__)


def extract_github_library_name(repo_url):
    """
    Extracts the library name from a GitHub repository URL.

    Args:
    repo_url (str): The GitHub repository URL.

    Returns:
    str: The extracted library name, or None if the URL is not valid.
    """
    pattern = r"https?://github\.com/[\w-]+/([\w-]+)"
    match = re.search(pattern, repo_url)
    if match:
        library_name = match.group(1)
        logger.info(f"Successfully extracted library name: {library_name}")
        return library_name
    else:
        logger.warning(f"Failed to extract library name from URL: {repo_url}")
        return None


def is_github_repo(url):
    """
    Checks if the given URL is a valid GitHub repository link.

    Args:
    url (str): The URL to check.

    Returns:
    bool: True if it's a valid GitHub repo URL, False otherwise.
    """
    pattern = r"^https?://github\.com/[\w-]+/[\w-]+/?$"
    is_valid = bool(re.match(pattern, url))
    return is_valid
