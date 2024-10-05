# Work in Progress notes

## TODOs 

## Work packages

### WP2: Trending on issues, analysis, categorization 
- [ ] More advanced statistics on issues (kpis and trends):
  - [ ] `num_suspicious_issue_discussions`, `num_toxic_issues`, `num_issues_disagreement_on_if_is_bug` 
- [ ] More advanced statistics on pull requests (kpis and trends):
  - [ ] `num_open_pull_requests` per category
- [ ] More advanced labelling and summarization of open issues
- [ ] More advanced labelling and summarization of pull requests 
- [ ] Further repo kpis and trends (need to check if this is not already provided somewhere)
  - [ ] `release_frequency`, `time_to_resolve_critical_bugs`,`maintainer_activity`, 
- [ ] Focus on actors: List actors (contributors, commenters on issues, pull-requests) and related statistics
- [ ] Focus on actors: Analyze tone of comments ("friendlyness" / "harshness" / ...), score helpfullness/involvement, flag "suspicious behaviour"
- [ ] Pictogram chart for issues over time, color coded by category


### WP3: Further features for dependency overview
- [ ] Dependencies graph
  - [ ] Model criticality of dependencies for specific set of applications
  - [ ] Also take into account committer information, see [blog post](https://blog.deps.dev/combining-dependencies-with-commits/), and [Python implementation](https://blog.deps.dev/assets/2023-11-29-combining-dependencies-with-commits/pagerank_deps.py)
- [ ] Parse and show Security Advisories (i.e. known vulnerabilities of dependencies) 
- [ ] Check security metrics using [OpenSSF ScoreCard](https://github.com/ossf/scorecard)



## Notes

### Idea: provide trends
- Provide trends a la [apple health trends](https://support.apple.com/en-us/105003)

### Notes on serving
Serving will depend on what problem we solve. Need to dig deeper.
- We serve information and offer overview around dependencies and related issues through a UI.
- We operate automatic testing integrated into the CI/CD process, or through e.g. the Github Marketplace and integrated into Github Actions
- We offer a CLI tool, which can be used manually, but also as part of CI/CD


### Parsing resolved list of packages from lacal python? 

Use poetry?

```Python
import subprocess
import json

def get_installed_packages():
    result = subprocess.run(['poetry', 'show', '--format', 'json'], capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Error running 'poetry show': {result.stderr}")
    
    packages = json.loads(result.stdout)
    return {pkg['name']: pkg['version'] for pkg in packages}

installed_packages = get_installed_packages()
for name, version in installed_packages.items():
    print(f"{name}: {version}")
```