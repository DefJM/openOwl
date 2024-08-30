from pprint import pprint

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from openowl.deps_local import check_files, clean_dependencies, parse_pyproject_toml
from openowl.clients import DepsDevClient
from openowl.depsdev_utils import (
    get_default_version,
    get_dependencies,
    get_packages,
    get_version,
)
from openowl.logger_config import setup_logger
from openowl.utils import extract_github_library_name, is_github_repo

logger = setup_logger(__name__)

app = FastAPI()


def scan_local(local_root_dir=None):
    if check_files(local_root_dir)["pyproject.toml"] == True:
        dependencies = parse_pyproject_toml()
    pprint(dependencies)
    # only take main dependencies, leave out dev-dependencies
    dependencies = dependencies["dependencies"]
    dependencies = clean_dependencies(dependencies)
    return dependencies


class InputRepoFromUrl(BaseModel):
    repo_url: str
    package_version: str | None = None


@app.post("/scan_from_url")
def scan_from_url(input: InputRepoFromUrl):
    repo_url = input.repo_url
    package_version = input.package_version

    if is_github_repo(repo_url):
        logger.info(f"URL is a valid GitHub repo: {repo_url}")
        package_name = extract_github_library_name(repo_url)
    else:
        logger.warning(f"URL is not a valid GitHub repo: {repo_url}")
    
    system_name = "pypi"
    depsdev_client = DepsDevClient()
    package_data = get_packages(depsdev_client, system_name, package_name)
    if package_version is None:
        package_version = get_default_version(package_data)
    package_version_data = get_version(
        depsdev_client, system_name, package_name, package_version
    )
    package_dependencies = get_dependencies(
        depsdev_client, system_name, package_name, package_version
    )

    return JSONResponse(
        content={
            "package_name": package_name,
            "package_version": package_version,
            "package_version_data": package_version_data.json(),
            "package_dependencies": package_dependencies.json(),
        }
    )
