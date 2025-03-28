import os
from datetime import datetime

from dotenv import load_dotenv
from tqdm import tqdm

from openowl.db import DB
from openowl.github_api import GithubAPI
from openowl.logger_config import setup_logger
from openowl.repository import Repository

load_dotenv()

logger = setup_logger(__name__)


# Class to get github data for a given repository
class GithubWorker:
    def __init__(self, url, version=None, token=None):
        self.api = GithubAPI(token=os.environ.get("GITHUB_ACCESS_TOKEN"))
        self.db = DB(os.environ.get("PATH_DB"))
        self.repository = Repository(url, version)
        self.repository_id = self.db.upsert_repository(self.repository)

    def process_issues(self, state="all", since=None, update=True):
        """Process and sync repository issues with the database.

        Fetches issues from GitHub API and upserts them into the database. If update=True,
        only fetches issues updated since the last sync, overwriting any provided since parameter.

        Args:
            token (str, optional): GitHub API token. Defaults to None.
            state (str, optional): Issue state to fetch ('open', 'closed', 'all'). Defaults to 'all'.
            since (str, optional): Only fetch issues updated after this timestamp (ISO 8601).
                Ignored if update=True. Defaults to None.
            update (bool, optional): If True, only fetch issues since last update,
                overriding since parameter. Defaults to True.

        Returns:
            None
        """

        if update:
            since = self.db.query_lastest_update_issues(self.repository.url)

        # Process issues
        issues = self.api.get_issues(
            self.repository.owner,
            self.repository.name,
            state=state,
            since=since,
        )
        self.db.upsert_issues(issues, self.repository_id)
        logger.info(
            f"Upserted {len(issues)} issues for repository {self.repository.url}"
        )

    def process_comments(
        self,
        since=None,
        update=True,
        state="all",
        max_issues=None,
        recent_first=True,
        min_comments=1,
        updated_after=None,
    ):
        """Process and sync comments for repository issues that are already in the database.

        Args:
            since (str, optional): Only fetch comments updated after this timestamp (ISO 8601).
                Ignored if update=True. Defaults to None.
            update (bool, optional): If True, only fetch comments since last update.
                Defaults to True.
            state (str, optional): Filter issues by state ('open', 'closed', 'all').
                Defaults to 'all'.
            max_issues (int, optional): Maximum number of issues to process.
                If None, processes all issues. Defaults to None.
            recent_first (bool, optional): If True, process most recently updated issues first.
                Defaults to True.
            min_comments (int, optional): Only process issues with at least this many comments.
                Defaults to 1.
            updated_after (str, optional): Only process issues updated after this timestamp.
                Defaults to None.

        Returns:
            int: Total number of comments processed
        """
        # Get the since parameter for comments if updating
        comments_since = None
        if update:
            comments_since = self.db.query_latest_update_comments(self.repository.url)
        else:
            comments_since = since

        # Determine the order by clause
        order_by = "i.updated_at DESC" if recent_first else "i.updated_at ASC"

        # Query issues from the database
        issues = self.db.query_issues_by_update_time(
            self.repository.url,
            state=state,
            after=updated_after,
            limit=max_issues,
            order_by=order_by,
        )

        # Filter issues by comment count if specified
        if min_comments > 0:
            issues = [
                issue for issue in issues if issue.get("comments", 0) >= min_comments
            ]

        logger.info(
            f"Processing comments for {len(issues)} issues in repository {self.repository.url}"
        )

        # Process comments for each issue
        total_comments = 0
        issues_with_comments = 0

        # Use tqdm with a more descriptive format
        with tqdm(
            total=len(issues), desc=f"Issues updated (0/{len(issues)})", unit="issue"
        ) as pbar:
            for i, issue in enumerate(issues):
                issue_number = issue["number"]

                # Get comments for this issue
                comments = self.api.get_comments(
                    self.repository.owner,
                    self.repository.name,
                    issue_number,
                )

                # Filter comments by since date if specified
                if comments_since and comments:
                    # Convert comments_since to datetime for comparison if it's a string
                    if isinstance(comments_since, str):
                        comments_since = datetime.fromisoformat(
                            comments_since.replace("Z", "+00:00")
                        )

                    # Filter comments based on updated_at
                    filtered_comments = []
                    for comment in comments:
                        comment_updated = datetime.fromisoformat(
                            comment["updated_at"].replace("Z", "+00:00")
                        )
                        if comment_updated > comments_since:
                            filtered_comments.append(comment)
                    comments = filtered_comments

                # Upsert comments to database
                if comments:
                    self.db.upsert_comments(comments, self.repository_id)
                    total_comments += len(comments)
                    issues_with_comments += 1
                    logger.debug(
                        f"Processed {len(comments)} comments for issue #{issue_number}"
                    )

                # Update the progress bar with current status
                pbar.set_description(
                    f"Issues updated ({issues_with_comments}/{len(issues)}) - Comments: {total_comments}"
                )
                pbar.update(1)

        logger.info(
            f"Processed a total of {total_comments} comments for {issues_with_comments}/{len(issues)} issues"
        )
        return total_comments
