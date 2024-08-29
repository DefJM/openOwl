# Work in Progress notes

## TODOs 
- [ ] logic to take default version, if versions are missing in pyproject.toml or requirements.txt, plus logging this

## Work packages

### WP1: Minimal end2end
- [ ] Return list of dependencies with their levels for specific project, using `requirements.txt` and/or `pyproject.toml`, or, alternatively, by entering the github handle (and thus reviewing another open source project)
- [ ] Minimal backend/frontend with FastAPI and Streamlit
- [ ] Deployed as docker / pypi package

### WP2: Further features for dependency overview
- [ ] Dependencies graph
- [ ] Parse and show advisories (i.e. known vulnerabilities) of dependencies

### Further ideas
- [ ] Issues: List number and statistics on issues (for open source libraries, which are on Github)
- [ ] Issues: Further synthesis for issues, i.e. summary, suggested topic category, etc
- [ ] Actors: List actors (contributors, commenters on issues, pull-requests) and related statistics
- [ ] Actors: Analyze tone of comments ("friendlyness" / "harshness" / ...), score helpfullness/involvement, flag "suspicious behaviour"


## Notes

### Notes on serving
Serving will depend on what problem we solve. Need to dig deeper.
- We serve information and offer overview around dependencies and related issues through a UI.
- We operate automatic testing integrated into the CI/CD process, or through e.g. the Github Marketplace and integrated into Github Actions
- We offer a CLI tool, which can be used manually, but also as part of CI/CD





deps_scan
