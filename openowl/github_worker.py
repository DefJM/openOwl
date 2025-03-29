import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from tqdm import tqdm

from openowl.github_api import GithubAPI
from openowl.logger_config import setup_logger
from openowl.repository import Repository

load_dotenv()

logger = setup_logger(__name__)


# Class to get github data for a given repository
class GithubWorker:
    def __init__(self, db, url, version=None, token=None):
        # Accept db as parameter instead of creating it internally
        self.api = GithubAPI(token=token or os.environ.get("GITHUB_ACCESS_TOKEN"))
        self.db = db
        self.repository = Repository(url, version)
        self.repository_id = self.db.upsert_repository(self.repository)

    def process_issues(self, state="all", since=None, update=True, buffer_hours=24):
        """Process and sync repository issues with the database.

        Fetches issues from GitHub API and upserts them into the database. If update=True,
        only fetches issues updated since the last sync, with a safety buffer to avoid
        missing issues if previous runs failed.

        Args:
            state (str, optional): Issue state to fetch ('open', 'closed', 'all'). Defaults to 'all'.
            since (str, optional): Only fetch issues updated after this timestamp (ISO 8601).
                Ignored if update=True. Defaults to None.
            update (bool, optional): If True, only fetch issues since last update,
                overriding since parameter. Defaults to True.
            buffer_hours (int, optional): Safety buffer in hours to subtract from the since timestamp.
                Defaults to 24 hours.

        Returns:
            None
        """
        # Apply buffer to since timestamp if updating
        if update:
            since = self.db.query_latest_update_issues(self.repository.url)
            if since:
                # Add a safety buffer by subtracting time from the since timestamp
                if isinstance(since, str):
                    since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                else:
                    since_dt = since
                buffer_time = timedelta(hours=buffer_hours)
                since_with_buffer = (since_dt - buffer_time).isoformat()
                since = since_with_buffer
                logger.info(f"Using timestamp {since} (original with {buffer_hours}h buffer)")

        # Process issues
        issues = self.api.get_issues(
            self.repository.owner,
            self.repository.name,
            state=state,
            since=since,
        )
        
        logger.info(f"Fetched {len(issues)} issues for repository {self.repository.url}")
        
        # Only proceed with updates if we have issues
        if not issues:
            logger.info("No issues to update")
            return
        
        # Get the most recent timestamp from fetched issues
        most_recent = max(issues, key=lambda x: x["updated_at"])
        most_recent_timestamp = most_recent["updated_at"]
        
        # Transaction for upsert and timestamp update
        try:
            # First upsert the issues
            self.db.upsert_issues(issues, self.repository_id)
            logger.info(f"Successfully upserted {len(issues)} issues")
            
            # Only after successful upsert, update the timestamp
            timestamp_updated = self.db._update_latest_issues_timestamp(
                self.repository_id, most_recent_timestamp
            )
            if timestamp_updated:
                logger.info(f"Successfully updated timestamp to {most_recent_timestamp}")
            else:
                logger.warning("Failed to update timestamp, next run may reprocess some issues")
            
        except Exception as e:
            logger.error(f"Failed to update issues: {e}")
            # Don't update the timestamp
            raise

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

        # If we have a comments_since value, use it to filter issues
        # that may have new comments
        if comments_since:
            # Override updated_after with comments_since if it's more recent
            if updated_after is None or (isinstance(updated_after, str) and 
                                         isinstance(comments_since, datetime) and
                                         datetime.fromisoformat(updated_after.replace("Z", "+00:00")) < comments_since):
                updated_after = comments_since.isoformat() if isinstance(comments_since, datetime) else comments_since
                logger.info(f"Filtering issues updated after {updated_after} which may have new comments")

        # Determine the order by clause
        order_by = "i.updated_at DESC" if recent_first else "i.updated_at ASC"

        # Query issues from the database with smart filtering
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
        if len(issues) == 0:
            logger.info("No issues need comment updates. Skipping comment processing.")
            return 0

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
                else:
                    logger.debug(f"No new comments for issue #{issue_number}")

                # Update the progress bar with current status
                pbar.set_description(
                    f"Issues updated ({issues_with_comments}/{len(issues)}) - Comments: {total_comments}"
                )
                pbar.update(1)

        logger.info(
            f"Processed a total of {total_comments} comments for {issues_with_comments}/{len(issues)} issues"
        )
        return total_comments

    def process_pull_requests(self, state="all", since=None, update=True):
        """Process and sync repository pull requests with the database.

        Fetches pull requests from GitHub API and upserts them into the database. If update=True,
        only fetches pull requests updated since the last sync, overwriting any provided since parameter.

        Args:
            state (str, optional): Pull request state to fetch ('open', 'closed', 'all'). Defaults to 'all'.
            since (str, optional): Only fetch pull requests updated after this timestamp (ISO 8601).
                Ignored if update=True. Defaults to None.
            update (bool, optional): If True, only fetch pull requests since last update,
                overriding since parameter. Defaults to True.

        Returns:
            None
        """
        if update:
            since = self.db.query_latest_update_pull_requests(self.repository.url)
            if since:
                logger.info(f"Updating pull requests since {since}")
            else:
                logger.info("No previous pull requests found, fetching all")

        # Process pull requests
        pull_requests = self.api.get_pull_requests(
            self.repository.owner,
            self.repository.name,
            state=state,
            since=since,
        )
        self.db.upsert_pull_requests(pull_requests, self.repository_id)
        logger.info(
            f"Upserted {len(pull_requests)} pull requests for repository {self.repository.url}"
        )

    def process_pull_request_comments(
        self,
        since=None,
        update=True,
        state="all",
        max_pull_requests=None,
        recent_first=True,
        min_comments=0,
        updated_after=None,
    ):
        """Process and sync comments for repository pull requests that are already in the database.

        Args:
            since (str, optional): Only fetch comments updated after this timestamp (ISO 8601).
                Ignored if update=True. Defaults to None.
            update (bool, optional): If True, only fetch comments since last update.
                Defaults to True.
            state (str, optional): Filter pull requests by state ('open', 'closed', 'all').
                Defaults to 'all'.
            max_pull_requests (int, optional): Maximum number of pull requests to process.
                If None, processes all pull requests. Defaults to None.
            recent_first (bool, optional): If True, process most recently updated pull requests first.
                Defaults to True.
            min_comments (int, optional): Only process pull requests with at least this many comments.
                Defaults to 0 (process all PRs).
            updated_after (str, optional): Only process pull requests updated after this timestamp.
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
        
        # Filter PRs based on comments_since timestamp if specified
        if comments_since:
            # Override updated_after with comments_since if it's more recent
            if updated_after is None or (isinstance(updated_after, str) and 
                                         isinstance(comments_since, datetime) and
                                         datetime.fromisoformat(updated_after.replace("Z", "+00:00")) < comments_since):
                updated_after = comments_since.isoformat() if isinstance(comments_since, datetime) else comments_since
                logger.info(f"Filtering pull requests updated after {updated_after} which may have new comments")

        # Determine the order by clause
        order_by = "pr.updated_at DESC" if recent_first else "pr.updated_at ASC"

        # Query pull requests from the database with smart filtering
        pull_requests = self.db.query_pull_requests_by_update_time(
            self.repository.url,
            state=state,
            after=updated_after,
            limit=max_pull_requests,
            order_by=order_by,
        )
        
        logger.info(f"Found {len(pull_requests)} pull requests before filtering")
        
        # Add debug information about PR comment counts
        comment_counts = {}
        for pr in pull_requests:
            count = pr.get("comments", 0)
            comment_counts[count] = comment_counts.get(count, 0) + 1
        
        logger.info(f"PR comment count distribution: {comment_counts}")

        # Filter pull requests by comment count if specified
        if min_comments > 0:
            filtered_prs = [
                pr for pr in pull_requests if pr.get("comments", 0) >= min_comments
            ]
            logger.info(
                f"Filtered to {len(filtered_prs)} PRs with {min_comments}+ comments"
            )
            pull_requests = filtered_prs

        logger.info(
            f"Processing {len(pull_requests)} PR comments for {self.repository.url}"
        )
        
        if len(pull_requests) == 0:
            logger.info("No PRs need comment updates. Skipping.")
            return 0

        # Process comments for each pull request
        total_comments = 0
        prs_with_comments = 0

        # Use tqdm with a more descriptive format
        with tqdm(
            total=len(pull_requests),
            desc=f"PRs updated (0/{len(pull_requests)})",
            unit="PR",
        ) as pbar:
            for i, pr in enumerate(pull_requests):
                pr_number = pr["number"]

                # Get comments for this pull request
                comments = self.api.get_pull_request_comments(
                    self.repository.owner,
                    self.repository.name,
                    pr_number,
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
                    prs_with_comments += 1
                    logger.debug(
                        f"Processed {len(comments)} comments for pull request #{pr_number}"
                    )
                else:
                    logger.debug(f"No new comments for pull request #{pr_number}")

                # Update the progress bar with current status
                pbar.set_description(
                    f"PRs updated ({prs_with_comments}/{len(pull_requests)}) - Comments: {total_comments}"
                )
                pbar.update(1)

        logger.info(
            f"Processed a total of {total_comments} comments for {prs_with_comments}/{len(pull_requests)} pull requests"
        )
        return total_comments
