import os
import tomllib


def find_project_root(start_path="."):
    """
    Find the root directory of the project.
    """
    root_indicators = ["setup.py", ".git", "pyproject.toml", "requirements.txt"]
    current_path: str = os.path.abspath(start_path)

    while True:
        if any(
            os.path.exists(os.path.join(current_path, indicator))
            for indicator in root_indicators
        ):
            return current_path
        parent_path = os.path.dirname(current_path)
        if parent_path == current_path:  # Reached the system root directory
            return None
        current_path = parent_path


def check_files(directory=None):
    """
    Check for the existence of requirements.txt and pyproject.toml in the project root directory.
    """
    if directory is None:
        directory = find_project_root()
        if directory is None:
            raise ValueError(
                "Unable to detect project root. Please specify a directory."
            )
    files_to_check = ["requirements.txt", "pyproject.toml"]
    results = {}
    for file in files_to_check:
        file_path: str = os.path.join(directory, file)
        results[file] = os.path.isfile(file_path)
    return results


def parse_pyproject_toml(directory=None):
    """
    Parse the pyproject.toml file and extract the dependencies and dev-dependencies with their versions.
    """
    if directory is None:
        directory = find_project_root()
        if directory is None:
            raise ValueError(
                "Unable to detect project root. Please specify a directory."
            )

    pyproject_path = os.path.join(directory, "pyproject.toml")
    if not os.path.exists(pyproject_path):
        raise FileNotFoundError(f"pyproject.toml not found in {directory}")
    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)

    result = {"dependencies": {}, "dev-dependencies": {}}
    if "tool" in pyproject_data and "poetry" in pyproject_data["tool"]:
        poetry_data = pyproject_data["tool"]["poetry"]
        # Parse regular dependencies
        if "dependencies" in poetry_data:
            result["dependencies"] = parse_poetry_dependencies(
                poetry_data["dependencies"]
            )
        # Parse dev-dependencies
        if (
            "group" in poetry_data
            and "dev" in poetry_data["group"]
            and "dependencies" in poetry_data["group"]["dev"]
        ):
            result["dev-dependencies"] = parse_poetry_dependencies(
                poetry_data["group"]["dev"]["dependencies"]
            )
    return result


def parse_poetry_dependencies(dependencies_dict):
    """Helper function to parse dependencies from poetry"""
    parsed = {}
    for package, version in dependencies_dict.items():
        if isinstance(version, str):
            parsed[package] = {"version": version, "dependencies": {}}
        elif isinstance(version, dict) and "version" in version:
            parsed[package] = {"version": version["version"], "dependencies": {}}
    return parsed


def strip_version_specs(version_spec):
    if version_spec.startswith("^"):
        return version_spec[1:]
    elif version_spec.startswith("~"):
        return version_spec[1:]
    else:
        return version_spec


def strip_version_specs(version):
    specifiers = ["^", "~", ">", "<", ">=", "<=", "==", "!="]
    for spec in specifiers:
        if version.startswith(spec):
            version = version.lstrip(spec)
        version = version.strip()
    if "," in version:
        version = version.split(",")[0].strip()
    return version


def remove_python_dependency(dependencies):
    return {k: v for k, v in dependencies.items() if k.lower() != "python"}


def clean_dependencies(dependencies):
    dependencies = remove_python_dependency(dependencies)
    cleaned = {}
    for package, info in dependencies.items():
        cleaned[package] = {
            "version": strip_version_specs(info["version"]),
            "dependencies": {},
        }
    return cleaned
