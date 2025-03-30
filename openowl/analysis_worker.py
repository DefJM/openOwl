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

    def _ensure_toxicity_columns_exist(self):
        """Ensure toxicity-related columns exist in the comments table."""
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
        
        try:
            self.db.cursor.execute(
                """
                ALTER TABLE comments
                ADD COLUMN metric_toxicity_detoxify TEXT
            """
            )
            self.db.conn.commit()
            logger.info("Added metric_toxicity_detoxify column to comments table")
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
        self._ensure_toxicity_columns_exist()

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

    def update_toxicity_scores_detoxify(
        self,
        repository_urls=None,
        start_date=None,
        end_date=None,
        limit=None,
        batch_size=10,
        repository_url=None,
        force_update=False,
        filter_bots=True,
        detoxify_model="original"
    ):
        """
        Update the comments table with toxicity scores for GitHub comments using Detoxify model.

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
            detoxify_model (str, optional): Detoxify model to use ("original", "unbiased", or "multilingual").
                Defaults to "original".

        Returns:
            int: The number of comments processed and updated
        """
        # Import here to avoid dependency issues if Detoxify is not installed
        try:
            from detoxify import Detoxify
        except ImportError:
            logger.error("Detoxify is not installed. Please install it with: pip install detoxify")
            return 0

        # Handle backward compatibility with repository_url parameter
        if repository_url is not None:
            if repository_urls is not None:
                logger.warning("Both repository_url and repository_urls were provided. Using repository_urls.")
            else:
                repository_urls = repository_url
                logger.warning("The repository_url parameter is deprecated. Please use repository_urls instead.")

        # Ensure the column exists
        self._ensure_toxicity_columns_exist()

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
                SELECT c.id, c.body, c.created_at, c.issue_id, r.url as repository_url, c.html_url, c.metric_toxicity_detoxify,
                       u.username as author_username, u.type as user_type
                FROM comments c
                JOIN repositories r ON c.repository_id = r.id
                JOIN users u ON c.user_id = u.id
                WHERE 1=1
            """
        else:
            # Otherwise, include only comments with no evaluation or that need to be updated
            query = """
                SELECT c.id, c.body, c.created_at, c.issue_id, r.url as repository_url, c.html_url, c.metric_toxicity_detoxify,
                       u.username as author_username, u.type as user_type
                FROM comments c
                JOIN repositories r ON c.repository_id = r.id
                JOIN users u ON c.user_id = u.id
                WHERE c.metric_toxicity_detoxify IS NULL
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
            logger.info(f"No comments found that need Detoxify toxicity analysis within the specified criteria.")
            return 0

        # Initialize Detoxify model
        try:
            detector = Detoxify(detoxify_model)
        except Exception as e:
            logger.error(f"Failed to initialize Detoxify model: {str(e)}")
            return 0

        # Process comments in batches
        processed_count = 0
        total_comments = len(all_comments)

        with tqdm(total=total_comments, desc="Analyzing comment toxicity with Detoxify") as pbar:
            # Process in batches for efficiency
            for i in range(0, total_comments, batch_size):
                batch = all_comments[i:i+batch_size]
                comment_texts = [comment[1] for comment in batch if comment[1]]  # Extract comment bodies
                comment_ids = [comment[0] for comment in batch if comment[1]]  # Extract comment IDs
                existing_toxicity_jsons = [comment[6] for comment in batch if comment[1]]  # Extract existing toxicity data
                
                # Skip empty batch
                if not comment_texts:
                    pbar.update(len(batch))
                    continue
                    
                try:
                    # Run Detoxify on the batch
                    batch_results = detector.predict(comment_texts)
                    
                    # Process each result
                    for j, (comment_id, comment_text, existing_toxicity_json) in enumerate(
                        zip(comment_ids, comment_texts, existing_toxicity_jsons)
                    ):
                        # Extract scores for this comment
                        scores = {
                            "toxicity": float(batch_results["toxicity"][j]),
                            "severe_toxicity": float(batch_results["severe_toxicity"][j]),
                            "obscene": float(batch_results["obscene"][j]),
                            "threat": float(batch_results["threat"][j]),
                            "insult": float(batch_results["insult"][j]),
                            "identity_attack": float(batch_results["identity_attack"][j])
                        }
                        
                        # Enrich with metadata
                        enriched_toxicity_data = self._enrich_detoxify_data(
                            scores, 
                            existing_toxicity_json
                        )
                        
                        # Convert to JSON for storage
                        toxicity_json = json.dumps(enriched_toxicity_data)
                        
                        # Log the toxicity result
                        logger.info(
                            f"[Detoxify] Comment {comment_id} | Score: {enriched_toxicity_data['evaluations'][enriched_toxicity_data['latest_evaluation']]['toxicity_score']} "
                            f"| Toxicity: {scores['toxicity']:.3f}, Severe: {scores['severe_toxicity']:.3f}"
                        )
                        
                        # Update the database
                        self.db.cursor.execute(
                            "UPDATE comments SET metric_toxicity_detoxify = ? WHERE id = ?",
                            (toxicity_json, comment_id),
                        )
                        
                        processed_count += 1
                    
                    # Commit batch updates
                    if (i + len(batch)) % batch_size == 0 or i + len(batch) == total_comments:
                        self.db.conn.commit()
                        logger.debug(f"Committed batch of {len(batch)} updates")
                    
                    pbar.update(len(batch))
                    
                except Exception as e:
                    logger.error(f"Error processing batch: {str(e)}")
                    pbar.update(len(batch))
                    continue

        # Ensure final commit
        self.db.conn.commit()
        logger.info(
            f"Successfully analyzed and updated {processed_count} comments with Detoxify toxicity scores"
        )

        return processed_count

    def _enrich_detoxify_data(self, detoxify_scores, existing_toxicity_json=None):
        """Enrich Detoxify toxicity data with metadata and store in multi-evaluation structure.
        
        Args:
            detoxify_scores (dict): Original toxicity scores from Detoxify.
            existing_toxicity_json (str, optional): Existing JSON toxicity data to merge with.
            
        Returns:
            dict: Enriched toxicity data with metadata in multi-evaluation structure.
        """
        # Get current timestamp in ISO format
        current_time = datetime.now().isoformat()
        
        # Define the Detoxify version/model
        detoxify_version = "original"  # Could be parameterized: "original", "unbiased", "multilingual"
        
        # Create derived overall toxicity score (1-5 scale)
        # This is a simplification - you might want a more sophisticated approach
        toxicity_value = detoxify_scores.get("toxicity", 0)
        severe_value = detoxify_scores.get("severe_toxicity", 0)
        
        # Weight severe toxicity more heavily in the combined score
        combined_score = (toxicity_value * 0.7) + (severe_value * 1.5)
        
        # Map to 1-5 scale (similar to LLM scale)
        if combined_score < 0.2:
            overall_score = 1  # not toxic
        elif combined_score < 0.4:
            overall_score = 2  # slightly concerning
        elif combined_score < 0.6:
            overall_score = 3  # moderately concerning
        elif combined_score < 0.8:
            overall_score = 4  # toxic
        else:
            overall_score = 5  # extremely toxic
        
        # Create explanation text based on the scores
        explanation = f"Detoxify scores: toxicity={toxicity_value:.3f}, severe_toxicity={severe_value:.3f}, "
        explanation += f"obscene={detoxify_scores.get('obscene', 0):.3f}, threat={detoxify_scores.get('threat', 0):.3f}, "
        explanation += f"insult={detoxify_scores.get('insult', 0):.3f}, identity_attack={detoxify_scores.get('identity_attack', 0):.3f}"
        
        # Create single evaluation structure
        evaluation = {
            "toxicity_score": str(overall_score),
            "toxicity_rationale": explanation,
            "detailed_scores": {
                "toxicity": detoxify_scores.get("toxicity", 0),
                "severe_toxicity": detoxify_scores.get("severe_toxicity", 0),
                "obscene": detoxify_scores.get("obscene", 0),
                "threat": detoxify_scores.get("threat", 0),
                "insult": detoxify_scores.get("insult", 0),
                "identity_attack": detoxify_scores.get("identity_attack", 0)
            },
            
            "model_info": {
                "model_name": "detoxify",
                "provider": "detoxify",
                "version": detoxify_version,
                "mapping_algorithm": "weighted_combined_score"
            },
            
            "eval_metadata": {
                "timestamp": current_time,
                "prompt_version": "n/a",  # Not applicable for Detoxify
            }
        }
        
        # Generate config key for this evaluation
        config_key = f"detoxify_{detoxify_version}"
        
        # Check if we have existing data to merge with
        if existing_toxicity_json:
            try:
                existing_data = json.loads(existing_toxicity_json)
                
                # If the existing data uses the old structure, convert it
                if 'evaluations' not in existing_data:
                    old_version = existing_data.get('model_info', {}).get('version', 'unknown')
                    old_key = f"detoxify_{old_version}"
                    
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

    def query_toxic_comments(self, repository_url=None, min_score=4, limit=100, model=None, provider=None, 
                             prompt_version=None, include_bots=False, evaluation_type="llm"):
        """Query comments with high toxicity scores.
        
        Args:
            repository_url (str, optional): Repository URL to filter comments by.
            min_score (int, optional): Minimum toxicity score threshold (1-5). Default is 4.
            limit (int, optional): Maximum number of comments to return. Default is 100.
            model (str, optional): Filter by specific model.
            provider (str, optional): Filter by specific provider.
            prompt_version (str, optional): Filter by specific prompt version.
            include_bots (bool, optional): Whether to include bot comments. Default is False.
            evaluation_type (str, optional): Type of evaluation to use ("llm", "detoxify", or "both"). Default is "llm".
            
        Returns:
            list: List of dictionaries containing comment data with high toxicity scores
        """
        # Determine which column to use based on evaluation_type
        toxicity_column = None
        if evaluation_type.lower() == "llm":
            toxicity_column = "c.metric_toxicity_llm"
        elif evaluation_type.lower() == "detoxify":
            toxicity_column = "c.metric_toxicity_detoxify"
        elif evaluation_type.lower() == "both":
            # Will handle this case specially below
            pass
        else:
            raise ValueError(f"Invalid evaluation_type: {evaluation_type}. Must be 'llm', 'detoxify', or 'both'.")
        
        # Build query based on evaluation type
        if evaluation_type.lower() == "both":
            query = """
                SELECT c.*, r.url as repository_url, u.username as author_username,
                       c.metric_toxicity_llm as raw_toxicity_llm,
                       c.metric_toxicity_detoxify as raw_toxicity_detoxify,
                       u.type as user_type
                FROM comments c
                JOIN repositories r ON c.repository_id = r.id
                JOIN users u ON c.user_id = u.id
                WHERE (c.metric_toxicity_llm IS NOT NULL OR c.metric_toxicity_detoxify IS NOT NULL)
            """
        else:
            query = f"""
                SELECT c.*, r.url as repository_url, u.username as author_username,
                       {toxicity_column} as raw_toxicity_data,
                       u.type as user_type
                FROM comments c
                JOIN repositories r ON c.repository_id = r.id
                JOIN users u ON c.user_id = u.id
                WHERE {toxicity_column} IS NOT NULL
            """
        
        params = []
        
        if repository_url:
            query += " AND r.url = ?"
            params.append(repository_url)
            
        # Filter out bot comments if include_bots is False
        if not include_bots:
            # Filter out users with type 'Bot' and usernames ending with '[bot]'
            query += " AND (u.type != 'Bot' AND u.username NOT LIKE '%[bot]')"
        
        query += " ORDER BY c.created_at DESC LIMIT ?"
        params.append(limit)
        
        self.db.cursor.execute(query, params)
        
        columns = [desc[0] for desc in self.cursor.description]
        results = []
        
        for row in self.cursor.fetchall():
            row_dict = dict(zip(columns, row))
            
            # Process based on evaluation type
            if evaluation_type.lower() == "both":
                # Process both LLM and Detoxify data
                llm_data = row_dict.get('raw_toxicity_llm')
                detoxify_data = row_dict.get('raw_toxicity_detoxify')
                
                llm_score = self._extract_toxicity_score(llm_data, model, provider, prompt_version)
                detoxify_score = self._extract_toxicity_score(detoxify_data, model, provider, prompt_version, 
                                                              is_detoxify=True)
                
                # Only include if either score meets the threshold
                if (llm_score and int(llm_score) >= min_score) or (detoxify_score and int(detoxify_score) >= min_score):
                    row_dict['llm_toxicity_score'] = llm_score
                    row_dict['detoxify_toxicity_score'] = detoxify_score
                    row_dict['max_toxicity_score'] = max(int(llm_score or 0), int(detoxify_score or 0))
                    results.append(row_dict)
            else:
                # Process for single evaluation type
                toxicity_json = row_dict.get('raw_toxicity_data')
                toxicity_score = self._extract_toxicity_score(
                    toxicity_json, model, provider, prompt_version, 
                    is_detoxify=(evaluation_type.lower() == "detoxify")
                )
                
                if toxicity_score and int(toxicity_score) >= min_score:
                    row_dict['toxicity_score'] = toxicity_score
                    results.append(row_dict)
        
        return results

    def _extract_toxicity_score(self, toxicity_json, model=None, provider=None, prompt_version=None, is_detoxify=False):
        """Helper method to extract toxicity score from JSON data with filtering.
        
        Args:
            toxicity_json (str): JSON string containing toxicity evaluation data
            model (str, optional): Filter by specific model
            provider (str, optional): Filter by specific provider
            prompt_version (str, optional): Filter by specific prompt version
            is_detoxify (bool): Whether this is Detoxify data
            
        Returns:
            str or None: Toxicity score as a string, or None if no matching evaluation
        """
        if not toxicity_json:
            return None
        
        try:
            toxicity_data = json.loads(toxicity_json)
            
            # Handle both old and new structure
            if 'evaluations' in toxicity_data:
                # New structure
                evaluations = toxicity_data['evaluations']
                latest_key = toxicity_data.get('latest_evaluation')
                
                # For Detoxify, filter differently
                if is_detoxify:
                    for key, eval_data in evaluations.items():
                        if "detoxify" in key:
                            eval_version = eval_data.get('model_info', {}).get('version')
                            if model is None or eval_version == model:
                                return eval_data.get('toxicity_score')
                    return None
                
                # For LLM, use existing filtering logic
                for key, eval_data in evaluations.items():
                    eval_model = eval_data.get('model_info', {}).get('model_name')
                    eval_provider = eval_data.get('model_info', {}).get('provider')
                    eval_prompt = eval_data.get('eval_metadata', {}).get('prompt_version')
                    
                    if (model is None or eval_model == model) and \
                       (provider is None or eval_provider == provider) and \
                       (prompt_version is None or eval_prompt == prompt_version):
                        return eval_data.get('toxicity_score')
                
                # If no match but we have a latest evaluation, use that
                if latest_key in evaluations and not (model or provider or prompt_version):
                    return evaluations[latest_key].get('toxicity_score')
                    
                return None
            else:
                # Old structure - direct access
                if is_detoxify:
                    return toxicity_data.get('toxicity_score')
                
                # For LLM, check filters
                if (model is None or toxicity_data.get('model_info', {}).get('model_name') == model) and \
                   (provider is None or toxicity_data.get('model_info', {}).get('provider') == provider) and \
                   (prompt_version is None or toxicity_data.get('eval_metadata', {}).get('prompt_version') == prompt_version):
                    return toxicity_data.get('toxicity_score')
                
                return None
                
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def update_toxicity_scores(
        self,
        evaluation_method="llm",  # "llm", "detoxify", or "both"
        repository_urls=None,
        start_date=None,
        end_date=None,
        limit=None,
        batch_size=10,
        repository_url=None,
        force_update=False,
        filter_bots=True,
        detoxify_model="original"
    ):
        """
        Update the comments table with toxicity scores using the specified evaluation method(s).
        
        Args:
            evaluation_method (str): Which evaluation method to use ("llm", "detoxify", or "both").
            
            # All other parameters are the same as in individual methods
            
        Returns:
            dict: Count of processed comments for each method
        """
        results = {}
        
        if evaluation_method.lower() in ["llm", "both"]:
            llm_count = self.update_toxicity_scores_llm(
                repository_urls=repository_urls,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                batch_size=batch_size,
                repository_url=repository_url,
                force_update=force_update,
                filter_bots=filter_bots
            )
            results["llm"] = llm_count
            
        if evaluation_method.lower() in ["detoxify", "both"]:
            detoxify_count = self.update_toxicity_scores_detoxify(
                repository_urls=repository_urls,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                batch_size=batch_size,
                repository_url=repository_url,
                force_update=force_update,
                filter_bots=filter_bots,
                detoxify_model=detoxify_model
            )
            results["detoxify"] = detoxify_count
            
        return results
