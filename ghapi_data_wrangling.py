import json
import os

import requests
from dotenv import load_dotenv

from openowl.ghapi import (
    get_diff_content,
    get_issue_details,
    get_issues,
    get_pull_requests,
)

load_dotenv()
owner = "psf"
repo = "requests"
github_token = os.environ.get("GITHUB_TOKEN")  # Optional, but recommended


### get all issues
# issues = get_github_issues(owner, repo, github_token)
# with open('data/ghapi_get_issues_requests.json', 'w') as file:
#     json.dump(issues, file, indent=2)
with open("data/ghapi_get_issues_requests.json", "r") as file:
    issues = json.load(file)

issue_map = {str(issue["number"]): issue for issue in issues}
i = issue_map["6793"]
print(i)

### get issue details
issue_number = 6711  # 6793
# issue_details = get_issue_details(owner, repo, issue_number, github_token)
# with open('data/ghapi_get_issue_details_requests_6711.json', 'w') as file:
#     json.dump(issue_details, file, indent=2)
with open("data/ghapi_get_issue_details_requests_6711.json", "r") as file:
    issue_details = json.load(file)







### get pull requests
# pulls = get_pull_requests(owner, repo, github_token)
# with open('data/ghapi_get_pulls_requests.json', 'w') as file:
#     json.dump(pulls, file, indent=2)
with open("data/ghapi_get_pulls_requests.json", "r") as file:
    pulls = json.load(file)

# pulls_summary = []
# for p in pulls:
#     pull_summary = {}
#     pull_summary["id"]=p["id"]
#     pull_summary["number"]=p["number"]
#     pull_summary["user"]={}
#     pull_summary["user"]["login"]=p["user"]["login"]
#     pull_summary["user"]["id"]=p["user"]["id"]
#     pull_summary["diff_url"]=p["diff_url"]
#     pull_summary["issue_url"]=p["issue_url"]
#     pull_summary["title"]=p["title"]
#     pull_summary["body"]=p["body"]
#     pulls_summary.append(pull_summary)

# for p in pulls_summary:
#     print(p["diff_url"])
#     p["diff"]=get_diff_content(p["diff_url"])

# with open('data/ghapi_get_pulls_requests_sum.json', 'w') as file:
#     json.dump(pulls_summary, file, indent=2)

with open("data/ghapi_get_pulls_requests_sum.json", "r") as file:
    pulls_summary = json.load(file)



### get pull request diff
diff_url = pulls_summary[5]["diff_url"]
# pull[0]["user"][["login", "id"]]
# pull = pulls[3:4]
# pull[0]["body"]
diff = get_diff_content(diff_url)
from pprint import pprint
pprint (diff)



