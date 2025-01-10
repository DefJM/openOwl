from dotenv import load_dotenv
import os

from openowl.github_api import GithubAPI
from openowl.github_worker import GithubWorker
from openowl.package import Package

load_dotenv()



github_url="https://github.com/pydantic/pydantic"
package_version=None
debug=True

package = Package(github_url, package_version)
api = GithubAPI(token=os.environ.get("GITHUB_ACCESS_TOKEN"))

issues = api.get_issues(package.owner, package.name)


package.owner
package.name
package.version
package.platform
