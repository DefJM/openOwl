import hashlib
from typing import Dict, Any

from tinydb import Query


def upsert_dependency(dependency, dependencies_table):
    """Upsert dependency to database."""
    dep_id = generate_dependency_hash(dependency)
    dependency["id"] = dep_id
    dependencies_table.upsert(dependency, Query().id == dep_id)
    return dep_id


def generate_dependency_hash(dependency):
    """Create unique identifier string (SHA256 hash) for dependency."""
    unique_string = f"{dependency['name']}:{dependency['version']}"
    return hashlib.sha256(unique_string.encode()).hexdigest()


def upsert_issue(issue, issues_table):
    """Upsert issue to database."""
    issues_table.upsert(issue, Query().id == issue["id"])


def link_issue_to_dependency(issue_id, dependency_id, issue_dependency_table):
    """Link issue to dependency in database."""
    issue_dependency_table.upsert(
        {"issue_id": issue_id, "dependency_id": dependency_id},
        (Query().issue_id == issue_id) & (Query().dependency_id == dependency_id),
    )


def find_issue_by_id(issue_id, issues_table):
    """Find issue by id in database."""
    return issues_table.get(Query().id == issue_id)


def find_issues_for_dependency(dependency_id, issue_dependency_table, issues_table):
    """Find issues for dependency in database."""
    IssueDepend = Query()
    links = issue_dependency_table.search(IssueDepend.dependency_id == dependency_id)
    return [find_issue_by_id(link["issue_id"], issues_table) for link in links]


def update_issue_details(issue_id, new_details, issues_table):
    """Update issue details in database."""
    return issues_table.update(new_details, Query().id == issue_id)
