import pandas as pd
from detoxify import Detoxify
from tqdm import tqdm
from tinydb import Query

from openowl.gh_llm import get_toxicity_score_llm
from openowl.logger_config import setup_logger

logger = setup_logger(__name__)


def get_toxicity_scores_detoxify(issues_table):
    """
    Analyze toxicity of GitHub issue comments using Detoxify model.

    Args:
        issues_table: TinyDB table containing GitHub issues with comments.
            The table documents will be updated with sentiment scores for each comment.

    Returns:
        pandas.DataFrame: DataFrame containing comment data and toxicity scores.
    """
    detector = Detoxify("original")  # "original" or "multilingual"
    comments_data = []
    total_comments = sum(
        len(issue.get("comments_list", [])) for issue in issues_table.all()
    )
    with tqdm(total=total_comments, desc="Analyzing comment toxicity") as pbar:
        for issue in issues_table.all():
            issue_id = issue["id"]
            if "comments_list" in issue and len(issue["comments_list"]) > 0:
                for i, comment in enumerate(issue["comments_list"]):
                    toxicity_scores = detector.predict(comment["body"])
                    # Store sentiment scores in a separate dictionary
                    sentiment_data = {
                        "toxicity": float(toxicity_scores["toxicity"]),
                        "severe_toxicity": float(toxicity_scores["severe_toxicity"]),
                        "obscene": float(toxicity_scores["obscene"]),
                        "threat": float(toxicity_scores["threat"]),
                        "insult": float(toxicity_scores["insult"]),
                        "identity_attack": float(toxicity_scores["identity_attack"]),
                    }
                    # Update the comment in TinyDB with sentiment data
                    issue["comments_list"][i]["comment_sentiments"] = sentiment_data
                    # Create full entry for DataFrame (unchanged)
                    comment_entry = {
                        "datetime": comment["created_at"],
                        "issue_id": issue_id,
                        "comment_details": comment["body"],
                        "author_association": comment["author_association"],
                        "user": comment["user"]["login"],
                        **sentiment_data,  # Unpack sentiment scores
                    }
                    comments_data.append(comment_entry)
                    pbar.update(1)
                # Update the issue in the database with modified comments_list
                issues_table.update(
                    {"comments_list": issue["comments_list"]},
                    doc_ids=[issue.doc_id],
                )
    comments_df = pd.DataFrame(comments_data)
    comments_df = comments_df.sort_values("datetime")
    return comments_df


def update_toxicity_scores_llm(db, model, start_idx=None, end_idx=None, dependency=None):
    """
    Update TinyDB table with toxicity scores for GitHub issue comments using an LLM model.

    Args:
        db: TinyDB database instance
        model: Name of the LLM model to use for toxicity analysis (e.g. "claude-3-5-haiku-latest")
        start_idx: Starting index for processing comments (0-based). If None, starts from beginning.
        end_idx: Ending index for processing comments (exclusive). If None, processes until the end.
        dependency: Optional dictionary containing package info to filter issues. If None, processes all issues.
            Should contain keys: package_manager, owner, name, version

    Returns:
        TinyDB database instance with updated toxicity scores
    """
    if dependency:
        issues_list = filter_issues_by_dependency(db, dependency)
        issues_table = db.table("issues")
    else:
        issues_table = db.table("issues")
        issues_list = issues_table.all()

    # Get all comments with their timestamps
    all_comments = []
    for issue in issues_list:
        if "comments_list" in issue and len(issue["comments_list"]) > 0:
            for comment in issue["comments_list"]:
                # Parse the timestamp string to ensure proper sorting
                timestamp = pd.to_datetime(comment["created_at"])
                all_comments.append(
                    (issue["id"], timestamp, comment["created_at"])
                )  # Store both timestamp formats

    # Sort comments by timestamp (newest first)
    all_comments.sort(key=lambda x: x[1], reverse=True)
    logger.info(f"Sorted {len(all_comments)} comments by timestamp (newest first)")
    if all_comments:
        logger.info(f"Date range: {all_comments[-1][1]} to {all_comments[0][1]}")

    # Slice the comments based on start and end indices
    start_idx = start_idx if start_idx is not None else 0
    end_idx = end_idx if end_idx is not None else len(all_comments)
    all_comments = all_comments[start_idx:end_idx]

    # Create set of (id, original_timestamp) tuples for efficient lookup
    comments_to_process = {(id_, orig_ts) for id_, _, orig_ts in all_comments}

    logger.info(f"Processing comments from index {start_idx} to {end_idx}")
    logger.info(f"Total comments to process: {len(comments_to_process)}")

    total_comments = len(comments_to_process)
    processed = 0
    with tqdm(total=total_comments, desc="Analyzing comment toxicity") as pbar:
        for issue in issues_list:
            if "comments_list" in issue and len(issue["comments_list"]) > 0:
                modified = False
                for i, comment in enumerate(issue["comments_list"]):
                    # Only process if comment is in our set
                    if (issue["id"], comment["created_at"]) in comments_to_process:
                        try:
                            toxicity_data = get_toxicity_score_llm(
                                comment["body"], model
                            )
                            logger.info(toxicity_data)
                            issue["comments_list"][i][
                                "comment_sentiments_llm"
                            ] = toxicity_data
                            modified = True
                            processed += 1
                            pbar.update(1)
                        except Exception as e:
                            logger.error(f"Error processing comment: {e}")
                            continue

                # Only update the database if we modified any comments in this issue
                if modified:
                    try:
                        issues_table.update(
                            {"comments_list": issue["comments_list"]},
                            doc_ids=[issue.doc_id],
                        )
                    except Exception as e:
                        logger.error(f"Error updating database: {e}")
    return db 



