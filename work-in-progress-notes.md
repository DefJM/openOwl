# Work in Progress notes

## Next steps

### MVP

#### Features
- [x] Simple dependency screen
    - [x] Return list of dependencies with their levels for Github open source Python project, by entering the github handle
    - [x] List dependencies from open-souerce GitHub repositories
- [ ] Plot sentiments / toxicity of issue / pull request comments over time
- [ ] Get dependency graph from local Python project https://github.com/bndr/pipreqs
- [ ] Check dependencies for existing security advisories, using (which uses https://osv.dev)

#### Create pip-installable package
- [ ] Backend/frontend with FastAPI/Streamlit
- [ ] Run `pip install openowl`. Deploy as Pypi package with proper versioning


## Feature ideas

### Improve sentiment analysis
Actual toxic comments in Github issues and pull requests are hard to find. Current approach using Detoxify is not very good, developer-specific lingo often confuses the classifier. 
- [ ] Try out other models
- [ ] Try out LLMs with prompt engineering

### Per-dependency analysis with focus on **issues** and **pull-requests**
- [ ] Per-dependency analysis issues
    - [ ] Summarize current issues
      - [ ] synthesis of issues, what's being discussed, what are major topics spanning across issues? 
      - [ ] Are there topics and issues with high negativity / toxity?
    - [ ] Label issues for `security_relevance`, `positivity_negativity`
    - [ ] Visualize statistics on issues for each dependency
      - [ ] num issues with higher security relevance
      - [ ] num issues reporting relevant bugs
      - [ ] percentage of issues with significant negative vibe
- [ ] Per-dependency analysis pull-requests 
    - [ ] Scope as above for issues



### Analyze, categorize, and plot trends on issues and pull requests
- [ ] More advanced statistics on issues (kpis and trends):
  - [ ] `num_suspicious_issue_discussions`, `num_toxic_issues`, `num_issues_disagreement_on_if_is_bug` 
- [ ] More advanced statistics on pull requests (kpis and trends):
  - [ ] `num_open_pull_requests` per category

### Analyze actors
- [ ] Focus on actors: List actors (contributors, commenters on issues, pull-requests) and related statistics
- [ ] Focus on actors: Analyze tone of comments ("friendlyness" / "harshness" / ...), score helpfullness/involvement, flag "suspicious behaviour"
- [ ] Pictogram chart for issues over time, color coded by category

### Analyze how dependencies relate to each other
- [ ] Dependencies graph
  - [ ] Model criticality of dependencies for specific set of applications
  - [ ] Also take into account committer information, see [blog post](https://blog.deps.dev/combining-dependencies-with-commits/), and [Python implementation](https://blog.deps.dev/assets/2023-11-29-combining-dependencies-with-commits/pagerank_deps.py)
- [ ] Parse and show Security Advisories (i.e. known vulnerabilities of dependencies) 
- [ ] Check security metrics using [OpenSSF ScoreCard](https://github.com/ossf/scorecard)



## Notes

### Notes on graphs and user interface
- Provide easy-to-digest trends a la [apple health trends](https://support.apple.com/en-us/105003)

### Notes on serving
Serving will depend on what problem we solve. Need to dig deeper.
- We serve information and offer overview around dependencies and related issues through a UI.
- We operate automatic testing integrated into the CI/CD process, or through e.g. the Github Marketplace and integrated into Github Actions
- We offer a CLI tool, which can be used manually, but also as part of CI/CD

### Notes on parsing resolved list of packages from local python

- How to do this reliably? 
- First step start with Python
- Poetry is one option

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

### Notes on sentiment analysis
- So far the sentiment analysis is not very good. Need to improve.
- Explore other models / LLMs
  - Sentiment Analysis in the Era of Large Language Models: A Reality Check https://arxiv.org/abs/2305.15005
  - Hugging Face: https://huggingface.co/models?pipeline_tag=text-classification&sort=downloads&search=sentiment
  - https://whylabs.ai/learning-center/llm-use-cases/sentiment-analysis-with-large-language-models-llms
- For plotting: use library https://pythonhosted.org/calmap/#module-calmap?

- Plotting: There is a library for plotting calendars https://pythonhosted.org/calmap/#module-calmap?



## "Today I Learned"
