from dotenv import load_dotenv
import os

from openowl.github_api import GithubAPI
from openowl.github_worker import GithubWorker
from openowl.repository import Repository
from openowl.db import DB

load_dotenv()


github_url="https://github.com/pydantic/pydantic"
package_version=None
debug=True

repository = Repository(github_url, package_version)
api = GithubAPI(token=os.environ.get("GITHUB_ACCESS_TOKEN"))

# initialize db
db = DB(os.environ.get("PATH_DB"))

# First upsert repository to get repository_id
db.upsert_repository(repository)

# Then get and upsert issues
issues = api.get_issues(repository.owner, repository.name)
db.upsert_issues(issues)


repository.owner
repository.name
repository.version
repository.platform
