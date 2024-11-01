import pandas as pd
from detoxify import Detoxify
from tinydb import TinyDB

# Load database
db = TinyDB("data/db_dependencies.json")
issues = db.table("issues")

# Initialize Detoxify
detector = Detoxify("original") # "multilingual" or "original"

# Initialize comments data
comments_data = []
for issue in issues:
    issue_id = issue["id"]
    if "comments_details" in issue:
        for comment in issue["comments_details"]:
            toxicity_scores = detector.predict(comment["body"])
            # Create a flat dictionary with all fields
            comment_entry = {
                "datetime": comment["created_at"],
                "issue_id": issue_id,
                "comment_details": comment["body"],
                "author_association": comment["author_association"],
                "user": comment["user"]["login"],
                "toxicity": float(toxicity_scores["toxicity"]),
                "severe_toxicity": float(toxicity_scores["severe_toxicity"]),
                "obscene": float(toxicity_scores["obscene"]),
                "threat": float(toxicity_scores["threat"]),
                "insult": float(toxicity_scores["insult"]),
                "identity_attack": float(toxicity_scores["identity_attack"]),
            }
            comments_data.append(comment_entry)

# Create DataFrame and sort by datetime
comments_df = pd.DataFrame(comments_data)
comments_df = comments_df.sort_values("datetime")

# Plot comment sentiments over time
comments_df.plot(kind="line", x="datetime", y="toxicity")

# Print toxic comments
comments_df["is_toxic"] = comments_df["toxicity"] > 0.0025
comments_df.loc[comments_df["is_toxic"]]["comment_details"].tolist()
