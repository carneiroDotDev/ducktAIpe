# Objective: This file defines the gatekeeper agent that evaluates 
# whether the user's input has enough context to build a repair tutorial.

import logging
from typing import Literal
from google.adk.agents import Agent
from pydantic import BaseModel, Field
from google.adk.agents.callback_context import CallbackContext

logger = logging.getLogger(__name__)

# Define the model version for the evaluation task
MODEL = "gemini-2.5-pro"

# Define the data structure for gatekeeper responses
class GatekeeperDecision(BaseModel):
    """Structured decision from the Gatekeeper agent."""
    enough_context: bool = Field(
        description="Whether there is enough context to identify the broken object and the general issue."
    )
    recognized_object: str = Field(
        description="The object that was recognized and what appears to be broken. If not enough context, a brief explanation of what is missing."
    )

# Logging callbacks for the agent
def agent_before_callback(callback_context: CallbackContext, **kwargs):
    logger.info(">>> A2A: Received incoming request. Validating user input...")

def agent_after_callback(callback_context: CallbackContext, **kwargs):
    logger.info("<<< A2A: Validation complete. Sending decision back.")

# Define the Gatekeeper Agent logic
gatekeeper = Agent(
    name="gatekeeper",
    model=MODEL,
    description="Evaluates if the user provided enough context to create a repair tutorial and identifies the broken object.",
    before_agent_callback=agent_before_callback,
    after_agent_callback=agent_after_callback,
    instruction="""
    You are a gatekeeper for a repair tutorial generator.
    Evaluate the user's prompt (which might describe an image or text).
    If there is enough information to understand what object is broken, set enough_context to true, and describe the recognized_object and the likely issue.
    If the prompt is too vague (e.g., 'fix this' without an object, or nonsense), set enough_context to false, and in recognized_object explain what context is missing.
    """,
    # Force the agent to output structured JSON
    output_schema=GatekeeperDecision,
    # These settings prevent the agent from delegating tasks
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

# Set the gatekeeper as the primary agent for this service
root_agent = gatekeeper