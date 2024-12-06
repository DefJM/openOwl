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

### Docker-based development

If you prefer to use docker for development, you can use the provided `docker-compose.yml` file.

You can start the docker-based setup with the following command:

```bash
docker compose up --build
```

Do not forget to create a GitHub personal access token in GitHub and add it to the `.env` file in the directory `openowl/`. The `.env` file should look like this:

```txt
GITHUB_ACCESS_TOKEN="github_pat_1234567890"
```

## Limitations

- MVP works only for Python Package Index (PyPi) 


## Further notes