def create_toxicity_dataframe(db, package_info):
    """
    Create a pandas DataFrame from issues table with toxicity analysis results.

    Args:
        db (TinyDB): TinyDB database instance containing GitHub issues from multiple dependencies
        dependency (dict, optional): Dictionary containing dependency information to filter issues.
            Should contain keys: package_manager, owner, name, version.
            If None, all issues will be processed.

    Returns:
        pandas.DataFrame: DataFrame containing comment data and sentiment scores
    """
    if package_info:
        issues_list = filter_issues_by_dependency(db, package_info)
    else:
        issues_table = db.table("issues")
        issues_list = issues_table.all()
    comments_data_llm = []
    for issue in issues_list:
        issue_id = issue["id"]
        issue_url = issue.get("html_url")  # Get the issue URL
        if "comments_list" in issue and len(issue["comments_list"]) > 0:
            for comment in issue["comments_list"]:
                # Create a base entry with None values for all fields
                comment_entry = {
                    "datetime": None,
                    "issue_id": issue_id,
                    "issue_url": issue_url,  # Add issue URL to each comment
                    "comment_details": None,
                    "author_association": None,
                    "user": None,
                    "reactions_plus1": None,
                    "reactions_minus1": None,
                    "reactions_laugh": None,
                    "reactions_hooray": None,
                    "reactions_confused": None,
                    "reactions_heart": None,
                    "reactions_rocket": None,
                    "reactions_eyes": None,
                    "toxicity_llm_score": None,
                    "toxicity_llm_rationale": None,
                }

                # Safely update fields that exist
                if "created_at" in comment:
                    comment_entry["datetime"] = comment["created_at"]
                if "body" in comment:
                    comment_entry["comment_details"] = comment["body"]
                if "author_association" in comment:
                    comment_entry["author_association"] = comment["author_association"]
                if "user" in comment and isinstance(comment["user"], dict):
                    comment_entry["user"] = comment["user"].get("login")

                # Safely get reaction data
                if "reactions" in comment and isinstance(comment["reactions"], dict):
                    reactions = comment["reactions"]
                    comment_entry.update(
                        {
                            "reactions_plus1": reactions.get("+1"),
                            "reactions_minus1": reactions.get("-1"),
                            "reactions_laugh": reactions.get("laugh"),
                            "reactions_hooray": reactions.get("hooray"),
                            "reactions_confused": reactions.get("confused"),
                            "reactions_heart": reactions.get("heart"),
                            "reactions_rocket": reactions.get("rocket"),
                            "reactions_eyes": reactions.get("eyes"),
                        }
                    )
                # Safely get sentiment data (detoxify)
                if "comment_sentiments" in comment:
                    toxicity_data = {
                        f"sentiment_dtxf_{k}": v 
                        for k, v in comment["comment_sentiments"].items()
                    }
                    comment_entry.update(toxicity_data)
                    
                # Safely get toxicity data
                if "comment_sentiments_llm" in comment:
                    toxicity_data = comment["comment_sentiments_llm"]
                    comment_entry.update(
                        {
                            "toxicity_llm_score": toxicity_data.get("toxicity_score"),
                            "toxicity_llm_rationale": toxicity_data.get(
                                "toxicity_rationale"
                            ),
                        }
                    )

                comments_data_llm.append(comment_entry)

    # Create DataFrame - missing values will automatically be NaN
    comments_df_llm = pd.DataFrame(comments_data_llm)

    # Convert toxicity score to numeric, handling any non-numeric values
    try:
        comments_df_llm["toxicity_llm_score"] = pd.to_numeric(
            comments_df_llm["toxicity_llm_score"], errors="coerce"
        )
    except (KeyError, AttributeError):
        # If LLM scores aren't available yet, just return the dataframe without them
        pass
    
    # Convert datetime to datetime object
    try:
        comments_df_llm["datetime"] = pd.to_datetime(comments_df_llm["datetime"])
        # Only sort if datetime column exists and has valid values
        if not comments_df_llm.empty:
            comments_df_llm = comments_df_llm.sort_values("datetime", na_position="last")
    except (KeyError, AttributeError):
        # If datetime isn't available, return unsorted dataframe
        pass

    return comments_df_llm



def filter_issues_by_dependency(db, dependency):
    """
    Filter issues table for a specific dependency using package info.
    
    Args:
        db: TinyDB database instance
        dependency: Dict containing package_manager, owner, name and version
    
    Returns:
        List of filtered issues
    """
    # Get dependency from dependencies table
    Dependency = Query()
    dependency_doc = db.table("dependencies").get(
        (Dependency.package_manager == dependency["package_manager"]) & 
        (Dependency.owner == dependency["owner"]) &
        (Dependency.name == dependency["name"]) &
        (Dependency.version == dependency["version"])
    )
    
    if not dependency_doc:
        logger.warning(f"No dependency found matching {dependency}")
        return []
        
    # Use the 'id' field instead of 'doc_id'
    dependency_id = dependency_doc['id']

    # Get issue IDs associated with this dependency
    IssueDependency = Query()
    issue_dependencies = db.table("issue_dependency").search(
        IssueDependency.dependency_id == dependency_id
    )
    issue_ids = [item["issue_id"] for item in issue_dependencies]

    # Filter issues table to only include issues for this dependency
    Issue = Query()
    filtered_issues = db.table("issues").search(Issue.id.one_of(issue_ids))

    logger.info(
        f"Found {len(filtered_issues)} issues for "
        f"{dependency['owner']}/{dependency['name']} v{dependency['version']}"
    )
    return filtered_issues
