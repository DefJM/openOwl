import re
from packaging import version
from urllib.parse import urlparse
from openowl.logger_config import setup_logger
from openowl.depsdev_utils import get_default_version
from openowl.clients import DepsDevClient

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


def sort_version_list(version_list):
    def clean_version(v):
        # Handle common non-standard version formats
        v = v.replace("-py", "+py")  # Convert -py2.7 to +py2.7 (valid local version)
        v = v.replace("-", ".")  # Replace other hyphens with dots
        return v

    # Convert to Version objects for proper comparison
    version_objects = []
    for v in version_list:
        try:
            version_objects.append(version.parse(clean_version(v)))
        except version.InvalidVersion as e:
            print(f"Warning: Could not parse version '{v}': {e}")
            # Add as string to preserve the version in the list
            version_objects.append(v)

    # Sort version objects (valid versions will be sorted properly)
    def sort_key(v):
        if isinstance(v, str):
            return (0, v)  # Invalid versions go to the end
        return (1, v)  # Valid versions sort normally

    sorted_versions = sorted(version_objects, key=sort_key, reverse=True)

    # Convert back to strings
    return [str(v) for v in sorted_versions]


def extract_github_info(github_url):
    """Extract owner and repo name from GitHub URL.

    Args:
        github_url (str): GitHub repository URL - can include additional paths
            like branches, folders, etc.

    Returns:
        tuple: (owner, repo_name)

    Raises:
        ValueError: If URL is not a valid GitHub repository URL
    """
    try:
        parsed = urlparse(github_url)
        if parsed.netloc not in ["github.com", "www.github.com"]:
            raise ValueError("Not a GitHub URL")

        # Remove trailing slashes and split path
        path_parts = parsed.path.strip("/").split("/")

        if len(path_parts) < 2:
            raise ValueError("URL does not contain owner/repo format")

        # Always take the first two parts after github.com
        # This handles cases like:
        # /owner/repo
        # /owner/repo/tree/main/docs
        # /owner/repo/blob/master/README.md
        # etc.
        return path_parts[0], path_parts[1]

    except Exception as e:
        raise ValueError(f"Invalid GitHub URL: {str(e)}")


def extract_package_info(package_manager, github_url, package_version=None):
    # extract package info from github url
    package_owner, package_name = extract_github_info(github_url)

    # if no version is provided, get latest version
    if package_version is None:
        depsdev_client = DepsDevClient()
        package_version = get_default_version(depsdev_client, package_manager, package_name)
        logger.info(f"No version provided, took the latest version: {package_version}")

    dependency = {
        "github_url": github_url,
        "package_manager": package_manager,
        "owner": package_owner,
        "name": package_name,
        "version": package_version,
    }
    return dependency