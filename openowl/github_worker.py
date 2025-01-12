import os
from datetime import datetime

from dotenv import load_dotenv

from openowl.db import DB
from openowl.github_api import GithubAPI
from openowl.logger_config import setup_logger
from openowl.repository import Repository

load_dotenv()

logger = setup_logger(__name__)


# Class to get github data for a given repository
class GithubWorker:
    def __init__(self, url, version=None, token=None):
        self.api = GithubAPI(token=os.environ.get("GITHUB_ACCESS_TOKEN"))
        self.db = DB(os.environ.get("PATH_DB"))
        self.repository = Repository(url, version)
        self.repository_id = self.db.upsert_repository(self.repository)

    def process_issues(self, state="all", since=None, update=True):
        """Process and sync repository issues with the database.

        Fetches issues from GitHub API and upserts them into the database. If update=True,
        only fetches issues updated since the last sync, overwriting any provided since parameter.

        Args:
            token (str, optional): GitHub API token. Defaults to None.
            state (str, optional): Issue state to fetch ('open', 'closed', 'all'). Defaults to 'all'.
            since (str, optional): Only fetch issues updated after this timestamp (ISO 8601).
                Ignored if update=True. Defaults to None.
            update (bool, optional): If True, only fetch issues since last update,
                overriding since parameter. Defaults to True.

        Returns:
            None
        """
 
        if update:
            since = self.db.query_lastest_update_issues(self.repository.url)
        
        # Process issues
        issues = self.api.get_issues(
            self.repository.owner,
            self.repository.name,
            state=state,
            since=since,
        )
        self.db.upsert_issues(issues, self.repository_id)
        logger.info(f"Upserted {len(issues)} issues for repository {self.repository.url}")

        # TODO: Update user table from issues (i.e. link existing users to the new issues, and create new users if not found)

    def process_comments(self, since=None,update=True):
        """TODO: Sync comments (and further issue details) for a given repository with the database
        1. get issue details, including comments
        2. upsert issue details as additional data to db issue table
        3. upsert comments-related data to db comments table
        """
        pass
