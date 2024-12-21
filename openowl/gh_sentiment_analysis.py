import pandas as pd
from detoxify import Detoxify
from tqdm import tqdm

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


def get_toxicity_scores_llm(issues_table, model):
    """
    Analyze toxicity of GitHub issue comments using Detoxify model.

    Args:
        issues_table: TinyDB table containing GitHub issues with comments.
            The table documents will be updated with sentiment scores for each comment.

    Returns:
        pandas.DataFrame: DataFrame containing comment data and toxicity scores.
    """
    comments_data_llm = []
    total_comments = sum(
        len(issue.get("comments_list", [])) for issue in issues_table.all()
    )
    with tqdm(total=total_comments, desc="Analyzing comment toxicity") as pbar:
        for issue in issues_table.all():
            issue_id = issue["id"]
            if "comments_list" in issue and len(issue["comments_list"]) > 0:
                for i, comment in enumerate(issue["comments_list"]):

                    # get toxicity score and rationale
                    toxicity_data = get_toxicity_score_llm(comment["body"], model)
                    logger.info(toxicity_data)

                    # Update the comment in TinyDB with toxicity data
                    issue["comments_list"][i]["comment_sentiments_llm"] = toxicity_data

                    # Create full entry for DataFrame (unchanged)
                    comment_entry = {
                        "datetime": comment["created_at"],
                        "issue_id": issue_id,
                        "comment_details": comment["body"],
                        "author_association": comment["author_association"],
                        "user": comment["user"]["login"],
                        "reactions_plus1": comment["reactions"]["+1"],
                        "reactions_minus1": comment["reactions"]["-1"],
                        "reactions_laugh": comment["reactions"]["laugh"],
                        "reactions_hooray": comment["reactions"]["hooray"],
                        "reactions_confused": comment["reactions"]["confused"],
                        "reactions_heart": comment["reactions"]["heart"],
                        "reactions_rocket": comment["reactions"]["rocket"],
                        "reactions_eyes": comment["reactions"]["eyes"],
                        "toxicity_llm_score": toxicity_data["toxicity_score"],
                        "toxicity_llm_rationale": toxicity_data["toxicity_rationale"],
                        # **toxicity_data,  # Unpack toxicity scores
                    }
                    comments_data_llm.append(comment_entry)
                    pbar.update(1)

                # Update the issue in the database with modified comments_list
                issues_table.update(
                    {"comments_list": issue["comments_list"]},
                    doc_ids=[issue.doc_id],
                )
    comments_df_llm = pd.DataFrame(comments_data_llm)
    comments_df_llm = comments_df_llm.sort_values("datetime")
    return comments_df_llm
