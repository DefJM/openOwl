from urllib.parse import quote
import pandas as pd

from openowl.logger_config import setup_logger

logger = setup_logger(__name__)


def get_packages(client, system_name, package_name):
    return client.get(f"/v3/systems/{system_name}/packages/{package_name}")


def get_default_version(raw_response):
    """parse default version from `get_packages` deps.dev api response"""
    try:
        default_version = next(
            version["versionKey"]["version"]
            for version in raw_response.json()["versions"]
            if version["isDefault"]
        )
        logger.info(f"The default version is: {default_version}")
    except StopIteration:
        logger.warning("No default version found.")
    return default_version


def get_dependencies(client, version_key_system, version_key_name, version_key_version):
    url = f"/v3/systems/{version_key_system}/packages/{version_key_name}/versions/{version_key_version}:dependencies"
    return client.get(url)


def get_version(client, version_key_system, version_key_name, version_key_version):
    url = f"/v3/systems/{version_key_system}/packages/{version_key_name}/versions/{version_key_version}"
    return client.get(url)


def get_advisory(client, advisory_key_id):
    url = f"/v3/advisories/{advisory_key_id}"
    return client.get(url)


def url_encode(string):
    return quote(string, safe="")


def get_deps_table(deps_json):
    df = pd.DataFrame([dep["versionKey"] for dep in deps_json["nodes"]])
    df["relation"] = pd.DataFrame([dep["relation"] for dep in deps_json["nodes"]])
    df = df.sort_values(by="relation")
    return df

def get_deps_stats(package_dependencies):
    df_deps = get_deps_table(package_dependencies)
    num_deps_total = len(df_deps.loc[df_deps["relation"].isin(["DIRECT", "INDIRECT"])])
    num_deps_direct = len(df_deps.loc[df_deps["relation"] == "DIRECT"])
    num_deps_indirect = len(df_deps.loc[df_deps["relation"] == "INDIRECT"])
    return num_deps_total, num_deps_direct, num_deps_indirect 