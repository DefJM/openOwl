from typing import Optional
from urllib.parse import quote

import pandas as pd
import requests

from openowl.logger_config import setup_logger

logger = setup_logger(__name__)


def get_packages(client, system_name, package_name):
    return client.get(f"/v3/systems/{system_name}/packages/{package_name}")


def get_default_version(raw_response):
    """parse default version from `get_packages` deps.dev api response"""
    try:
        default_version = next(
            version["versionKey"]["version"]
            for version in raw_response.json()["versions"]
            if version["isDefault"]
        )
        logger.info(f"The default version is: {default_version}")
    except StopIteration:
        logger.warning("No default version found.")
    return default_version


def get_package_version_list(raw_response):
    """get all versions of a package"""
    return [
        version["versionKey"]["version"] for version in raw_response.json()["versions"]
    ]


def get_dependencies(client, version_key_system, version_key_name, version_key_version):
    url = f"/v3/systems/{version_key_system}/packages/{version_key_name}/versions/{version_key_version}:dependencies"
    return client.get(url)


def get_version(client, version_key_system, version_key_name, version_key_version):
    url = f"/v3/systems/{version_key_system}/packages/{version_key_name}/versions/{version_key_version}"
    return client.get(url)


def get_advisory(client, advisory_key_id):
    url = f"/v3/advisories/{advisory_key_id}"
    return client.get(url)


def url_encode(string):
    return quote(string, safe="")


def get_deps_table(deps_dict):
    df = pd.DataFrame([dep["versionKey"] for dep in deps_dict["nodes"]])
    df["relation"] = pd.DataFrame([dep["relation"] for dep in deps_dict["nodes"]])
    df = df.sort_values(by="relation")
    return df


def get_deps_stats(package_dependencies):
    df_deps = get_deps_table(package_dependencies)
    num_deps_total = len(df_deps.loc[df_deps["relation"].isin(["DIRECT", "INDIRECT"])])
    num_deps_direct = len(df_deps.loc[df_deps["relation"] == "DIRECT"])
    num_deps_indirect = len(df_deps.loc[df_deps["relation"] == "INDIRECT"])
    return num_deps_total, num_deps_direct, num_deps_indirect


def extract_package_url(deps_dict):
    """
    Extract GitHub repository URL from package metadata.
    First tries deps.dev API response, then falls back to importlib.metadata.

    Args:
        response_dict (dict): Response dictionary from deps.dev API

    Returns:
        Optional[str]: GitHub repository URL if found, None otherwise
    """
    # Step 1: Try deps.dev API response
    links = deps_dict["package_version_data"]["links"]
    for link in links:
        if link["label"] == "SOURCE_REPO":
            return link["url"]

    # Step 2: Try importlib.metadata
    package_name = deps_dict["package_name"]
    try:
        url = get_package_url_pypi(package_name)
        if url:
            return url
    except Exception as e:
        logger.debug(f"Error getting URL from importlib.metadata: {e}")

    # Step 3: If both methods fail, log warning and return None
    logger.warning(f"No GitHub repository URL found for package {package_name}")
    return None


def get_package_url_pypi(package_name: str) -> Optional[str]:
    """
    Get package repository URL using PyPI API
    
    Args:
        package_name (str): Name of the Python package
        
    Returns:
        Optional[str]: Repository URL if found, None otherwise
    """
    try:
        response = requests.get(f"https://pypi.python.org/pypi/{package_name}/json", timeout=2)
        response.raise_for_status()
        
        data = response.json()
        info = data['info']
        
        # Check project_urls first
        if 'project_urls' in info and info['project_urls']:
            # First priority: Look for Repository or Source labels
            for label, url in info['project_urls'].items():
                if not url:
                    continue
                    
                if any(key.lower() in label.lower() for key in ['Repository', 'Source', 'Code']):
                    return url.strip().rstrip('/').rstrip('.git')
        
        # Second priority: Check homepage URL
        if info.get('home_page'):
            return info['home_page'].strip().rstrip('/').rstrip('.git')
                
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from PyPI for {package_name}: {e}")
        return None
