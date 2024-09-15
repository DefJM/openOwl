
import requests

def get_github_issues(owner, repo, token=None, state="open"):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    issues = []
    page = 1
    while True:
        params = {"state": state, "per_page": 100, "page": page}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        page_issues = response.json()
        if not page_issues:
            break
        issues.extend(page_issues)
        page += 1
    return issues


def get_issue_details(owner, repo, issue_number, token=None):
    base_url = "https://api.github.com"
    # Headers for authentication (if token is provided)
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    # 1. Get issue details
    issue_url = f"{base_url}/repos/{owner}/{repo}/issues/{issue_number}"
    issue_response = requests.get(issue_url, headers=headers)
    issue_data = issue_response.json()
    # 2. Get issue comments
    comments_url = f"{issue_url}/comments"
    comments_response = requests.get(comments_url, headers=headers)
    comments_data = comments_response.json()
    # 3. Combine issue data and comments
    full_issue_data = {
        "issue": issue_data,
        "comments": comments_data
    }
    return full_issue_data





# # Usage example
# owner = "explodinggradients"
# repo = "ragas"
# token = "your_personal_access_token"

# all_issues = list_github_issues(owner, repo, token)

# for issue in all_issues:
#     print(f"#{issue['number']} - {issue['title']}")
