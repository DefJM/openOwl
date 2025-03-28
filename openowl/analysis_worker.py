import json

from tqdm import tqdm

from openowl.llm import get_toxicity_score_llm
from openowl.logger_config import setup_logger

logger = setup_logger(__name__)


class AnalysisWorker:
    def __init__(self, db, model):
        self.db = db
        self.model = model

    def _ensure_toxicity_column_exists(self):
        """
        Ensure the metric_toxicity_llm column exists in the comments table.
        """
        try:
            self.db.cursor.execute(
                """
                ALTER TABLE comments
                ADD COLUMN metric_toxicity_llm TEXT
            """
            )
            self.db.conn.commit()
            logger.info("Added metric_toxicity_llm column to comments table")
        except Exception as e:
            # Column might already exist, which is fine
            logger.debug(f"Note: {str(e)}")
            pass

    def update_toxicity_scores_llm(
        self,
        repository_url=None,
        start_date=None,
        end_date=None,
        limit=None,
        batch_size=100,
    ):
        """
        Update the comments table with toxicity scores for GitHub comments using an LLM model.

        Args:
            repository_url (str, optional): URL of the repository to analyze. If None, analyzes all repositories.
            start_date (str, optional): ISO format date to filter comments created on or after this date.
            end_date (str, optional): ISO format date to filter comments created before this date.
            limit (int, optional): Maximum number of comments to process. If None, processes all matching comments.
            batch_size (int, optional): Number of comments to process in each batch for efficient processing.

        Returns:
            int: The number of comments processed and updated
        """
        # Ensure the column exists
        self._ensure_toxicity_column_exists()

        # Build the base query
        query = """
            SELECT c.id, c.body, c.created_at, c.issue_id, r.url as repository_url
            FROM comments c
            JOIN repositories r ON c.repository_id = r.id
            WHERE c.metric_toxicity_llm IS NULL
        """

        params = []

        # Add filters if provided
        if repository_url:
            query += " AND r.url = ?"
            params.append(repository_url)

        if start_date:
            query += " AND c.created_at >= ?"
            params.append(start_date)

        if end_date:
            query += " AND c.created_at <= ?"
            params.append(end_date)

        # Order by newest first
        query += " ORDER BY c.created_at DESC"

        # Add limit if provided
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        # Execute the query
        self.db.cursor.execute(query, params)
        comments = self.db.cursor.fetchall()

        if not comments:
            logger.info("No comments found that need toxicity analysis.")
            return 0

        logger.info(f"Found {len(comments)} comments to analyze for toxicity")

        # Process comments in batches
        processed_count = 0
        total_comments = len(comments)

        with tqdm(total=total_comments, desc="Analyzing comment toxicity") as pbar:
            for i, comment in enumerate(comments):
                comment_id, body, created_at, issue_id, repo_url = comment

                if not body:
                    logger.warning(
                        f"Empty comment body for comment ID {comment_id}, skipping"
                    )
                    pbar.update(1)
                    continue

                try:
                    # Get toxicity score from LLM
                    toxicity_data = get_toxicity_score_llm(body, self.model)

                    # Convert to JSON string for storage
                    toxicity_json = json.dumps(toxicity_data)

                    # Update the database
                    self.db.cursor.execute(
                        "UPDATE comments SET metric_toxicity_llm = ? WHERE id = ?",
                        (toxicity_json, comment_id),
                    )

                    # Commit every batch_size updates to avoid long transactions
                    if (i + 1) % batch_size == 0 or i == total_comments - 1:
                        self.db.conn.commit()
                        logger.debug(
                            f"Committed batch of {min(batch_size, i + 1 - processed_count)} updates"
                        )

                    processed_count += 1
                    pbar.update(1)

                except Exception as e:
                    logger.error(f"Error processing comment {comment_id}: {str(e)}")
                    pbar.update(1)
                    continue

        # Ensure final commit
        self.db.conn.commit()
        logger.info(
            f"Successfully analyzed and updated {processed_count} comments with toxicity scores"
        )

        return processed_count
