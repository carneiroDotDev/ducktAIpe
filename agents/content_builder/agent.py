# Objective: This file defines the content builder agent that compiles 
# final research into structured tutorials.

import os
import logging
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import SseConnectionParams, McpToolset
from google.adk.agents.callback_context import CallbackContext

logger = logging.getLogger(__name__)

def get_id_token(url: str) -> str:
    """Fetches an identity token for the given audience when running in GCP."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import id_token
        target_audience = "/".join(url.split("/")[:3]) 
        return id_token.fetch_id_token(Request(), target_audience)
    except Exception:
        return ""

# Set up the MCP toolset for the content builder
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8888/sse")

mcp_headers = {}
if "localhost" not in MCP_SERVER_URL:
    token = get_id_token(MCP_SERVER_URL)
    if token:
        mcp_headers["Authorization"] = f"Bearer {token}"

mcp_toolset = McpToolset(
    connection_params=SseConnectionParams(
        url=MCP_SERVER_URL,
        headers=mcp_headers
    ),
    tool_filter=["find_youtube_video", "fetch_stock_image"]
)

# Define the model version for content generation
MODEL = "gemini-2.5-pro"

# Logging callbacks for the agent
def agent_before_callback(callback_context: CallbackContext, **kwargs):
    logger.info(">>> A2A: Received incoming request. Starting tutorial assembly...")

def agent_after_callback(callback_context: CallbackContext, **kwargs):
    logger.info("<<< A2A: Assembly complete. Sending tutorial back.")

# Define the Content Builder Agent
# This agent should take approved research and format it into a repair tutorial.
content_builder = Agent(
    name="content_builder",
    model=MODEL,
    description="Transforms research findings into a structured repair tutorial.",
    before_agent_callback=agent_before_callback,
    after_agent_callback=agent_after_callback,
    instruction="""
    You are the Expert Repair Guide Creator for ducktAIpe.
    Take the approved 'research_findings' from the session state and transform them into a
    well-structured, easy-to-follow repair tutorial in clean Markdown.

    **CRITICAL OUTPUT RULES:**
    - Output ONLY the final tutorial in Markdown. Do NOT include any internal context
      tags, JSON snippets, debug text, or phrases like "[Context: ...]" in your output.
    - Never repeat intermediate research drafts, judge feedback, or status messages.
      The output must be clean, polished, and ready for the end user.

    **Formatting Rules:**
    0. Each of the following parts should appear just once:
    1. Start with a main title using a single `#` (H1), e.g. `# How to Fix a Flat Bicycle Tire`.
    2. Include a `## Safety Warning` section immediately after the title if the repair has risks.
    3. You MUST call the `fetch_stock_image` tool with a short descriptive query (e.g. "bicycle flat tire repair").
       Embed the returned URL as a full-width image right after the Safety Warning section using:
       `![Repair Guide Image](URL_RETURNED_BY_TOOL)`
    4. Use `##` (H2) for sections: "Required Tools", "Step-by-Step Instructions", "Final Testing".
    5. Use `###` (H3) for individual steps within sections.
    6. Use bold text for tool names and critical safety actions.
    7. Maintain a helpful, encouraging, and clear tone throughout.
    8. At the very end of the tutorial, add a section:
       `## 🎬 Check this video tutorial!`
       Call the `find_youtube_video` tool with the main repair descriptive query.
       On the very next line after the heading, output ONLY the bare YouTube URL returned by
       the tool, with nothing else on that line. Example:
       ```
       ## 🎬 Check this video tutorial!
       https://www.youtube.com/watch?v=XXXXXXXXXXX
       ```
       Do NOT wrap the URL in markdown link syntax `[text](url)` — output the raw URL only.
    
    Aim for 3 images total to make the guide look premium and professional.

    Ensure the content directly addresses what the user's broken object is and how to fix it.

    To finalize, make a review of the content to eliminate any repetition or redundancy.
    """,
    tools=[mcp_toolset],
)
# Export the content builder as the root for this service
root_agent = content_builder