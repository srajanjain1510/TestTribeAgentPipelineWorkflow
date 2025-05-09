"""
agentic_pipeline_stlc.py
"""
from __future__ import annotations

import os
from typing import List
import requests
from dotenv import load_dotenv
from jira import JIRA
from pydantic import BaseModel
from langgraph.graph import StateGraph, END
# pylint: disable=too-few-public-methods
load_dotenv()
# JIRA Authentication Configuration
JIRA_SERVER = os.environ.get("JIRA_SERVER")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN")
# Connect to JIRA
jira_client = JIRA(server=JIRA_SERVER, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))


# Define the schemas for each state
class GraphState(BaseModel):
    """
    GraphState is a Pydantic model that defines the schema for the state of the pipeline.
    """
    issue_key: str | None = None
    jira_story: JiraStory | None = None
    test_cases: List[str] | None = None
    update_status: str | None = None


class JiraStory(BaseModel):
    """
    JiraStory is a Pydantic model that defines the schema for a JIRA user story.
    """
    key: str
    summary: str
    description: str
    acceptance_criteria: List[str]


# Create the StateGraph pipeline
graph = StateGraph(state_schema=GraphState)


# Define the start state
def start(data: GraphState):
    """
    Start state of the pipeline. This state initializes the pipeline and prepares
    for the next state.
    :param data: The input data for the pipeline.
    :return: issue_key: The JIRA issue key.
    """
    # Use dot notation to access attributes
    issue_key = data.issue_key
    # Return a dictionary with the updated state
    return {"issue_key": issue_key}


graph.add_node("start", start)


# Define the fetch_jira_story state
def fetch_story(data: GraphState):
    """
    Fetches the JIRA story from the JIRA server using the provided issue key.
    :param data: input data for the pipeline.
    :return: jira_story: The JIRA story object.
    """
    issue_key = data.issue_key
    # Fetch the JIRA issue
    issue = jira_client.issue(issue_key)

    # Extract relevant details from the JIRA issue
    jira_story = JiraStory(
        key=issue.key,
        summary=issue.fields.summary,
        description=issue.fields.description,
        acceptance_criteria=[
            # Example: Parse acceptance criteria from a custom field or description
            line.strip()
            for line in issue.fields.description.split("\n")
            if line.strip().startswith("-")
        ]
    )

    # Return a dictionary with the updated state
    return {"jira_story": jira_story}


graph.add_node("fetch_jira_story", fetch_story)


# Define the generate_test_cases state
def generate_cases(data: GraphState):
    """
    Generates test cases for the JIRA story using the LLaMA model.
    :param data: input data for the pipeline.
    :return: generated test cases.
    """
    jira_story = data.jira_story

    # Prepare the input prompt for the LLaMA model
    prompt = f"""
    Generate test cases for the following JIRA story:

    Title: {jira_story.summary}
    Description: {jira_story.description}
    Acceptance Criteria:
    {', '.join(jira_story.acceptance_criteria)}

    Please provide detailed test cases.
    """

    # Use the Ollama LLaMA model to generate test cases
    # Send the request to the local LLaMA server
    response = requests.post(
        "http://localhost:11434/v1/completions",
        json={
            "model": "llama3.1:latest",
            "prompt": prompt,
            "max_tokens": 1024,
            "temperature": 0.5
        }
    )

    # Check for errors in the response
    response.raise_for_status()

    # Parse the response
    generated_text = response.json()["choices"][0]["text"]

    # Extract test cases from the generated text
    test_cases = [line.strip() for line in generated_text.split("\n") if line.strip()]

    # Return a dictionary with the updated state
    return {"test_cases": test_cases}


graph.add_node("generate_test_cases", generate_cases)


# Define the update_jira_with_test_cases state
def update_jira(data: GraphState):
    """
    Updates the JIRA issue with the generated test cases.
    :param data: input data for the pipeline.
    :return: update status.
    """
    issue_key = data.issue_key
    test_cases = data.test_cases

    # Format the test cases as a comment
    comment_body = "### Generated Test Cases:\n" + "\n".join(f"- {tc}" for tc in test_cases)

    # Add the comment to the JIRA issue
    jira_client.add_comment(issue_key, comment_body)

    # Update status
    update_status = f"Test cases added to JIRA issue {issue_key}"

    # Return a dictionary with the updated state
    return {"update_status": update_status}


graph.add_node("update_jira_with_test_cases", update_jira)

# Define the edges
graph.add_edge("start", "fetch_jira_story")
graph.add_edge("fetch_jira_story", "generate_test_cases")
graph.add_edge("generate_test_cases", "update_jira_with_test_cases")
graph.add_edge("update_jira_with_test_cases", END)

# Set the entry point
graph.set_entry_point("start")

# Compile the graph
graph = graph.compile()

# Example: Run the pipeline
if __name__ == "__main__":
    # Input to the pipeline
    input_data = {"issue_key": "AIAGENTS-1"}

    # Run the pipeline
    result = graph.invoke(input_data)

    # Print the final output
    print("Pipeline Result:", result)
