import json
import os

import hashlib
import requests
from dotenv import load_dotenv
from tinydb import TinyDB, Query
from tinydb.table import Document

from openowl.gh_llm import get_issue_summarization

from openowl.gh_api import (
    get_diff_content,
    get_issue_details,
    filter_issue_details,
    get_issues,
    get_pull_requests,
)
from openowl.prompt_templates import bug_label_dict, issue_label_dict
load_dotenv()



def generate_dependency_hash(dependency):
    # Create a string that uniquely identifies the dependency
    unique_string = f"{dependency['name']}:{dependency['version']}"
    # Generate a SHA256 hash of the unique string
    return hashlib.sha256(unique_string.encode()).hexdigest()

def upsert_dependency(dependency):
    # Generate a hash ID for the dependency
    dep_id = generate_dependency_hash(dependency)
    dependency['id'] = dep_id
    # Upsert the dependency
    dependencies_table.upsert(dependency, Query().id == dep_id)
    return dep_id

def upsert_issue(issue):
    issues_table.upsert(issue, Query().id == issue['id'])

def link_issue_to_dependency(issue_id, dependency_id):
    issue_dependency_table.upsert(
        {'issue_id': issue_id, 'dependency_id': dependency_id},
        (Query().issue_id == issue_id) & (Query().dependency_id == dependency_id)
    )

def find_issue_by_id(issue_id):
    return issues_table.get(Query().id == issue_id)

def find_issues_for_dependency(dependency_id):
    IssueDepend = Query()
    links = issue_dependency_table.search(IssueDepend.dependency_id == dependency_id)
    return [find_issue_by_id(link['issue_id']) for link in links]

def update_issue_details(issue_id, new_details):
    return issues_table.update(new_details, Query().id == issue_id)


def main():

    # Initialize TinyDB
    path_db = os.environ.get("PATH_DB")
    db = TinyDB(path_db)
    dependencies_table = db.table('dependencies')
    issues_table = db.table('issues')
    issue_dependency_table = db.table('issue_dependency')

    # get github access token
    github_access_token = os.environ.get("GITHUB_ACCESS_TOKEN")  # Optional, but recommended


    # TODO: add loop over dependencies
    dependency = {
        'owner': "psf",
        'name': 'requests',
        'version': '2.26.0' # or None
    }
    dep_id = upsert_dependency(dependency)

    owner = dependency["owner"]
    repo = dependency["name"]

    # get issues
    issues = get_issues(owner, repo, github_access_token)
    issues = issues[-10:]


    # get issue details and upsert to db
    # i = issues[5]
    for i in issues:
        issue_number = i["number"]
        issue_id = i["id"]
        issue_details = get_issue_details(owner, repo, issue_number, github_access_token)
        issue = filter_issue_details(issue_details)
        issues_table.upsert(issue["issue"], Query().id == issue["issue"]['id'])
        # upsert_issue(issue["issue"])
        link_issue_to_dependency(i['id'], dep_id)
        



    # issue = issues_table.all()[1] 
    for issue in issues_table.all():
        issue_summarization = get_issue_summarization(
            issue,
            issue_label_dict,
            bug_label_dict,
            issue_summary_example,
        )
        issue["issue_summarization"] = issue_summarization
        issues_table.upsert(issue, Query().id == issue['id'])


































# # Get and update the issue in the database, linking it to the 'requests' dependency
# issue_id = get_and_update_issue(issue_number, 'requests')

# # Append additional information
# additional_info = {
#     "analysis_date": "2023-06-15",
#     "priority": "high",
#     "estimated_time": "3 hours"
# }
# update_issue_details(issue_id, {'additional_info': additional_info})

# # Retrieve and print the updated issue
# updated_issue = find_issue_by_id(issue_id)
# if updated_issue:
#     print("\nUpdated issue details:")
#     pprint(updated_issue)

# # Find all issues for the 'requests' dependency
# requests_issues = find_issues_for_dependency('requests')
# print(f"\nFound {len(requests_issues)} issues for 'requests' dependency:")
# for issue in requests_issues:
#     print(f"- Issue {issue['number']}: {issue['title']}")












# ### get all issues
# issues = get_issues(owner, repo, github_access_token)
# # with open('data/ghapi_get_issues_requests.json', 'w') as file:
# #     json.dump(issues, file, indent=2)
# # with open("data/ghapi_get_issues_requests.json", "r") as file:
# #     issues = json.load(file)


