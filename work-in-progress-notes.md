# Work in Progress notes

## TODOs 

## Work packages

### WP1: Minimal end2end
- [ ] Return list of dependencies with their levels for specific project, using `requirements.txt` and/or `pyproject.toml`, or, alternatively, by entering the github handle (and thus reviewing another open source project)
- [ ] Minimal backend/frontend with FastAPI and Streamlit
- [ ] Deployed as docker / pypi package

### WP2: Issues overview, analysis, categorization 
- [ ] Issues: List number and statistics on issues (for open source libraries, which are on Github)
- [ ] Issues: Further synthesis for issues, i.e. summary, suggested topic category, etc
- [ ] Actors: List actors (contributors, commenters on issues, pull-requests) and related statistics
- [ ] Actors: Analyze tone of comments ("friendlyness" / "harshness" / ...), score helpfullness/involvement, flag "suspicious behaviour"
- [ ] Pictogram chart for issues over time, color coded by category

### WP3: Further features for dependency overview
- [ ] Dependencies graph
  - [ ] Model criticality of dependencies for specific set of applications
  - [ ] Also take into account committer information, see [blog post](https://blog.deps.dev/combining-dependencies-with-commits/), and [Python implementation](https://blog.deps.dev/assets/2023-11-29-combining-dependencies-with-commits/pagerank_deps.py)
- [ ] Parse and show Security Advisories (i.e. known vulnerabilities of dependencies) 
- [ ] Check security metrics using [OpenSSF ScoreCard](https://github.com/ossf/scorecard)



## Notes

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