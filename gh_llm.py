from dotenv import load_dotenv


load_dotenv()

# os.getenv("CLAUDE_API_KEY")


# loosely following anthropic's guide https://docs.anthropic.com/en/docs/about-claude/use-case-guides/ticket-routing#time-to-assignment and https://docs.anthropic.com/en/docs/about-claude/use-case-guides/legal-summarization


def classify_support_request(issue_content):
    # Define the prompt for the classification task
    issue_summarization_prompt = f"""You will be acting as a summarization system for Github issues of open source libraries. Your task is to analyze the issue, including its comments, and output the appropriate summary and respective label, alongside with your reasoning. 

        Here is the Github issue data, obtained through the Github API, in JSON-format, which you need to classify:

        <request>{issue_content}</request>

        Please carefully analyze the above issue to determine and fill in the following fields


        Field 1: `tldr`: Text, summary of what the issue is about. very short. 
        Field 2: `security_relevancy`: Score, between 1 and 5, to assess the issue's relevancy for security / vulnerability concerns. 1 = no indication that the issue has concerns for security, 5 = very strong pointers for critical security concerns
        Field 3: `issue_label`: Label, which adds an issue label. Provide maximum three labels.
        Field 4: `positivity_negativity`: Score, between 1 and 5, to assess the positivity or negativity of the issue. 1 = positive, constructive discussion, 3 = factual, neutral discussion, 5 = negative discussion lacking constructive suggestions and rather disruptive to the thought process
        Field 5: `bug_label`: (Optional field) Label, which adds a bug class (only if issue is or has indicators to be a bug, provide a bug classification). Provide maximum three labels.
        
        
        regarding `issue_class`: Please have a look at following issue label list: {issue_label_list}. You only need to add new ones if the topic in not in this list
        regarding `bug_label`: Please have a look at follwing bug label list: {bug_label_list}. You only need to add new ones if the topic in not in this list
        

        Here is an example, considering following issue

        {example_issue_summary}

        Remember to always include your reasoning for the respective fields before your actual output. The reasoning should be enclosed in <reasoning> tags. Return only the reasoning and then the other fields 1 to 5.
 
        """
    


example_issue_summary = """
<tldr>Requests 2.32.0 strips double slashes in URLs, breaking AWS S3 presigned URLs and potentially other services.</tldr>

<security_relevancy>2</security_relevancy>

<issue_label>compatibility</issue_label>
<issue_label>url-handling</issue_label>
<issue_label>aws-s3</issue_label>

<positivity_negativity>3</positivity_negativity>

<bug_label>regression</bug_label>
<bug_label>breaking-change</bug_label>
"""