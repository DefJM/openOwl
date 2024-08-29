import re
from pprint import pprint

import pandas as pd

from openowl.deps_local import check_files, clean_dependencies, parse_pyproject_toml
from openowl.depsdev_client import DepsDevClient
from openowl.depsdev_utils import (
    get_default_version,
    get_dependencies,
    get_packages,
    get_version,
)
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


def scan_local(local_root_dir=None):
    if check_files(local_root_dir)["pyproject.toml"] == True:
        dependencies = parse_pyproject_toml()
    pprint(dependencies)
    # only take main dependencies, leave out dev-dependencies
    dependencies = dependencies["dependencies"]
    dependencies = clean_dependencies(dependencies)
    return dependencies


def get_deps_table(deps_json):
    df = pd.DataFrame([dep["versionKey"] for dep in deps_json["nodes"]])
    df["relation"] = pd.DataFrame([dep["relation"] for dep in deps_json["nodes"]])
    return df


def scan_from_url(repo_url=None, package_version=None):
    if is_github_repo(repo_url):
        logger.info(f"URL is a valid GitHub repo: {repo_url}")
        package_name = extract_github_library_name(repo_url)
    else:
        logger.warning(f"URL is not a valid GitHub repo: {repo_url}")
    system_name = "pypi"
    depsdev_client = DepsDevClient()
    if package_version is None:
        package_data = get_packages(depsdev_client, system_name, package_name)
        default_version = get_default_version(package_data)
        package_version_data = get_version(
            depsdev_client, system_name, package_name, default_version
        )
        package_dependencies = get_dependencies(
            depsdev_client, system_name, package_name, default_version
        )
        df = get_deps_table(package_dependencies.json())
        return df


if __name__ == "__main__":
    repo_url = "https://github.com/pandas-dev/pandas"
    df = scan_from_url(repo_url)
    print(
        """
############## Dependencies ################
          
        """
    )
    print(df[1:])
