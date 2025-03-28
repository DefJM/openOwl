import requests
from tqdm import tqdm

from openowl.logger_config import setup_logger

logger = setup_logger(__name__)


class GithubAPI:
    def __init__(self, token=None, api_version="2022-11-28"):
        self.token = token
        self.api_version = api_version
        self.headers = {
            "X-GitHub-Api-Version": self.api_version,
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def get_issues(self, owner, repo, state="open", since=None):
        """Get issues for a given package with progress bar.

        Args:
            owner (str): Repository owner
            repo (str): Repository name
            state (str): Issue state ('open', 'closed', or 'all')
            since (str): Only show issues updated after given time. Must be a timestamp
                in ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ

        Returns:
            list: List of issue dictionaries
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        issues = []
        page = 1

        # Set up initial parameters
        params = {
            "state": state,
            "per_page": 100,
            "page": page,
            "sort": "updated",  # Sort by update time to work better with since parameter
            "direction": "desc",  # Get most recently updated first
        }
        if since:
            params["since"] = since

        # First request to get initial batch of issues
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        # Get first batch of issues
        first_batch = response.json()
        issues.extend(first_batch)

        # Initialize progress bar with a default size that will adjust
        with tqdm(desc="Fetching issues") as pbar:
            pbar.update(len(first_batch))

            while True:
                page += 1
                params["page"] = page
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()

                page_issues = response.json()
                if not page_issues:
                    break

                issues.extend(page_issues)
                pbar.update(len(page_issues))

        return issues

    def get_comments(self, owner, repo, issue_number):
        """Get comments for a given issue.

        Args:
            owner (str): Repository owner
            repo (str): Repository name
            issue_number (int): Issue number

        Returns:
            list: List of comment dictionaries
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
        comments = []
        page = 1

        # Set up initial parameters
        params = {"per_page": 100, "page": page}

        # First request to get initial batch of comments
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        # Get first batch of comments
        first_batch = response.json()
        comments.extend(first_batch)

        # Continue fetching pages until no more results
        while len(first_batch) == params["per_page"]:
            page += 1
            params["page"] = page
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            page_comments = response.json()
            if not page_comments:
                break

            comments.extend(page_comments)

        return comments

    def get_all_issue_comments(self, owner, repo, since=None):
        """Get all comments for all issues in a repository with progress bar.

        Args:
            owner (str): Repository owner
            repo (str): Repository name
            since (str): Only show comments updated after given time (ISO 8601 format)

        Returns:
            list: List of comment dictionaries
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/comments"
        comments = []
        page = 1

        # Set up initial parameters
        params = {"per_page": 100, "page": page, "sort": "updated", "direction": "desc"}

        if since:
            params["since"] = since

        # First request to get initial batch of comments
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        # Get first batch of comments
        first_batch = response.json()
        comments.extend(first_batch)

        # Initialize progress bar with a default size that will adjust
        with tqdm(desc="Fetching all issue comments") as pbar:
            pbar.update(len(first_batch))

            while True:
                page += 1
                params["page"] = page
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()

                page_comments = response.json()
                if not page_comments:
                    break

                comments.extend(page_comments)
                pbar.update(len(page_comments))

        return comments

    def get_pull_requests(self, owner, repo):
        """Get pull requests for a given package"""
        pass
