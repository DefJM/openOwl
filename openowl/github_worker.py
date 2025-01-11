import requests

from openowl.logger_config import setup_logger
from openowl.repository import Repository
from openowl.github_api import GithubAPI
from openowl.db import DB

from dotenv import load_dotenv
import os

load_dotenv()

logger = setup_logger(__name__)


# Class to get github data for a given repository
class GithubWorker:
    def __init__(self, url, token=None, version=None):
        self.repository = Repository(url, version)
        self.api = GithubAPI(token=token)
        # initialize db
        self.db = DB(os.environ.get("PATH_DB"))

    def process_issues(self,owner, repo, token=None, state="open"):
        """Sync issues for a given repository with the database
        1. get issues using get_issues method from github_api.py
        2. upsert issues to db 
          - using json from api response
          - using upsert_issues method from db.py
        """
        issues = self.api.get_issues(owner, repo, state)
        self.db.upsert_issues(issues)


    
    def get_comments(self):
        """Sync comments (and further issue details) for a given repository with the database
        1. get issue details, including comments
        2. upsert issue details as additional data to db issue table
        3. upsert comments-related data to db comments table 
        """
        pass
