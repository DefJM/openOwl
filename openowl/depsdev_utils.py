from urllib.parse import quote


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
        print(f"The default version is: {default_version}")
    except StopIteration:
        print("No default version found.")
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
