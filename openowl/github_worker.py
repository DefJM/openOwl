import requests

from openowl.logger_config import setup_logger
from openowl.package import Package
from openowl.github_api import GithubAPI

from dotenv import load_dotenv
import os

load_dotenv()

logger = setup_logger(__name__)


# Class to get github data for a given package
class GithubWorker:
    def __init__(self, url, token=None, version=None):
        self.package = Package(url, version)
        self.api = GithubAPI(token=token)

    def process_issues(self,owner, repo, token=None, state="open"):
        """Sync issues for a given package with the database
        1. get issues
        2. upsert issues to db
        3. upsert issue_dependency to db
        """

    
    def get_pull_requests(self):
        pass
    
    def get_comments(self):
        """Sync comments (and further issue details) for a given package with the database
        1. get issue details, including comments
        2. upsert issue details as additional data to db issue table
        3. upsert comments-related data to db comments table 
        """
        pass
    
    def process_pull_requests(self):
        """Sync pull requests for a given package with the database"""
        pass