import requests
from urllib.parse import urljoin 


class DepsDevClient(requests.Session):
    def __init__(self) -> None:
        super().__init__()
        self.baseurl = "https://api.deps.dev"
        self.headers.update({"Content-Type": "application/json"})

    def request(self, method, url, *args, **kwargs):
        return super().request(method, urljoin(self.baseurl, url), *args, **kwargs)