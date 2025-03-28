import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from openowl.logger_config import setup_logger

logger = setup_logger(__name__)


class DB:
    """Class to initialize and interact with SQLite DB"""

    def __init__(self, path: str):
        """Initialize SQLite database with core tables.

        This class provides an interface to interact with a SQLite database,
        creating core tables for storing repository, user, issue and
        comment data if they don't already exist.

        Created tables:
            - repositories: Stores repository metadata
            - users: Stores user information
            - issues: Stores issue tracking data
            - comments: Stores issue comments

        Args:
            path (str): Path to SQLite database file location.

        Attributes:
            conn: SQLite database connection object
            cursor: SQLite cursor object for executing queries
        """
        # Create the db directory if it doesn't exist
        if not Path(path).parent.exists():
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory {Path(path).parent}")
        self.conn = sqlite3.connect(Path(path))
        self.cursor = self.conn.cursor()
        self._create_tables()
        self.repository_id = None  # Add this line to track current repository

    def _create_tables(self):
        """Create core tables if they don't exist"""
        # Repositories table
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL,
                name TEXT NOT NULL,
                platform TEXT NOT NULL,
                url TEXT NOT NULL,
                created_at TIMESTAMP,
                latest_update_issues TIMESTAMP,
                UNIQUE(owner, name, platform)
            )
        """
        )

        # Users table
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER NOT NULL PRIMARY KEY,  -- This will now be GitHub's user ID
                username TEXT NOT NULL,
                name TEXT,
                email TEXT,
                node_id TEXT,
                type TEXT,
                site_admin BOOLEAN,
                UNIQUE(username),
                UNIQUE(id)  -- GitHub's user ID is unique
            )
        """
        )

        # Issues table
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number INTEGER NOT NULL,
                html_url TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT,
                state TEXT,
                locked BOOLEAN,
                active_lock_reason TEXT,
                comments INTEGER,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP,
                closed_at TIMESTAMP,
                author_association TEXT,
                state_reason TEXT,
                repository_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,  -- Changed from author_id
                
                FOREIGN KEY (repository_id) REFERENCES repositories (id),
                FOREIGN KEY (user_id) REFERENCES users (id),  -- Changed from author_id
                UNIQUE(number, repository_id)
            )
        """
        )

        # Comments table - updated schema
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY, 
                node_id TEXT,
                url TEXT,
                html_url TEXT,
                body TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP,
                issue_id INTEGER NOT NULL, 
                author_association TEXT,
                user_id INTEGER NOT NULL,
                repository_id INTEGER NOT NULL,
                FOREIGN KEY (issue_id) REFERENCES issues (id),
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (repository_id) REFERENCES repositories (id),
                UNIQUE(id)
            )
        """
        )

        self.conn.commit()

    def upsert_repository(self, repository):
        """Upsert repository info into database.

        Args:
            repository (Repository): Repository object containing owner, name, platform and url

        Returns:
            int: ID of the inserted/updated repository row
        """
        sql = """
            INSERT INTO repositories (owner, name, platform, url)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(owner, name, platform) 
            DO UPDATE SET 
                owner=excluded.owner,
                name=excluded.name,
                platform=excluded.platform,
                url=excluded.url
            RETURNING id
        """

        self.cursor.execute(
            sql,
            (repository.owner, repository.name, repository.platform, repository.url),
        )

        result = self.cursor.fetchone()[0]
        self.conn.commit()
        self.repository_id = result
        return self.repository_id

    def upsert_issues(self, issues, repository_id):
        """Upsert issues into the database from GitHub API response.

        Args:
            issues (list): List of issue dictionaries from GitHub API response
            repository_id (int, optional): Repository ID to associate issues with.
                         If not provided, uses the last upserted repository ID.
        """
        repository_id = repository_id or self.repository_id
        if repository_id is None:
            raise ValueError("No repository_id provided or set via upsert_repository")

        user_sql = """
            INSERT INTO users (id, username, node_id, type, site_admin)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) 
            DO UPDATE SET 
                username=excluded.username,
                node_id=excluded.node_id,
                type=excluded.type,
                site_admin=excluded.site_admin
        """

        issue_sql = """
            INSERT INTO issues (
                number, html_url, title, body, state, locked, active_lock_reason,
                comments, created_at, updated_at, closed_at,
                author_association, state_reason, repository_id, user_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(number, repository_id) DO UPDATE SET
                html_url = excluded.html_url,
                title = excluded.title,
                body = excluded.body,
                state = excluded.state,
                locked = excluded.locked,
                active_lock_reason = excluded.active_lock_reason,
                comments = excluded.comments,
                updated_at = excluded.updated_at,
                closed_at = excluded.closed_at,
                author_association = excluded.author_association,
                state_reason = excluded.state_reason,
                user_id = excluded.user_id
            RETURNING id
        """

        issue_ids = []
        for issue in issues:
            # First upsert the user
            self.cursor.execute(
                user_sql,
                (
                    issue["user"]["id"],
                    issue["user"]["login"],
                    issue["user"].get("node_id"),
                    issue["user"].get("type"),
                    issue["user"].get("site_admin", False),
                ),
            )

            # Then upsert the issue
            self.cursor.execute(
                issue_sql,
                (
                    issue["number"],
                    issue["html_url"],
                    issue["title"],
                    issue.get("body"),
                    issue["state"],
                    issue.get("locked", False),
                    issue.get("active_lock_reason"),
                    issue.get("comments", 0),
                    issue["created_at"],
                    issue["updated_at"],
                    issue.get("closed_at"),
                    issue.get("author_association"),
                    issue.get("state_reason"),
                    repository_id,
                    issue["user"]["id"],  # Using GitHub's user ID as the foreign key
                ),
            )
            issue_ids.append(self.cursor.fetchone()[0])

        self.conn.commit()
        self._latest_update_issues(repository_id)
        return issue_ids

    def _latest_update_issues(self, repository_id):
        """Update the repository's last issue update timestamp based on most recent issue update.

        Args:
            repository_id (int): ID of the repository to update
        """
        self.cursor.execute(
            """
            UPDATE repositories 
            SET latest_update_issues = (
                SELECT MAX(updated_at)
                FROM issues
                WHERE repository_id = ?
            )
            WHERE id = ?
            RETURNING latest_update_issues
        """,
            (repository_id, repository_id),
        )

        latest_update_issues = self.cursor.fetchone()[0]
        self.conn.commit()
        logger.info(
            f"Updated field latest_update_issues for repository {repository_id} to {latest_update_issues}"
        )

    def upsert_users_from_issues(self):
        """TODO: Upsert users from issues into the database"""
        pass

    def upsert_comments(self, comments, repository_id=None):
        """Upsert comments into the database from GitHub API response.

        Args:
            comments (list): List of comment dictionaries from GitHub API response
            repository_id (int, optional): Repository ID to associate comments with.
                         If not provided, uses the last upserted repository ID.

        Returns:
            list: List of comment IDs
        """
        repository_id = repository_id or self.repository_id
        if repository_id is None:
            raise ValueError("No repository_id provided or set via upsert_repository")

        user_sql = """
            INSERT INTO users (id, username, node_id, type, site_admin)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) 
            DO UPDATE SET 
                username=excluded.username,
                node_id=excluded.node_id,
                type=excluded.type,
                site_admin=excluded.site_admin
        """

        comment_sql = """
            INSERT INTO comments (
                id, node_id, url, html_url, body, created_at, updated_at,
                issue_id, author_association, user_id, repository_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                node_id = excluded.node_id,
                url = excluded.url,
                html_url = excluded.html_url,
                body = excluded.body,
                updated_at = excluded.updated_at,
                author_association = excluded.author_association
            RETURNING id
        """

        comment_ids = []
        for comment in comments:
            # First upsert the user
            self.cursor.execute(
                user_sql,
                (
                    comment["user"]["id"],
                    comment["user"]["login"],
                    comment["user"].get("node_id"),
                    comment["user"].get("type"),
                    comment["user"].get("site_admin", False),
                ),
            )

            # Extract issue_id from the issue_url
            issue_url_parts = comment["issue_url"].split("/")
            issue_number = int(issue_url_parts[-1])

            # Get the corresponding issue_id from our database
            self.cursor.execute(
                "SELECT id FROM issues WHERE number = ? AND repository_id = ?",
                (issue_number, repository_id),
            )
            result = self.cursor.fetchone()
            if not result:
                logger.warning(
                    f"Issue {issue_number} not found in database, skipping comment"
                )
                continue

            issue_id = result[0]

            # Then upsert the comment
            self.cursor.execute(
                comment_sql,
                (
                    comment["id"],
                    comment.get("node_id"),
                    comment.get("url"),
                    comment.get("html_url"),
                    comment["body"],
                    comment["created_at"],
                    comment["updated_at"],
                    issue_id,
                    comment.get("author_association"),
                    comment["user"]["id"],
                    repository_id,
                ),
            )
            comment_ids.append(self.cursor.fetchone()[0])

        self.conn.commit()
        logger.info(
            f"Upserted {len(comment_ids)} comments for repository_id {repository_id}"
        )
        return comment_ids

    def query_issues(self, repository_url_list, state="all", since=None):
        """Query issues from the database for given repository URLs with optional filters.

        Args:
            repository_url_list (list): List of repository URLs to query issues for
            state (str, optional): Filter issues by state ('open', 'closed', or 'all').
                                 Defaults to 'all'.
            since (str, optional): ISO format timestamp to filter issues created after this time.
                                 Defaults to None.

        Returns:
            list: List of dictionaries containing issue data including repository and author info
        """
        # Build base query using the url column directly
        query = """
            SELECT i.*, r.url as repository_url, u.username as author_username
            FROM issues i
            JOIN repositories r ON i.repository_id = r.id 
            JOIN users u ON i.user_id = u.id
            WHERE r.url IN ({})
        """.format(
            ",".join("?" * len(repository_url_list))
        )

        # Add filters
        params = list(repository_url_list)
        if state != "all":
            query += " AND i.state = ?"
            params.append(state)

        if since:
            query += " AND i.created_at >= ?"
            params.append(since)

        # Execute query
        self.cursor.execute(query, params)

        # Get results
        columns = [desc[0] for desc in self.cursor.description]
        results = [dict(zip(columns, row)) for row in self.cursor.fetchall()]

        # Log issue counts per repository
        repo_counts = {
            url: 0 for url in repository_url_list
        }  # Initialize all repos to 0
        for issue in results:
            repo_url = issue["repository_url"]
            repo_counts[repo_url] += 1

        for repo_url, count in repo_counts.items():
            logger.info(
                f"query_issues: Found {count} issues for repository: {repo_url}"
            )
        return results

    def query_lastest_update_issues(self, repository_url: str) -> Optional[datetime]:
        """Query the latest update timestamp for issues in the given repository.

        Args:
            repository_url (str): URL of the repository to query

        Returns:
            Optional[datetime]: Timestamp of the most recently updated issue for the repository,
                              or None if no issues exist
        """
        query = """
            SELECT latest_update_issues
            FROM repositories
            WHERE url = ?
        """
        self.cursor.execute(query, (repository_url,))
        result = self.cursor.fetchone()

        if result and result[0]:
            latest_update = datetime.fromisoformat(result[0].replace("Z", "+00:00"))
            logger.info(
                f"Latest issue update for repository {repository_url}: {latest_update}"
            )
            return latest_update

        logger.info(f"No issues found for repository {repository_url}")
        return None

    def query_repository_id(self, repository_url: str) -> Optional[int]:
        """Query the repository ID for a given repository URL.
        If not found, upsert repository and return id.

        Args:
            repository_url (str): URL of the repository to query

        Returns:
            Optional[int]: Repository ID if found, None if not found
        """
        # Query existing repository
        query = """
            SELECT id 
            FROM repositories
            WHERE url = ?
        """
        self.cursor.execute(query, (repository_url,))
        result = self.cursor.fetchone()

        if result:
            logger.debug(f"Found repository ID {result[0]} for {repository_url}")
            return result[0]

        logger.debug(f"No repository found for {repository_url}")
        return None

    def query_user_from_issue(self, issue_id):
        """Query user from an issue"""
        query = """
            SELECT DISTINCT u.id, u.username
            FROM users u
            JOIN issues i ON u.id = i.user_id
            WHERE i.id = ?
        """
        self.cursor.execute(query, (issue_id,))
        result = self.cursor.fetchone()
        return result

    def query_latest_update_comments(self, repository_url: str) -> Optional[datetime]:
        """Query the latest update timestamp for comments in the given repository.

        Args:
            repository_url (str): URL of the repository to query

        Returns:
            Optional[datetime]: Timestamp of the most recently updated comment for the repository,
                              or None if no comments exist
        """
        query = """
            SELECT MAX(updated_at) as latest_update
            FROM comments c
            JOIN repositories r ON c.repository_id = r.id
            WHERE r.url = ?
        """
        self.cursor.execute(query, (repository_url,))
        result = self.cursor.fetchone()

        if result and result[0]:
            latest_update = datetime.fromisoformat(result[0].replace("Z", "+00:00"))
            logger.info(
                f"Latest comment update for repository {repository_url}: {latest_update}"
            )
            return latest_update

        logger.info(f"No comments found for repository {repository_url}")
        return None

    def query_issues_by_update_time(
        self,
        repository_url,
        state="all",
        after=None,
        limit=None,
        order_by="updated_at DESC",
    ):
        """Query issues from the database for a repository, filtered by update time.

        Args:
            repository_url (str): Repository URL to query issues for
            state (str, optional): Filter issues by state ('open', 'closed', 'all').
                Defaults to 'all'.
            after (str, optional): ISO format timestamp to filter issues updated after this time.
                Defaults to None.
            limit (int, optional): Maximum number of issues to return.
                Defaults to None (all issues).
            order_by (str, optional): SQL ORDER BY clause.
                Defaults to "updated_at DESC" (most recently updated first).

        Returns:
            list: List of dictionaries containing issue data
        """
        # Build base query
        query = """
            SELECT i.*, r.url as repository_url, u.username as author_username
            FROM issues i
            JOIN repositories r ON i.repository_id = r.id 
            JOIN users u ON i.user_id = u.id
            WHERE r.url = ?
        """

        # Add filters
        params = [repository_url]
        if state != "all":
            query += " AND i.state = ?"
            params.append(state)

        if after:
            query += " AND i.updated_at >= ?"
            params.append(after)

        # Add order by
        if order_by:
            query += f" ORDER BY {order_by}"

        # Add limit
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        # Execute query
        self.cursor.execute(query, params)

        # Get results
        columns = [desc[0] for desc in self.cursor.description]
        results = [dict(zip(columns, row)) for row in self.cursor.fetchall()]

        logger.info(
            f"query_issues_by_update_time: Found {len(results)} issues for repository: {repository_url}"
        )
        return results

    def get_comments_for_issue(self, issue_id):
        """Get all comments for a given issue."""
        query = """
            SELECT c.*
            FROM comments c
            JOIN issues i ON c.issue_id = i.id
            WHERE i.id = ?
        """
        self.cursor.execute(query, (issue_id,))
        return self.cursor.fetchall()
