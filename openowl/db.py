import sqlite3
from typing import Optional

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
        self.conn = sqlite3.connect(path)
        self.cursor = self.conn.cursor()
        self._create_tables()
        self.repository_id = None  # Add this line to track current repository
        
    def _create_tables(self):
        """Create core tables if they don't exist"""
        # Repositories table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL,
                name TEXT NOT NULL,
                platform TEXT NOT NULL,
                created_at TIMESTAMP,
                UNIQUE(owner, name, platform)
            )
        ''')
        
        # Users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                name TEXT,
                email TEXT,
                UNIQUE(username)
            )
        ''')
        
        # Issues table
        self.cursor.execute('''
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
        ''')
        
        # Comments table
        self.cursor.execute('''
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
        ''')
        
        self.conn.commit()

    def upsert_repository(self, repository):
        """Upsert repository info into database.
        
        Args:
            repository (Repository): Repository object containing owner, name, and platform
            
        Returns:
            int: ID of the inserted/updated repository row
        """
        sql = '''
            INSERT INTO repositories (owner, name, platform)
            VALUES (?, ?, ?)
            ON CONFLICT(owner, name, platform) 
            DO UPDATE SET 
                owner=excluded.owner,
                name=excluded.name,
                platform=excluded.platform
            RETURNING id
        '''
        
        self.cursor.execute(sql, (
            repository.owner,
            repository.name, 
            repository.platform
        ))
        
        result = self.cursor.fetchone()[0]  # Fetch the result first
        self.conn.commit()                  # Then commit
        self.repository_id = result         # Finally store the ID
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
            
        user_sql = '''
            INSERT INTO users (username)
            VALUES (?)
            ON CONFLICT(username) 
            DO UPDATE SET username=excluded.username
            RETURNING id
        '''
        
        # Then upsert the issues
        issue_sql = '''
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
        '''
        
        issue_ids = []
        for issue in issues:
            # First try to insert/update user and get id
            try:
                self.cursor.execute(user_sql, (issue['user']['login'],))
                user_id = self.cursor.fetchone()[0]
            except sqlite3.Error:
                # Fallback to select if RETURNING isn't supported
                self.cursor.execute(get_user_sql, (issue['user']['login'],))
                user_id = self.cursor.fetchone()[0]
            
            # Then upsert the issue
            self.cursor.execute(issue_sql, (
                issue['number'],
                issue['title'],
                issue['body'],
                issue['state'],
                issue['created_at'],
                issue['updated_at'],
                repository_id,
                user_id
            ))
            issue_ids.append(self.cursor.fetchone()[0])
            
        self.conn.commit()
        return issue_ids

    def upsert_comments(self, comments):
        """Upsert comments into the database"""
        pass

    def upsert_issue_dependency(self, issue_id, dependency_id):
        """Upsert issue dependency into the database"""
        pass
