"""
jira_user_story.py
"""
from typing import List, Optional
from pydantic import BaseModel

class JiraStory(BaseModel):
    """
    JiraStory is a Pydantic model that defines the schema for a JIRA user story.
    """
    key: str
    summary: str
    description: Optional[str]
    acceptance_criteria: List[str]

    class Config:
        """
        Config is a Pydantic model configuration class that provides additional settings.
        """
        schema_extra = {
            "example": {
                "key": "PROJ-123",
                "summary": "As a user, I want to reset my password so that I can regain access to my account.",
                "description": "This feature allows users to reset their passwords via email.",
                "acceptance_criteria": [
                    "User can request a password reset link.",
                    "Password reset link expires after 24 hours.",
                    "User can set a new password after clicking the link."
                ]
            }
        }
