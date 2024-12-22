import os

from dotenv import load_dotenv
from tinydb import Query, TinyDB
from tqdm import tqdm

from openowl.clients import OpenOwlClient
from openowl.db_utils import link_issue_to_dependency, upsert_dependency
from openowl.gh_api import filter_issue_details, get_issue_details, get_issues
from openowl.logger_config import setup_logger
from openowl.utils import extract_github_info, sort_version_list

logger = setup_logger(__name__)
load_dotenv()


def main():
    package_manager = "pypi"
    github_url = "https://github.com/pydantic/pydantic"
    package_version = None
    debug = False
    max_issues = 400

    # extract package info from github url
    package_owner, package_name = extract_github_info(github_url)

    # if no version is provided, get latest version
    if package_version is None:
        oowl_client = OpenOwlClient()
        package_versions = oowl_client.get_package_versions(
            package_manager, package_name
        )
        package_versions = sort_version_list(package_versions)
        package_version = package_versions[0]
        logger.info(f"No version provided, took the latest version: {package_version}")

    dependency = {
        "package_manager": package_manager,
        "owner": package_owner,
        "name": package_name,
        "version": package_version,
    }

    # Initialize/load TinyDB
    db = TinyDB(os.environ.get("PATH_DB"))
    dependencies_table = db.table("dependencies")
    issues_table = db.table("issues")
    issue_dependency_table = db.table("issue_dependency")

    # get github access token
    github_access_token = os.environ.get(
        "GITHUB_ACCESS_TOKEN"
    )  # Optional, but recommended

    dep_id = upsert_dependency(dependency, dependencies_table)
    owner = dependency["owner"]
    repo = dependency["name"]

    # get issues
    issues = get_issues(owner, repo, github_access_token)

    # limit num of issues for processing for debugging
    if debug:
        issues = issues[:25]
    elif max_issues:
        issues = issues[:max_issues]

    # get issues details and upsert to db
    for i in tqdm(issues, desc="Processing issues"):
        issue_number = i["number"]
        issue_id = i["id"]
        issue_details = get_issue_details(
            owner, repo, issue_number, github_access_token
        )
        issue = filter_issue_details(issue_details)
        issues_table.upsert(issue["issue"], Query().id == issue["issue"]["id"])
        # upsert_issue(issue["issue"])
        link_issue_to_dependency(i["id"], dep_id, issue_dependency_table)

    logger.info(
        f"Done! Added `{len(issues)}` issues for dependency '{package_name}', version '{package_version}' to database."
    )


if __name__ == "__main__":
    main()
