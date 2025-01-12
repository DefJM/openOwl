from dotenv import load_dotenv
import os

from openowl.github_api import GithubAPI
from openowl.github_worker import GithubWorker
from openowl.repository import Repository
from openowl.db import DB

load_dotenv()

# Test script for debugging workers and db functions

# github_url="https://github.com/pydantic/pydantic"
# github_url="https://github.com/pandas-dev/pandas"
# github_url="https://github.com/psf/requests"
github_url="https://github.com/formbricks/formbricks"


package_version=None
token = os.environ.get("GITHUB_ACCESS_TOKEN")

worker = GithubWorker(github_url, package_version, token)
worker.process_issues(token=token, update=False, state="all", since=None)

######################################################################

repository = Repository(github_url, package_version)
# api = GithubAPI(token=os.environ.get("GITHUB_ACCESS_TOKEN"))

# # Initialize db
db = DB(os.environ.get("PATH_DB"))
# db.upsert_repository(repository)

# # Get and upsert issues
# issues = api.get_issues(repository.owner, repository.name, state="all", since=None)
# db.upsert_issues(issues)

# # Example query to get all issues for the pydantic repository since 2024-11-18
github_url_list = [
    # "https://github.com/pydantic/pydantic",
    # "https://github.com/pandas-dev/pandas",
    # "https://github.com/psf/requests", 
    "https://github.com/formbricks/formbricks"
]
issues = db.query_issues(github_url_list, state="all", since=None)

# latest_update = db.query_lastest_update_issues(github_url)

######################################################################

repository = Repository(github_url, package_version)

# # Initialize db
db = DB(os.environ.get("PATH_DB"))

api = GithubAPI(token=os.environ.get("GITHUB_ACCESS_TOKEN"))
issue_number = "3075"
issues
comments = api.get_comments(repository.owner, repository.name, issue_number)

