# openOwl - Open Source Monitoring and Security

## Summary
OpenOwl aims to monitor common open-source projects for their dependencies and related security-relevant information. We focus on analyzing our dependencies' issues and pull requests.

![Screenshot web app](assets/streamlit-screenshot.png)

## Features MVP (Work in Progress)
- [ ] Simple dependency screen
    - [x] Return list of dependencies with their levels for Github open source Python project, by entering the github handle
    - [ ] Return list of dependencies with their levels for local Python project, using `requirements.txt` and/or `pyproject.toml`
    - [x] List dependencies from open-souerce GitHub repositories
    - [x] List dependencies from local Python project
    - [ ] Check dependencies for existing security advisories, using (which uses https://osv.dev)
- [ ] Plot sentiment of issue / pull request comments over time, 1) aggregated per week, 2) as individual datapoints
- [ ] Per-dependency analysis with focus on **issues**
    - [ ] Summarize current issues
      - [ ] synthesis of issues, what's being discussed, what are major topics spanning across issues? 
      - [ ] Are there topics and issues with high negativity / toxity?
    - [ ] Label issues for `security_relevance`, `positivity_negativity`
    - [ ] Visualize statistics on issues for each dependency
      - [ ] num issues with higher security relevance
      - [ ] num issues reporting relevant bugs
      - [ ] percentage of issues with significant negative vibe
- [ ] Per-dependency analysis with focus on **pull-requests** (first, stick to what's being done above for issues)
- [ ] Backend/frontend with FastAPI/Streamlit
- [ ] Run `pip install openowl`. Deploy as Pypi package with proper versioning

See [work-in-progress](work-in-progress-notes.md) for further feature ideas, notes and research


## Getting started

Start fast-api server
```Bash
poetry run uvicorn openowl.api:app --reload
```

Open Streamlit dashboard
```Bash
poetry run streamlit run openowl/app.py 
```

## Limitations

- MVP works only for Python Package Index (PyPi) 


## Further notes
