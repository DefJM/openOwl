import requests

from openowl.logger_config import setup_logger

logger = setup_logger(__name__)


def get_issues(owner, repo, token=None, state="open"):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    issues = []
    page = 1
    while True:
        params = {"state": state, "per_page": 100, "page": page}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        page_issues = response.json()
        if not page_issues:
            break
        issues.extend(page_issues)
        page += 1
    return issues


def get_issue_details(owner, repo, issue_number, token=None):
    """
    Fetch detailed information about a specific GitHub issue, including its comments.

    Args:
        owner (str): The owner of the repository.
        repo (str): The name of the repository.
        issue_number (int): The number of the issue to fetch.
        token (str, optional): GitHub API token for authentication.

    Returns:
        dict: A dictionary containing the issue data and its comments.
    """
    base_url = "https://api.github.com"
    # Headers for authentication (if token is provided)
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    # 1. Get issue details
    issue_url = f"{base_url}/repos/{owner}/{repo}/issues/{issue_number}"
    issue_response = requests.get(issue_url, headers=headers)
    issue_data = issue_response.json()
    # 2. Get issue comments
    comments_url = f"{issue_url}/comments"
    comments_response = requests.get(comments_url, headers=headers)
    comments_data = comments_response.json()
    # 3. Combine issue data and comments
    full_issue_data = {"issue": issue_data, "comments": comments_data}
    return full_issue_data


def filter_issue_details(data):
    """
    Filter and extract relevant details from GitHub issue data.

    This function takes the full issue data and filters out specific keys
    for the issue, user, reactions, assignees, and comments to create a
    more concise representation of the issue details.

    Args:
        data (dict): The full GitHub issue data including comments.

    Returns:
        dict: A filtered dictionary containing relevant issue details.
    """
    issue_keys = [
        "html_url",
        "id",
        "number",
        "title",
        "created_at",
        "updated_at",
        "closed_at",
        "body",
        "author_association",
        "comments",
        "state",
    ]
    user_keys = ["login", "id", "site_admin"]
    comment_keys = [
        "url",
        "id",
        "created_at",
        "updated_at",
        "author_association",
        "body",
        "reactions",
        "performed_via_github_app",
    ]
    filtered_data = {
        "issue": {key: data["issue"][key] for key in issue_keys if key in data["issue"]}
    }
    # Filter user data
    if "user" in data["issue"]:
        filtered_data["issue"]["user"] = {
            key: data["issue"]["user"][key]
            for key in user_keys
            if key in data["issue"]["user"]
        }
    # Filter reactions
    if "reactions" in data["issue"]:
        filtered_data["issue"]["reactions"] = data["issue"]["reactions"]
    # Filter assignees
    if "assignees" in data["issue"]:
        filtered_data["issue"]["assignees"] = data["issue"]["assignees"]
    # Filter comments
    if "comments" in data:
        filtered_data["issue"]["comments_list"] = []
        for comment in data["comments"]:
            filtered_comment = {
                key: comment[key] for key in comment_keys if key in comment
            }
            # Filter user data for each comment
            if "user" in comment:
                filtered_comment["user"] = {
                    key: comment["user"][key]
                    for key in user_keys
                    if key in comment["user"]
                }
            filtered_data["issue"]["comments_list"].append(filtered_comment)
    return filtered_data


def get_pull_requests(owner, repo, token, state="open"):
    """
    Fetch all pull requests for a given repository.

    Args:
        owner (str): The owner of the repository.
        repo (str): The name of the repository.
        token (str): GitHub API token for authentication.
        state (str, optional): State of pull requests to fetch. Defaults to "open".

    Returns:
        list: A list of dictionaries containing pull request data.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    params = {"state": state}
    all_prs = []
    page = 1

    while True:
        response = requests.get(url, headers=headers, params={**params, "page": page})
        response.raise_for_status()
        prs = response.json()
        if not prs:
            break
        all_prs.extend(prs)
        page += 1

    return all_prs


def get_diff_content(diff_url):
    """
    Retrieve the content of a diff from a given URL.

    Args:
        diff_url (str): The URL of the diff to retrieve.

    Returns:
        str or None: The content of the diff if successful, None otherwise.
    """
    response = requests.get(diff_url)
    if response.status_code == 200:
        return response.text
    else:
        logger.error(f"Failed to retrieve diff. Status code: {response.status_code}")
        return None
