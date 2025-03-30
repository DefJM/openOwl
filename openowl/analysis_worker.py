import json
from datetime import datetime, timedelta

from tqdm import tqdm

from openowl.llm import get_toxicity_score_llm
from openowl.logger_config import setup_logger

logger = setup_logger(__name__)


class AnalysisWorker:
    def __init__(self, db, model, provider=None):
        """Initialize the analysis worker.
        
        Args:
            db: Database connection.
            model: LLM model to use.
            provider (str, optional): LLM provider to use ('claude' or 'ollama').
        """
        self.db = db
        self.model = model
        self.provider = provider
        self.prompt_version = "1.1" 

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

    def _enrich_toxicity_data(self, toxicity_data, existing_toxicity_json=None):
        """Enrich toxicity data with metadata fields and store in multi-evaluation structure.
        
        Args:
            toxicity_data (dict): Original toxicity data from LLM.
            existing_toxicity_json (str, optional): Existing JSON toxicity data to merge with.
            
        Returns:
            dict: Enriched toxicity data with metadata in multi-evaluation structure.
        """
        # Get current timestamp in ISO format
        current_time = datetime.now().isoformat()
        
        # Define generation parameters
        gen_params = {
            "temperature": 0,
            "max_tokens": 700
        }
        
        # Create single evaluation structure
        evaluation = {
            "toxicity_score": toxicity_data.get("toxicity_score"),
            "toxicity_rationale": toxicity_data.get("toxicity_rationale"),
            
            "model_info": {
                "model_name": self.model,
                "provider": self.provider,
                "generation_parameters": gen_params
            },
            
            "eval_metadata": {
                "timestamp": current_time,
                "prompt_version": self.prompt_version,
                "parsing_error": toxicity_data.get("_parsing_error", False)
            }
        }
        
        # Generate config key for this evaluation
        config_key = self._generate_config_key()
        
        # Check if we have existing data to merge with
        if existing_toxicity_json:
            try:
                existing_data = json.loads(existing_toxicity_json)
                
                # If the existing data uses the old structure, convert it
                if 'evaluations' not in existing_data:
                    old_model = existing_data.get('model_info', {}).get('model_name')
                    old_provider = existing_data.get('model_info', {}).get('provider')
                    old_prompt = existing_data.get('eval_metadata', {}).get('prompt_version')
                    old_key = self._generate_config_key(old_model, old_provider, old_prompt)
                    
                    # Create new structure with the old evaluation
                    result = {
                        "evaluations": {
                            old_key: existing_data
                        },
                        "latest_evaluation": old_key
                    }
                else:
                    # Use existing multi-evaluation structure
                    result = existing_data
                    
                # Add new evaluation
                result["evaluations"][config_key] = evaluation
                result["latest_evaluation"] = config_key
                
                return result
                
            except (json.JSONDecodeError, KeyError, TypeError):
                # If there's an error with existing data, just create new
                pass
        
        # Create new multi-evaluation structure
        return {
            "evaluations": {
                config_key: evaluation
            },
            "latest_evaluation": config_key
        }

    def _generate_config_key(self, model=None, provider=None, prompt_version=None):
        """Generate a unique key for a specific configuration.
        
        Args:
            model (str, optional): Model name. Defaults to self.model.
            provider (str, optional): Provider name. Defaults to self.provider.
            prompt_version (str, optional): Prompt version. Defaults to self.prompt_version.
            
        Returns:
            str: A unique key identifying this configuration
        """
        model = model or self.model
        provider = provider or self.provider
        prompt_version = prompt_version or self.prompt_version
        
        return f"{model}_{provider}_v{prompt_version}"

    def _evaluation_settings_match(self, existing_toxicity_json, current_settings=None):
        """Check if existing evaluation has identical settings to current settings.
        
        Args:
            existing_toxicity_json (str): JSON string of existing toxicity data
            current_settings (dict, optional): Dictionary of current settings to compare against.
                                              If None, uses current worker settings.
        
        Returns:
            bool: True if settings match, False otherwise
        """
        if not existing_toxicity_json:
            return False
        
        try:
            # Parse existing JSON
            existing_data = json.loads(existing_toxicity_json)
            
            # Get current settings
            current_model = current_settings.get('model') if current_settings else self.model
            current_provider = current_settings.get('provider') if current_settings else self.provider
            current_prompt_version = current_settings.get('prompt_version') if current_settings else self.prompt_version
            
            # Check if we're using the new multi-evaluation structure or old single-evaluation structure
            if 'evaluations' in existing_data:
                # New structure - check if this configuration exists
                config_key = self._generate_config_key(current_model, current_provider, current_prompt_version)
                return config_key in existing_data['evaluations']
            else:
                # Old structure - check settings directly
                existing_model = existing_data.get('model_info', {}).get('model_name')
                existing_provider = existing_data.get('model_info', {}).get('provider')
                existing_prompt_version = existing_data.get('eval_metadata', {}).get('prompt_version')
                
                return (
                    existing_model == current_model and
                    existing_provider == current_provider and
                    existing_prompt_version == current_prompt_version
                )
        except (json.JSONDecodeError, KeyError, TypeError):
            # If there's any error parsing or accessing the JSON, assume no match
            return False

    def update_toxicity_scores_llm(
        self,
        repository_urls=None,
        start_date=None,
        end_date=None,
        limit=None,
        batch_size=10,
        repository_url=None,
        force_update=False,
        filter_bots=True,
    ):
        """
        Update the comments table with toxicity scores for GitHub comments using an LLM model.

        Args:
            repository_urls (list or str, optional): URL(s) of the repositories to analyze. 
                If None, analyzes all repositories. Can be a single URL string or a list of URLs.
            start_date (str, optional): ISO format date to filter comments created on or after this date.
                If None and end_date is provided, defaults to 2 months before end_date.
            end_date (str, optional): ISO format date to filter comments created before this date.
                If None, defaults to current date.
            limit (int, optional): Maximum number of comments to process. If None, processes all matching comments.
            batch_size (int, optional): Number of comments to process in each batch for efficient processing.
            repository_url (str, optional): Deprecated. URL of a repository to analyze. Use repository_urls instead.
            force_update (bool, optional): If True, updates all comments regardless of existing evaluation.
            filter_bots (bool, optional): If True, excludes comments from bot users. Defaults to True.

        Returns:
            int: The number of comments processed and updated
        """
        # Handle backward compatibility with repository_url parameter
        if repository_url is not None:
            if repository_urls is not None:
                logger.warning("Both repository_url and repository_urls were provided. Using repository_urls.")
            else:
                repository_urls = repository_url
                logger.warning("The repository_url parameter is deprecated. Please use repository_urls instead.")

        # Ensure the column exists
        self._ensure_toxicity_column_exists()

        # Set default date range if not provided
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
            
        if start_date is None and end_date is not None:
            # Default to 2 months before end_date
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00')) if 'Z' in end_date else datetime.fromisoformat(end_date)
            start_dt = end_dt - timedelta(days=60)  # 2 months as 60 days
            start_date = start_dt.strftime("%Y-%m-%d")

        # Handle repository_urls parameter
        if repository_urls is not None and not isinstance(repository_urls, list):
            repository_urls = [repository_urls]  # Convert single URL to list

        # Build the base query
        if force_update:
            # If force_update is True, include all comments regardless of existing evaluation
            query = """
                SELECT c.id, c.body, c.created_at, c.issue_id, r.url as repository_url, c.html_url, c.metric_toxicity_llm,
                       u.username as author_username, u.type as user_type
                FROM comments c
                JOIN repositories r ON c.repository_id = r.id
                JOIN users u ON c.user_id = u.id
                WHERE 1=1
            """
        else:
            # Otherwise, include only comments with no evaluation or that need to be updated
            query = """
                SELECT c.id, c.body, c.created_at, c.issue_id, r.url as repository_url, c.html_url, c.metric_toxicity_llm,
                       u.username as author_username, u.type as user_type
                FROM comments c
                JOIN repositories r ON c.repository_id = r.id
                JOIN users u ON c.user_id = u.id
                WHERE c.metric_toxicity_llm IS NULL
            """

        params = []

        # Add repository filter if provided
        if repository_urls:
            placeholders = ','.join(['?'] * len(repository_urls))
            query += f" AND r.url IN ({placeholders})"
            params.extend(repository_urls)

        # Add date filters
        if start_date:
            query += " AND c.created_at >= ?"
            params.append(start_date)

        if end_date:
            query += " AND c.created_at <= ?"
            params.append(end_date)
        
        # Add bot filtering if requested
        if filter_bots:
            query += " AND (u.type != 'Bot' AND u.username NOT LIKE '%[bot]')"

        # Order by newest first
        query += " ORDER BY c.created_at DESC"

        # Add limit if provided
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        # Execute the query
        self.db.cursor.execute(query, params)
        all_comments = self.db.cursor.fetchall()

        if not all_comments:
            logger.info(f"No comments found that need toxicity analysis within the specified criteria.")
            return 0

        # Filter out comments that already have matching evaluations
        comments_to_process = []
        for comment in all_comments:
            comment_id, body, created_at, issue_id, repo_url, html_url, existing_toxicity_json, author_username, user_type = comment
            
            # Skip if already evaluated with the same settings and not forcing update
            if not force_update and existing_toxicity_json and self._evaluation_settings_match(existing_toxicity_json):
                continue
            
            comments_to_process.append((comment_id, body, created_at, issue_id, repo_url, html_url, author_username, user_type))
        
        if not comments_to_process:
            logger.info(f"All {len(all_comments)} comments already have up-to-date toxicity evaluations with current settings.")
            return 0
        
        logger.info(f"Found {len(comments_to_process)} comments to analyze for toxicity (skipped {len(all_comments) - len(comments_to_process)} already evaluated)")
        
        # Process comments in batches
        processed_count = 0
        total_comments = len(comments_to_process)

        with tqdm(total=total_comments, desc="Analyzing comment toxicity") as pbar:
            for i, comment in enumerate(comments_to_process):
                comment_id, body, created_at, issue_id, repo_url, html_url, author_username, user_type = comment

                if not body:
                    logger.warning(
                        f"Empty comment body for comment ID {comment_id}, URL: {html_url}, skipping"
                    )
                    pbar.update(1)
                    continue

                try:
                    # Get basic toxicity data
                    basic_toxicity_data = get_toxicity_score_llm(body, self.model, self.provider)
                    
                    # Enrich with metadata, merging with existing data if present
                    enriched_toxicity_data = self._enrich_toxicity_data(
                        basic_toxicity_data, 
                        existing_toxicity_json
                    )
                    
                    # Convert to JSON for storage
                    toxicity_json = json.dumps(enriched_toxicity_data)

                    # Log the toxicity result with comment URL and author info
                    logger.info(
                        f"Comment {comment_id} | Author: {author_username} | Score: {basic_toxicity_data.get('toxicity_score')} | URL: {html_url}"
                    )

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

    def check_comments_need_evaluation(self, repository_urls=None, start_date=None, end_date=None, filter_bots=True):
        """
        Check how many comments need evaluation with current settings.
        
        Args:
            repository_urls (list or str, optional): URL(s) of repositories to check.
            start_date (str, optional): ISO format date to filter comments created after this date.
            end_date (str, optional): ISO format date to filter comments created before this date.
            filter_bots (bool, optional): If True, excludes comments from bot users. Defaults to True.
            
        Returns:
            dict: Dictionary with counts of comments needing evaluation and total comments
        """
        # Convert single URL to list
        if repository_urls is not None and not isinstance(repository_urls, list):
            repository_urls = [repository_urls]
        
        # Build query to get all comments in the criteria
        query = """
            SELECT c.id, c.metric_toxicity_llm
            FROM comments c
            JOIN repositories r ON c.repository_id = r.id
            JOIN users u ON c.user_id = u.id
            WHERE 1=1
        """
        
        params = []
        
        # Add repository filter
        if repository_urls:
            placeholders = ','.join(['?'] * len(repository_urls))
            query += f" AND r.url IN ({placeholders})"
            params.extend(repository_urls)
            
        # Add date filters
        if start_date:
            query += " AND c.created_at >= ?"
            params.append(start_date)
            
        if end_date:
            query += " AND c.created_at <= ?"
            params.append(end_date)
        
        # Add bot filtering if requested
        if filter_bots:
            query += " AND (u.type != 'Bot' AND u.username NOT LIKE '%[bot]')"
        
        # Execute query
        self.db.cursor.execute(query, params)
        comments = self.db.cursor.fetchall()
        
        # Count comments needing evaluation
        total_comments = len(comments)
        needs_evaluation = 0
        
        for comment_id, existing_toxicity_json in comments:
            if not existing_toxicity_json or not self._evaluation_settings_match(existing_toxicity_json):
                needs_evaluation += 1
        
        return {
            "total_comments": total_comments,
            "needs_evaluation": needs_evaluation,
            "already_evaluated": total_comments - needs_evaluation,
            "evaluation_settings": {
                "model": self.model,
                "provider": self.provider,
                "prompt_version": self.prompt_version
            },
            "filter_bots": filter_bots
        }
