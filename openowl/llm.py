import os
import xml.etree.ElementTree as ET

from dotenv import load_dotenv

from openowl.llm_provider import LLMProvider
from openowl.llm_prompt_templates import (
    bug_label_dict,
    issue_label_dict,
    issue_summary_example,
)

load_dotenv()


# Config for providers and models
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "claude")  # claude or ollama
DEFAULT_MODEL = os.getenv("LLM_MODEL", "claude-3-5-haiku-20241022")  # For Claude
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")  # Default model for Ollama


def get_llm_provider(provider=None, model=None):
    """
    Get the LLM provider based on configuration.
    
    Args:
        provider (str, optional): The provider to use ('claude' or 'ollama')
        model (str, optional): The model to use
        
    Returns:
        LLMProvider: An instance of the requested LLM provider
    """
    provider = provider or DEFAULT_PROVIDER
    
    if provider.lower() == 'claude':
        model = model or DEFAULT_MODEL
    elif provider.lower() == 'ollama':
        model = model or OLLAMA_MODEL
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    
    return LLMProvider.create(provider, model)


# def get_issue_summarization(issue_new_dict, model=None, provider=None):
#     """
#     Summarize a GitHub issue and its comments using LLM.

#     Args:
#         issue_new_dict (dict): The issue data to be summarized.
#         model (str, optional): The model to use for summarization.
#         provider (str, optional): The provider to use ('claude' or 'ollama')

#     Returns:
#         dict: A dictionary containing the summarization results.
#     """
#     # Define the prompt for the classification task
#     issue_summarization_prompt = f"""You will be acting as a summarization system for Github issues of open source libraries. 
#         Your task is to analyze the issue, including its comments, and output the appropriate summary and respective label, alongside with your reasoning. 
        
#         <tldr> Text, summary of what the issue is about. very short. </tldr>
#         <security_relevancy> Score, INTEGER, between 1 and 5, to assess the issue's relevancy for security / vulnerability concerns. 1 = no indication that the issue has concerns for security, 5 = very strong pointers for critical security concerns</security_relevancy>
#         <issue_label> Label, which adds an issue label. Provide maximum three labels.</issue_label>
#         <positivity_negativity> Score, between 1 and 5, to assess the positivity or negativity of the issue. 1 = positive, constructive discussion, 3 = factual, neutral discussion, 5 = negative discussion lacking constructive suggestions and rather disruptive to the thought process </positivity_negativity>
#         <bug_label> OPTIONAL FIELD, ONLY USE IF THE ISSUE REALLY IS INDICATING A BUG! Label, which adds a bug class (only if issue is or has indicators to be a bug, provide a bug classification). Provide maximum three labels.</bug_label>
                
#         Note regarding `issue_label`: Please have a look at following issue label list: {issue_label_dict}. You only need to add new ones if the topic in not in this list
#         Note regarding `bug_label`: Please have a look at follwing bug label list: {bug_label_dict}. You only need to add new ones if the topic in not in this list
        
#         Here is the summary example, which would be the resulting output of your summarization system: <example_summary_issue>{issue_summary_example}</example_summary_issue>

#         The input Github issue data is obtained through the Github API, in JSON-format. 

#         <issue>{issue_new_dict}</issue>
#         Please carefully analyze the above issue, and provide the XML-output in the structure explained above.
#         Please also include reasoning for the respective XML sections: 
#         <security_relevancy_reasoning> your reasoning for security_relevancy</security_relevancy_reasoning>
#         <issue_label_reasoning> your reasoning for the provided issue_label </issue_label_reasoning>
#         <positivity_negativity_reasoning> your reasoning for the provided posivity / negativity score </positivity_negativity_reasoning>
#         <bug_label_reasoning> your reasoning for the provided bug_label </bug_label_reasoning>
#         """

#     # Get the LLM provider
#     llm = get_llm_provider(provider, model)
    
#     # Generate the response
#     response_text = llm.generate_text(
#         prompt=issue_summarization_prompt,
#         max_tokens=700,
#         temperature=0,
#     )
    
#     issue_summarization_dict = xml_to_json(response_text)
#     return issue_summarization_dict


