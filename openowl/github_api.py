import requests
from openowl.logger_config import setup_logger

logger = setup_logger(__name__)

class GithubAPI:
    def __init__(self, token=None):
        self.token = token
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def get_issues(self, owner, repo, state="open"):
        """Get issues for a given package"""
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        issues = []
        page = 1
        while True:
            params = {"state": state, "per_page": 100, "page": page}
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            page_issues = response.json()
            if not page_issues:
                break
            issues.extend(page_issues)
            page += 1
        return issues
        
    def get_issue_details(self, owner, repo, issue_number):
        """Get issue details for a given issue"""
        pass 


    def get_pull_requests(self, owner, repo):
        """Get pull requests for a given package"""
        pass