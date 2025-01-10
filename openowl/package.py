from urllib.parse import urlparse

from openowl.logger_config import setup_logger

logger = setup_logger(__name__)


class Package:
    """Class to represent a package, collecting all relevant info from
    relevant sources and other classes
    """

    def __init__(self, url, version=None):
        self.url = url
        self.version = version
        self.platform = self._identify_package_platform()
        self.owner, self.name = self._extract_owner_and_name()

    def _identify_package_platform(self):
        """Identify the platform of the package, e.g. Github or Gitlab

        args:
            url (str): The URL of the package, e.g. https://github.com/bndr/pipreqs, or https://gitlab.com/bndr/pipreqs

        returns:
            str: The platform of the package, e.g. "github" or "gitlab"

        raises:
            ValueError: If URL does not contain a supported platform
        """
        parsed = urlparse(self.url)
        if parsed.netloc in ["github.com", "www.github.com"]:
            return "github"
        elif parsed.netloc in ["gitlab.com", "www.gitlab.com"]:
            return "gitlab"

        msg = f"URL must contain a supported platform (github.com or gitlab.com). Got: {url}"
        logger.error(msg)
        raise ValueError(msg)

    def _extract_owner_and_name(self):
        """Extract owner and repo name from GitHub or GitLab URL.
        By always taking the first two parts after github.com/gitlab.com,
        it handles cases like:
        /owner/repo
        /owner/repo/tree/main/docs
        /owner/repo/blob/master/README.md
        etc.

        Args:
            url (str): Repository URL - can include additional paths
                like branches, folders, etc.

        Returns:
            tuple: (owner, repo_name)

        Raises:
            ValueError: If URL is not a valid GitHub or GitLab repository URL
        """
        try:
            parsed = urlparse(self.url)
            if parsed.netloc not in ["github.com", "www.github.com", "gitlab.com", "www.gitlab.com"]:
                raise ValueError("Not a GitHub or Gitlab URL")
            # Remove trailing slashes and split path
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) < 2:
                raise ValueError("URL does not contain owner/repo format")
            return path_parts[0], path_parts[1]
        except Exception as e:
            raise ValueError(f"Invalid GitHub URL: {str(e)}")
