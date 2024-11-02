import pandas as pd
from detoxify import Detoxify
from tqdm import tqdm


def get_toxicity_scores(issues_table):
    """
    Analyze toxicity of GitHub issue comments using Detoxify model.

    Args:
        issues_table: TinyDB table containing GitHub issues with comments.
            The table documents will be updated with sentiment scores for each comment.

    Returns:
        pandas.DataFrame: DataFrame containing comment data and toxicity scores.
    """
    detector = Detoxify("original") # "original" or "multilingual"
    comments_data = []
    total_comments = sum(
        len(issue.get("comments_details", [])) for issue in issues_table.all()
    )
    with tqdm(total=total_comments, desc="Analyzing comment toxicity") as pbar:
        for issue in issues_table.all():
            issue_id = issue["id"]
            if "comments_details" in issue and len(issue["comments_details"]) > 0:
                for i, comment in enumerate(issue["comments_details"]):
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
                    issue["comments_details"][i]["comment_sentiments"] = sentiment_data
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
                # Update the issue in the database with modified comments_details
                issues_table.update(
                    {"comments_details": issue["comments_details"]},
                    doc_ids=[issue.doc_id],
                )
    comments_df = pd.DataFrame(comments_data)
    comments_df = comments_df.sort_values("datetime")
    return comments_df
