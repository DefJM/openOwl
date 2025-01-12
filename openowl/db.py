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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                name TEXT,
                email TEXT,
                UNIQUE(username)
            )
        """
        )

        # Issues table
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number INTEGER NOT NULL,
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
                author_id INTEGER NOT NULL,
                
                -- User fields
                user_login TEXT,
                user_id INTEGER,
                user_node_id TEXT,
                user_type TEXT,
                user_site_admin BOOLEAN,
                
                -- Milestone fields
                milestone_id INTEGER,
                milestone_number INTEGER,
                milestone_title TEXT,
                milestone_state TEXT,
                milestone_due_on TIMESTAMP,
                
                FOREIGN KEY (repository_id) REFERENCES repositories (id),
                FOREIGN KEY (author_id) REFERENCES users (id),
                UNIQUE(number, repository_id)
            )
        """
        )

        # Comments table
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                body TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP,
                parent_id INTEGER NOT NULL,
                parent_type TEXT NOT NULL,  -- 'issue' only
                author_id INTEGER NOT NULL,
                FOREIGN KEY (author_id) REFERENCES users (id)
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

    def upsert_issues(self, issues, repository_id=None):
        """Upsert issues into the database from GitHub API response.

        Args:
            issues (list): List of issue dictionaries from GitHub API response
            repository_id (int, optional): Repository ID to associate issues with.
                         If not provided, uses the last upserted repository ID.

        Raises:
            ValueError: If no repository_id is provided or set
        """
        # Use provided repository_id or fall back to stored one
        repository_id = repository_id or self.repository_id
        if repository_id is None:
            raise ValueError("No repository_id provided or set via upsert_repository")

        user_sql = """
            INSERT INTO users (username)
            VALUES (?)
            ON CONFLICT(username) 
            DO UPDATE SET username=excluded.username
            RETURNING id
        """

        # Then upsert the issues
        issue_sql = """
            INSERT INTO issues (
                number, title, body, state, created_at, updated_at,
                repository_id, author_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(number, repository_id) DO UPDATE SET
                title = excluded.title,
                body = excluded.body,
                state = excluded.state,
                updated_at = excluded.updated_at,
                author_id = excluded.author_id
            RETURNING id
        """

        issue_ids = []
        for issue in issues:
            # First try to insert/update user and get id
            try:
                self.cursor.execute(user_sql, (issue["user"]["login"],))
                user_id = self.cursor.fetchone()[0]
            except sqlite3.Error:
                # Fallback to select if RETURNING isn't supported
                self.cursor.execute(get_user_sql, (issue["user"]["login"],))
                user_id = self.cursor.fetchone()[0]

            # Then upsert the issue
            self.cursor.execute(
                issue_sql,
                (
                    issue["number"],
                    issue["title"],
                    issue["body"],
                    issue["state"],
                    issue["created_at"],
                    issue["updated_at"],
                    repository_id,
                    user_id,
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

    def upsert_comments(self, comments):
        """Upsert comments into the database"""
        pass

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
            JOIN users u ON i.author_id = u.id
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
            SELECT MAX(updated_at) as latest_update
            FROM issues i
            JOIN repositories r ON i.repository_id = r.id
            WHERE r.url = ?
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
