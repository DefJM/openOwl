
import requests

def list_github_issues(owner, repo, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        # "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    issues = []
    page = 1
    
    while True:
        params = {"state": "open", "per_page": 100, "page": page}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        page_issues = response.json()
        if not page_issues:
            break
        
        issues.extend(page_issues)
        page += 1
    
    return issues

# # Usage example
# owner = "explodinggradients"
# repo = "ragas"
# token = "your_personal_access_token"

# all_issues = list_github_issues(owner, repo, token)

# for issue in all_issues:
#     print(f"#{issue['number']} - {issue['title']}")