# ### get issue details
# issue_number = 6711  # 6793 #5536
# issue_details = get_issue_details(owner, repo, issue_number, github_access_token)
# # with open('data/ghapi_get_issue_details_requests_6711.json', 'w') as file:
# #     json.dump(issue_details, file, indent=2)
# # with open("data/ghapi_get_issue_details_requests_6711.json", "r") as file:
# #     issue_details = json.load(file)


# ### filter issue details
# issue_details_filtered = filter_issue_details(issue_details)
# # with open('data/ghapi_get_issue_details_requests_6711_filtered.json', 'w') as file:
# #     json.dump(issue_details_filtered, file, indent=2)
# # with open("data/ghapi_get_issue_details_requests_6711_filtered.json", "r") as file:
# #     issue_details_filtered = json.load(file)


# # Example usage:
# # with open('paste.txt', 'r') as file:
# #     data = json.load(file)
# # filtered_data = filter_issue_data(data)
# # with open('filtered_issue_data.json', 'w') as file:
# #     json.dump(filtered_data, file, indent=2)
# # print("Filtered data has been saved to 'filtered_issue_data.json'")












































# # Load the JSON data
# with open('paste.txt', 'r') as file:
#     data = json.load(file)

# # Filter the data
# filtered_data = filter_issue_data(data)

# # Save the filtered data to a new JSON file
# with open('filtered_issue_data.json', 'w') as file:
#     json.dump(filtered_data, file, indent=2)






# ### get pull requests
# # pulls = get_pull_requests(owner, repo, github_token)
# # with open('data/ghapi_get_pulls_requests.json', 'w') as file:
# #     json.dump(pulls, file, indent=2)
# with open("data/ghapi_get_pulls_requests.json", "r") as file:
#     pulls = json.load(file)

# # pulls_summary = []
# # for p in pulls:
# #     pull_summary = {}
# #     pull_summary["id"]=p["id"]
# #     pull_summary["number"]=p["number"]
# #     pull_summary["user"]={}
# #     pull_summary["user"]["login"]=p["user"]["login"]
# #     pull_summary["user"]["id"]=p["user"]["id"]
# #     pull_summary["diff_url"]=p["diff_url"]
# #     pull_summary["issue_url"]=p["issue_url"]
# #     pull_summary["title"]=p["title"]
# #     pull_summary["body"]=p["body"]
# #     pulls_summary.append(pull_summary)

# # for p in pulls_summary:
# #     print(p["diff_url"])
# #     p["diff"]=get_diff_content(p["diff_url"])

# # with open('data/ghapi_get_pulls_requests_sum.json', 'w') as file:
# #     json.dump(pulls_summary, file, indent=2)

# with open("data/ghapi_get_pulls_requests_sum.json", "r") as file:
#     pulls_summary = json.load(file)



# ### get pull request diff
# diff_url = pulls_summary[5]["diff_url"]
# # pull[0]["user"][["login", "id"]]
# # pull = pulls[3:4]
# # pull[0]["body"]
# diff = get_diff_content(diff_url)
# from pprint import pprint
# pprint (diff)






# issue_new_url = Path("data/ghapi_get_issue_details_requests_5536_filtered.json")
# with open(issue_new_url, "r") as file:
#     issue_new_dict = json.load(file)

# issue_example_url = Path("data/ghapi_get_issue_details_requests_6711_filtered.json")
# with open(issue_example_url, "r") as file:
#     issue_example = json.load(file)

# # issue_summary_example_dict = {
# #     "tldr": "Requests 2.32.0 strips double slashes in URLs, breaking AWS S3 presigned URLs and potentially other services.",
# #     "security_relevancy": 2,
# #     "issue_labels": ["compatibility", "url-handling", "aws-s3"],
# #     "positivity_negativity": 3,
# #     "bug_labels": ["regression", "breaking-change"],
# # }

# issue_summary_example = """
# <tldr>Requests 2.32.0 strips double slashes in URLs, breaking AWS S3 presigned URLs and potentially other services.</tldr>
# <security_relevancy>2</security_relevancy>
# <issue_label>compatibility</issue_label>
# <issue_label>url-handling</issue_label>
# <issue_label>aws-s3</issue_label>
# <positivity_negativity>3</positivity_negativity>
# <bug_label>regression</bug_label>
# <bug_label>breaking-change</bug_label>
# """

# issue_summarization = get_issue_summarization(
#     issue_new_dict,
#     issue_label_dict,
#     bug_label_dict,
#     issue_summary_example,
# )
# pprint(issue_summarization)


