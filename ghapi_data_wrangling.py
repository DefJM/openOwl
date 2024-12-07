import os

from dotenv import load_dotenv
from tinydb import Query, TinyDB
from tqdm import tqdm

from openowl.clients import OpenOwlClient
from openowl.db_utils import upsert_dependency
from openowl.gh_api import filter_issue_details, get_issue_details, get_issues
from openowl.gh_llm import get_issue_summarization
from openowl.gh_sentiment_llm_guard import get_toxicity_scores
from openowl.logger_config import setup_logger
from openowl.utils import sort_version_list, extract_github_info

logger = setup_logger(__name__)
load_dotenv()


def upsert_issue(issue, issues_table):
    """Upsert issue to database."""
    issues_table.upsert(issue, Query().id == issue["id"])


def link_issue_to_dependency(issue_id, dependency_id, issue_dependency_table):
    """Link issue to dependency in database."""
    issue_dependency_table.upsert(
        {"issue_id": issue_id, "dependency_id": dependency_id},
        (Query().issue_id == issue_id) & (Query().dependency_id == dependency_id),
    )


def find_issue_by_id(issue_id, issues_table):
    """Find issue by id in database."""
    return issues_table.get(Query().id == issue_id)


def find_issues_for_dependency(dependency_id, issue_dependency_table, issues_table):
    """Find issues for dependency in database."""
    IssueDepend = Query()
    links = issue_dependency_table.search(IssueDepend.dependency_id == dependency_id)
    return [find_issue_by_id(link["issue_id"], issues_table) for link in links]


def update_issue_details(issue_id, new_details, issues_table):
    """Update issue details in database."""
    return issues_table.update(new_details, Query().id == issue_id)


def summarize_issues(issues_table, default_model):
    """Summarize issues in database."""
    for issue in issues_table.all():
        issue_summarization = get_issue_summarization(
            issue,
            default_model,
        )
        issue["issue_summarization"] = issue_summarization
        issues_table.upsert(issue, Query().id == issue["id"])

    from urllib.parse import urlparse



def main():
    DEFAULT_MODEL_ISSUE_SUMMARY = "claude-3-haiku-20240307"

    DEBUG = True  # limit num of issues for debugging

    # Example package
    package_manager = "pypi"
    github_url = "https://github.com/pandas-dev/pandas/bla"
    package_owner, package_name = extract_github_info(github_url)
    version = None

    # if no version is provided, get latest version
    if version is None:
        oowl_client = OpenOwlClient()
        package_versions = oowl_client.get_package_versions(
            package_manager, package_name
        )
        package_versions = sort_version_list(package_versions)
        version = package_versions[0]
        logger.info(f"No version provided, took the latest version: {version}")

    # Initialize/load TinyDB
    db = TinyDB(os.environ.get("PATH_DB"))
    dependencies_table = db.table("dependencies")
    issues_table = db.table("issues")
    issue_dependency_table = db.table("issue_dependency")

    # get github access token
    github_access_token = os.environ.get(
        "GITHUB_ACCESS_TOKEN"
    )  # Optional, but recommended

    # TODO: add loop over dependencies

    dependency = {
        "package_manager": package_manager,
        "owner": package_owner,
        "name": package_name,
        "version": version,
    }
    dep_id = upsert_dependency(dependency, dependencies_table)

    owner = dependency["owner"]
    repo = dependency["name"]

    # get issues
    issues = get_issues(owner, repo, github_access_token)

    # get issue details and upsert to db
    # limit num of issues for debugging: 10
    if DEBUG:
        issues = issues[:10]
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


    # WIP ############################################################
    # get toxicity scores, add them to the issues table and obtain dataframe
    comments_df = get_toxicity_scores(issues_table)
    # plot toxicity over time
    comments_df.plot(kind="line", x="datetime", y="toxicity")
    # threshold for toxic comments
    comments_df["is_toxic"] = comments_df["toxicity"] > 0.04

    # print toxic comments
    toxic_comments_df = comments_df.loc[comments_df["is_toxic"]]
    for _, row in toxic_comments_df.iterrows():
        print(f"Toxicity: {row['toxicity']:.4f}")
        print(f"Comment: {row['comment_details']}\n")
    # toxic_comments = toxic_comments_df["comment_details"].tolist()


if __name__ == "__main__":
    main()
