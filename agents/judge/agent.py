# Objective: This file defines the judge agent that evaluates 
# research findings for completeness and quality.

import logging
from typing import Literal
from google.adk.agents import Agent
from google.adk.apps.app import App
from pydantic import BaseModel, Field
from google.adk.agents.callback_context import CallbackContext

logger = logging.getLogger(__name__)

# Define the model version for the evaluation task
MODEL = "gemini-2.5-pro"

# Define the data structure for judge responses
class JudgeFeedback(BaseModel):
    """Structured feedback from the Judge agent."""
    # The status must be either pass or fail
    status: Literal["pass", "fail"] = Field(
        description="Whether the research is sufficient ('pass') or needs more work ('fail')."
    )
    # Explanation of the decision
    feedback: str = Field(
        description="Detailed feedback on what is missing. If 'pass', a brief confirmation."
    )

# Logging callbacks for the agent
def agent_before_callback(callback_context: CallbackContext, **kwargs):
    logger.info(">>> A2A: Received incoming request. Starting evaluation...")

def agent_after_callback(callback_context: CallbackContext, **kwargs):
    logger.info("<<< A2A: Evaluation complete. Sending feedback back.")

# Define the Judge Agent logic
# This agent acts as a quality gatekeeper
judge = Agent(
    name="judge",
    model=MODEL,
    description="Evaluates research findings for completeness and accuracy.",
    before_agent_callback=agent_before_callback,
    after_agent_callback=agent_after_callback,
    instruction="""
    You are the Master Repair Inspector for ducktAIpe.
    Evaluate the 'research_findings' against the user's repair request.
    Check for:
    1. Technical accuracy of the steps.
    2. Inclusion of necessary safety warnings.
    3. Clarity of the identification of the problem.
    
    If the findings are missing critical safety steps or technical details, return status='fail'.
    If they are comprehensive and safe, return status='pass'.
    """,
    # Force the agent to output structured JSON
    output_schema=JudgeFeedback,
    # These settings prevent the agent from delegating tasks
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

# Set the judge as the primary agent for this service
root_agent = judge