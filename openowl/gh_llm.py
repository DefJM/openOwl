import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from pprint import pprint

import anthropic
from dotenv import load_dotenv

from openowl.prompt_templates import bug_label_dict, issue_label_dict

load_dotenv()


# loosely following anthropic's guide https://docs.anthropic.com/en/docs/about-claude/use-case-guides/ticket-routing#time-to-assignment and https://docs.anthropic.com/en/docs/about-claude/use-case-guides/legal-summarization


def get_issue_summarization(
    issue_new_dict,
    issue_label_dict,
    bug_label_dict,
    issue_summary_example,
):
    # Define the prompt for the classification task
    issue_summarization_prompt = f"""You will be acting as a summarization system for Github issues of open source libraries. 
        Your task is to analyze the issue, including its comments, and output the appropriate summary and respective label, alongside with your reasoning. 
        
        <tldr> Text, summary of what the issue is about. very short. </tldr>
        <security_relevancy> Score, between 1 and 5, to assess the issue's relevancy for security / vulnerability concerns. 1 = no indication that the issue has concerns for security, 5 = very strong pointers for critical security concerns</security_relevancy>
        <issue_label> Label, which adds an issue label. Provide maximum three labels.</issue_label>
        <positivity_negativity> Score, between 1 and 5, to assess the positivity or negativity of the issue. 1 = positive, constructive discussion, 3 = factual, neutral discussion, 5 = negative discussion lacking constructive suggestions and rather disruptive to the thought process </positivity_negativity>
        <bug_label> OPTIONAL FIELD, ONLY USE IF THE ISSUE REALLY IS INDICATING A BUG! Label, which adds a bug class (only if issue is or has indicators to be a bug, provide a bug classification). Provide maximum three labels.</bug_label>
                
        Note regarding `issue_label`: Please have a look at following issue label list: {issue_label_dict}. You only need to add new ones if the topic in not in this list
        Note regarding `bug_label`: Please have a look at follwing bug label list: {bug_label_dict}. You only need to add new ones if the topic in not in this list
        
        Here is the summary example, which would be the resulting output of your summarization system: <example_summary_issue>{issue_summary_example}</example_summary_issue>

        The input Github issue data is obtained through the Github API, in JSON-format. 

        <issue>{issue_new_dict}</issue>
        Please carefully analyze the above issue, and provide the XML-output in the structure explained above.
        Please also include reasoning for the respective XML sections: 
        <security_relevancy_reasoning> your reasoning for security_relevancy</security_relevancy_reasoning>
        <issue_label_reasoning> your reasoning for the provided issue_label </issue_label_reasoning>
        <positivity_negativity_reasoning> your reasoning for the provided posivity / negativity score </positivity_negativity_reasoning>
        <bug_label_reasoning> your reasoning for the provided bug_label </bug_label_reasoning>
        """

    # Set the default model
    DEFAULT_MODEL = "claude-3-haiku-20240307"
    client = anthropic.Anthropic(
        # defaults to os.environ.get("ANTHROPIC_API_KEY")
        api_key=os.getenv("CLAUDE_API_KEY"),
    )
    message = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=700,
        temperature=0,
        messages=[{"role": "user", "content": issue_summarization_prompt}],
        stream=False,
    )
    issue_summarization_dict = xml_to_json(message.content[0].text)
    return issue_summarization_dict


def xml_to_json(xml_string):
    """
    Convert XML string to JSON-like dictionary.
    Wraps XML in root element, parses to dictionary.
    Handles reasoning tags and converts duplicates to lists.

    Args:
        xml_string (str): The XML string to be converted.

    Returns:
        dict: A dictionary representation of the XML content.
    """
    xml_string = f"<root>{xml_string.strip()}</root>"
    root = ET.fromstring(xml_string)
    # Iterate through all elements in the XML
    result = {}
    for elem in root:
        tag = elem.tag
        if tag.endswith("_reasoning"):
            # For reasoning tags, combine the text of all child elements
            text = "".join(elem.itertext()).strip()
        else:
            text = elem.text.strip() if elem.text else ""
        # If the tag already exists in the result, make it a list
        if tag in result:
            if isinstance(result[tag], list):
                result[tag].append(text)
            else:
                result[tag] = [result[tag], text]
        else:
            result[tag] = text
    return result
