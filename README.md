# openOwl - Open Source Monitoring and Security

## Summary
OpenOwl aims to monitor common open-source projects for their dependencies and related security-relevant information. We focus on analyzing our dependencies' issues and pull requests.

![Screenshot web app](assets/streamlit-screenshot.png)

## Features 
- See [work-in-progress-notes.md](work-in-progress-notes.md)


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
