import hashlib
from typing import Dict, Any

from tinydb import Query, TinyDB


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