def get_toxicity_score_llm(comment, model=None, provider=None):
    """
    Analyze the toxicity of a GitHub comment using LLM.

    Args:
        comment (str): The comment text to analyze for toxicity.
        model (str, optional): The model to use for toxicity analysis.
        provider (str, optional): The provider to use ('claude' or 'ollama')

    Returns:
        dict: A dictionary containing toxicity score and the rationale for the score.
    """
    # Define the prompt for the classification task
    toxicity_prompt = f"""You will be acting as a toxicity analysis system for Github comments.
        Your task is to analyze the comment and output a toxicity score on the scale from 1 to 5 and rationale.
        A toxic comment is one that is rude, disrespectful, or unreasonable, and likely to make other users leave a discussion.
        
        You MUST respond ONLY with the following XML format and nothing else:
        <toxicity_score>Score between 1 and 5</toxicity_score>
        <toxicity_rationale>Brief explanation of the score</toxicity_rationale>
        
        Toxicity scale, MUST BE AN INTEGER BETWEEN 1 AND 5, NO DECIMALS:
        1 = not toxic at all, constructive and respectful
        2 = not toxic
        3 = neutral or mildly negative but not toxic
        4 = moderately toxic, showing negativity or hostility
        5 = extremely toxic, hostile, or harmful

        Here is the comment to analyze:
        <comment>{comment}</comment>

        Remember, respond ONLY with valid XML using <toxicity_score> and <toxicity_rationale> tags.
        The toxicity_score MUST be a single integer value: 1, 2, 3, 4, or 5. Do not use 0 or decimal values.
        Do not include any other text outside these tags. Start your response with <toxicity_score>.
        """

    # Get the LLM provider
    llm = get_llm_provider(provider, model)
    
    # Generate the response
    response_text = llm.generate_text(
        prompt=toxicity_prompt,
        max_tokens=700,
        temperature=0,
    )
    
    try:
        toxicity_dict = xml_to_json(response_text)
        # Validate the required keys exist, or use defaults
        if 'toxicity_score' not in toxicity_dict:
            toxicity_dict['toxicity_score'] = '3'  # Default neutral score
            toxicity_dict['_parsing_error'] = True
        if 'toxicity_rationale' not in toxicity_dict:
            toxicity_dict['toxicity_rationale'] = "Parsing error - couldn't extract rationale"
            toxicity_dict['_parsing_error'] = True
            
        # Normalize the toxicity score to ensure it's an integer between 1-5
        try:
            # Convert to float first to handle both integer and decimal formats
            score_float = float(toxicity_dict['toxicity_score'])
            
            # Round and clamp to range 1-5
            if score_float < 1:
                normalized_score = 1
            elif score_float > 5:
                normalized_score = 5
            else:
                normalized_score = round(score_float)
                
            toxicity_dict['toxicity_score'] = str(normalized_score)
        except ValueError:
            # If conversion fails, default to neutral
            toxicity_dict['toxicity_score'] = '3'
            toxicity_dict['_score_normalization_error'] = True
            
    except Exception as e:
        # Fallback for completely invalid XML
        toxicity_dict = {
            'toxicity_score': '3',  # Default neutral score
            'toxicity_rationale': f"Error parsing LLM response: {str(e)}",
            '_parsing_error': True
        }
    print(f"Toxicity score: {toxicity_dict['toxicity_score']} - {toxicity_dict['toxicity_rationale']}")
    return toxicity_dict


def xml_to_json(xml_string):
    """
    Convert XML string to JSON-like dictionary.
    More robust parsing to handle malformed or incomplete XML.

    Args:
        xml_string (str): The XML string to be converted.

    Returns:
        dict: A dictionary representation of the XML content.
    """
    # Clean up the XML string - remove any text before the first < and after the last >
    clean_xml = xml_string.strip()
    
    # Add root element to make parsing easier
    xml_string = f"<root>{clean_xml}</root>"
    
    try:
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
    except ET.ParseError as e:
        # If XML parsing fails, try regex-based extraction as a fallback
        import re
        result = {}
        
        # Extract content between tags using regex
        tags_to_find = ['toxicity_score', 'toxicity_rationale']
        for tag in tags_to_find:
            pattern = f"<{tag}>(.*?)</{tag}>"
            matches = re.findall(pattern, xml_string, re.DOTALL)
            if matches:
                result[tag] = matches[0].strip()
        
        # If we couldn't extract anything, raise the original error
        if not result:
            raise
            
        return result
