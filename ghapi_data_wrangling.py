import json

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


# # API calls to get all issues
# issues = get_github_issues(owner, repo, github_token)
# with open('data/ghapi_get_issues_requests.json', 'w') as file:
#     json.dump(issues, file, indent=2)
with open("data/ghapi_get_issues_requests.json", "r") as file:
    issues = json.load(file)

issue_map = {str(issue["number"]): issue for issue in issues}
i = issue_map["6793"]
print(i)


issue_number = 6777  # 6793
# issue_details = get_issue_details(owner, repo, issue_number, github_token)
# with open('data/ghapi_get_issue_details_requests.json', 'w') as file:
#     json.dump(issue_details, file, indent=2)
with open("data/ghapi_get_issue_details_requests.json", "r") as file:
    issue_details = json.load(file)


# pulls = get_pull_requests(owner, repo, github_token)
# with open('data/ghapi_get_pulls_requests.json', 'w') as file:
#     json.dump(pulls, file, indent=2)
with open("data/ghapi_get_pulls_requests.json", "r") as file:
    pulls = json.load(file)


# pulls_sum = []
# for p in pulls:
#     pull_sum = {}
#     pull_sum["id"]=p["id"]
#     pull_sum["number"]=p["number"]
#     pull_sum["user"]={}
#     pull_sum["user"]["login"]=p["user"]["login"]
#     pull_sum["user"]["id"]=p["user"]["id"]
#     pull_sum["diff_url"]=p["diff_url"]
#     pull_sum["issue_url"]=p["issue_url"]
#     pull_sum["title"]=p["title"]
#     pull_sum["body"]=p["body"]
#     pulls_sum.append(pull_sum)

# for p in pulls_sum:
#     print(p["diff_url"])
#     p["diff"]=get_diff_content(p["diff_url"])

# with open('data/ghapi_get_pulls_requests_sum.json', 'w') as file:
#     json.dump(pulls_sum, file, indent=2)

with open("data/ghapi_get_pulls_requests_sum.json", "r") as file:
    pulls_sum = json.load(file)


diff_url = pulls[5]["diff_url"]

# pull[0]["user"][["login", "id"]]
# pull = pulls[3:4]
# pull[0]["body"]

diff = requests.get(diff_url)
diff.text
