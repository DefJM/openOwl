# openOwl - Open Source Monitoring and Security

## Summary
OpenOwl provides analysis and monitoring for dependencies and related security-relevant information. 
- [ ] List dependencies from local Python projects, or open-souerce GitHub repositories
- [ ] Check dependencies for existing security advisories, using (which uses https://osv.dev)

![Screenshot web app](assets/streamlit-screenshot.png)


## Getting started

Start the fast-api server
```Bash
poetry run uvicorn openowl.api:app --reload
```

Open the Streamlit dashboard
```Bash
poetry run streamlit run openowl/app.py 
```



## Further notes
See [work-in-progress](work-in-progress-notes.md) for upcoming tasks, notes and research
