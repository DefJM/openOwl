


class DB:
    """Class to initialize and interact with the database using SQLite DB 
    """

    def __init__(self, path):
        """Initialize SQLite database
        Tables:
            - dependencies -> package info
            - issues -> issues data
            - issue_dependency -> issue id and dependency id
            - pull_requests -> pull requests data
            - pull_request_dependency -> pull request id and dependency id
            - comments -> comments data
            - comment_dependency -> comment id and dependency id
        Queries:
            - get_issues(owner, repo, state="open") -> get issues for a given package
            - get_issue_details(owner, repo, issue_number) -> get detailed data for a given issue
            - get_pull_requests(owner, repo) -> get pull requests for a given package
            - get_comments(owner, repo, issue_number) -> get comments for a given issue
        """


    def upsert_package(self, package):
        """Upsert package info into database"""
        pass

    def upsert_issues(self, issues):
        """Upsert issues into the database"""
        pass
    
    def upsert_pull_requests(self, pull_requests):
        """Upsert pull requests into the database"""
        pass
    
    def upsert_comments(self, comments):
        """Upsert comments into the database"""
        pass

    def upsert_issue_dependency(self, issue_id, dependency_id):
        """Upsert issue dependency into the database"""
        pass
    
    def upsert_pull_request_dependency(self, pull_request_id, dependency_id):
        """Upsert pull request dependency into the database"""
        pass
