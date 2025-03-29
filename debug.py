import json
import os
import sqlite3
from datetime import datetime

from dotenv import load_dotenv

from openowl.db import DB
from openowl.github_api import GithubAPI
from openowl.github_worker import GithubWorker
from openowl.analysis_worker import AnalysisWorker

load_dotenv()


############# Test script for debugging workers and db functions ################


# github_url="https://github.com/pydantic/pydantic"
# github_url="https://github.com/pandas-dev/pandas"
# github_url = "https://github.com/psf/requests"
github_url="https://github.com/formbricks/formbricks"

package_version = None
token = os.environ.get("GITHUB_ACCESS_TOKEN")
db = DB(os.environ.get("PATH_DB"))
model = "claude-3-5-haiku-20241022"

worker = GithubWorker(db, github_url, package_version, token)

# worker.process_issues(update=False, state="open", since=None)
# worker.process_comments(update=False, since=None)

# worker.process_pull_requests(update=False, state="open", since=None)
# worker.process_pull_request_comments(update=False, since=None)

# worker.process_issues(update=True)
# worker.process_comments(update=True)

# worker.process_pull_requests(update=True)
# worker.process_pull_request_comments(update=True)

# Analyze toxicity of comments
analysis_worker = AnalysisWorker(worker.db, model)
analysis_worker.update_toxicity_scores_llm(repository_urls=github_url, start_date="2025-03-01", end_date=None)






################ couple of queries to the database ################


def show_existing_tables():
    """
    Show all existing tables in the database and their row counts.
    """
    conn = sqlite3.connect(os.environ.get("PATH_DB"))
    cursor = conn.cursor()

    # Get all tables
    cursor.execute(
        """
        SELECT name 
        FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%';
    """
    )

    tables = cursor.fetchall()

    print("Existing tables and their row counts:")
    print("-" * 40)

    for (table_name,) in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"{table_name}: {count} rows")

    conn.close()


def show_table_contents(table_name=None):
    """
    Show all records from a specified table (or all tables) with all their fields.

    Args:
        table_name (str, optional): Specific table to show. If None, shows all tables.
    """

    conn = sqlite3.connect(os.environ.get("PATH_DB"))
    cursor = conn.cursor()

    def get_table_data(table):
        # Get all columns for the table
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]

        # Get all records
        cursor.execute(f"SELECT * FROM {table}")
        records = cursor.fetchall()

        # Convert to list of dictionaries
        data = []
        for record in records:
            record_dict = dict(zip(columns, record))
            # Convert datetime strings to ISO format
            for key, value in record_dict.items():
                if isinstance(value, str) and ("_at" in key or "_on" in key):
                    try:
                        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                        record_dict[key] = dt.isoformat()
                    except ValueError:
                        pass
            data.append(record_dict)

        return {"table_name": table, "total_records": len(records), "records": data}

    # Get all tables if no specific table is specified
    if table_name is None:
        cursor.execute(
            """
            SELECT name 
            FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """
        )
        tables = [row[0] for row in cursor.fetchall()]
        result = {table: get_table_data(table) for table in tables}
    else:
        result = get_table_data(table_name)

    print(json.dumps(result, indent=2))
    conn.close()


def show_comments_for_issue(issue_id):
    """
    Show all comments for a given issue.
    """

    db = DB(os.environ.get("PATH_DB"))
    comments = db.query_comments_for_issue(issue_id)
    print(comments)


# show_comments_for_issue(1)


# show_table_contents()

# show_table_contents("issues")

# show_table_contents("repositories")

# show_table_contents("users")

# show_table_contents("comments")

# show_existing_tables()
