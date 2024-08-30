import requests
from urllib.parse import urljoin 


class DepsDevClient(requests.Session):
    def __init__(self) -> None:
        super().__init__()
        self.baseurl = "https://api.deps.dev"
        self.headers.update({"Content-Type": "application/json"})

    def request(self, method, url, *args, **kwargs):
        return super().request(method, urljoin(self.baseurl, url), *args, **kwargs)




class OpenOwlClient(requests.Session):
    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        super().__init__()
        self.base_url = base_url
        self.headers.update({
            "accept": "application/json",
            "Content-Type": "application/json"
        })

    def request(self, method, url, *args, **kwargs):
        return super().request(method, urljoin(self.base_url, url), *args, **kwargs)

    def scan_from_url(self, repo_url, package_version = None):
        """
        Scan a repository from its URL, optionally specifying a package version.
        """
        url = "/scan_from_url"
        data = {"repo_url": repo_url}
        if package_version:
            data["package_version"] = package_version
        
        response = self.post(url, json=data)
        response.raise_for_status()
        return response.json()
