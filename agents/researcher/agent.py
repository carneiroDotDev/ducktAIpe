# Objective: This file defines the researcher agent that uses search 
# tools to gather information on requested topics.

import os
import logging
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import SseConnectionParams, McpToolset
from google.adk.agents.callback_context import CallbackContext

logger = logging.getLogger(__name__)

# Set up the MCP toolset for the researcher.
# Fallback to local 8888 if no ENV var is present (during direct python testing).
#
# NOTE ON VERTEX AI TOOL COMPATIBILITY:
# Vertex AI does NOT allow mixing its built-in search grounding tool (google_search)
# with custom function declarations (like MCP tools) in a single request.
# To solve this, web search capability has been moved INTO the MCP server as the
# `search_web` tool (powered by duckduckgo_search). This way, the researcher
# uses ONLY McpToolset — a single homogeneous tool type — which Vertex AI supports.
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8888/sse")
mcp_toolset = McpToolset(
    connection_params=SseConnectionParams(url=MCP_SERVER_URL),
    # Expose both search and web reading tools to the researcher
    tool_filter=["search_web", "fetch_web_page_content"]
)

# Define the model version for the agent
MODEL = "gemini-2.5-pro"

# Logging callbacks for the agent
def agent_before_callback(callback_context: CallbackContext, **kwargs):
    logger.info(">>> A2A: Received incoming request. Starting processing...")

def agent_after_callback(callback_context: CallbackContext, **kwargs):
    logger.info("<<< A2A: Completed processing. Sending response back.")

# Define the Researcher Agent
researcher = Agent(
    name="researcher",
    model=MODEL,
    description="Gathers information on a topic using web search.",
    before_agent_callback=agent_before_callback,
    after_agent_callback=agent_after_callback,
    instruction="""
    You are the Lead Repair Researcher for ducktAIpe. Your goal is to find comprehensive 
    and accurate technical information to fix the specific object identified by the user.
    Use the `search_web` tool to find:
    1. Common failure points for this object.
    2. Step-by-step disassembly and repair instructions.
    3. Required tools and safety precautions.
    4. Sourcing for replacement parts if applicable.
    
    CRITICAL: When you find a promising link, highly technical manual, or official repair guide URL via `search_web`, YOU MUST USE the `fetch_web_page_content` tool to read the raw contents and exact steps from the page. Do not guess the fix. Read the manuals.
    
    If you receive feedback that your research is insufficient, refine your next search 
    to focus on the missing technical details.
    """,
    # All tools are MCP tools (function declarations) — fully compatible with Vertex AI.
    tools=[mcp_toolset],
)

# Export the agent as the root for this service
root_agent = researcher
