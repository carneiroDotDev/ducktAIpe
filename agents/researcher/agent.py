# Objective: This file defines the researcher agent that uses search 
# tools to gather information on requested topics.

from google.adk.agents import Agent
from google.adk.tools.google_search_tool import google_search

# Define the model version for the agent
MODEL = "gemini-2.5-pro"

# Define the Researcher Agent
# The researcher should be an Agent that uses the google_search tool
# and follows the instructions to gather information.

researcher = Agent(
    name="researcher",
    model=MODEL,
    description="Gathers information on a topic using Google Search.",
    instruction="""
    You are the Lead Repair Researcher for ducktAIpe. Your goal is to find comprehensive 
    and accurate technical information to fix the specific object identified by the user.
    Use the `google_search` tool to find:
    1. Common failure points for this object.
    2. Step-by-step disassembly and repair instructions.
    3. Required tools and safety precautions.
    4. Sourcing for replacement parts if applicable.
    
    If you receive feedback that your research is insufficient, refine your next search 
    to focus on the missing technical details.
    """,
    # The agent has access to external search capabilities
    tools=[google_search],
)

# Export the agent as the root for this service
root_agent = researcher
