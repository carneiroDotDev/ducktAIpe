# Objective: This file initializes the FastAPI web 
# application and manages the interaction between the user 
# interface and the orchestrator.

import logging
import os
import json
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from httpx_sse import aconnect_sse

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from google.genai import types as genai_types
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider, export
from pydantic import BaseModel

# Import utility for authenticated communication
from authenticated_httpx import create_authenticated_client

# Define data model for user feedback on agent runs
class Feedback(BaseModel):
    score: float
    text: str | None = None
    run_id: str | None = None
    user_id: str | None = None

# Configure logging for the application
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up tracing with OpenTelemetry and Cloud Trace
provider = TracerProvider()
processor = export.BatchSpanProcessor(
    CloudTraceSpanExporter(),
)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Initialize FastAPI application
app = FastAPI()

# Enable Cross Origin Resource Sharing for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load configuration from environment variables
agent_name = os.getenv("AGENT_NAME", None)
agent_server_url = os.getenv("AGENT_SERVER_URL")

# Validate that the agent server URL is provided
if not agent_server_url:
    raise ValueError("AGENT_SERVER_URL environment variable not set")
else:
    # Remove trailing slashes for consistent URL building
    agent_server_url = agent_server_url.rstrip("/")

# Cache for authenticated HTTP clients
clients: Dict[str, httpx.AsyncClient] = {}

# Helper to retrieve or create an authenticated client for a server origin
async def get_client(agent_server_origin: str) -> httpx.AsyncClient:
    global clients
    if agent_server_origin not in clients:
        clients[agent_server_origin] = create_authenticated_client(agent_server_origin)
    return clients[agent_server_origin]

# Initiates a new session with the remote ADK agent server
async def create_session(agent_server_origin: str, agent_name: str, user_id: str) -> Dict[str, Any]:
    httpx_client = await get_client(agent_server_origin)
    headers=[
        ("Content-Type", "application/json")
    ]
    # Build the endpoint path for session creation
    session_request_url = f"{agent_server_origin}/apps/{agent_name}/users/{user_id}/sessions"
    session_response = await httpx_client.post(
        session_request_url,
        headers=headers
    )
    # Ensure the request was successful
    session_response.raise_for_status()
    return session_response.json()

# Fetches existing session details from the ADK server
async def get_session(agent_server_origin: str, agent_name: str, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    httpx_client = await get_client(agent_server_origin)
    headers=[
        ("Content-Type", "application/json")
    ]
    # Build the endpoint path for session retrieval
    session_request_url = f"{agent_server_origin}/apps/{agent_name}/users/{user_id}/sessions/{session_id}"
    session_response = await httpx_client.get(
        session_request_url,
        headers=headers
    )
    # Return None if the session is not found
    if session_response.status_code == 404:
        return None
    # Raise error for other failed status codes
    session_response.raise_for_status()
    return session_response.json()


# Retrieves a list of available agents from the server
async def list_agents(agent_server_origin: str) -> List[str]:
    httpx_client = await get_client(agent_server_origin)
    headers=[
        ("Content-Type", "application/json")
    ]
    list_url = f"{agent_server_origin}/list-apps"
    list_response = await httpx_client.get(
        list_url,
        headers=headers
    )
    list_response.raise_for_status()
    agent_list = list_response.json()
    # Default to a generic agent name if none are found
    if not agent_list:
        agent_list = ["agent"]
    return agent_list


# Executes a user query against the ADK agent using Server Sent Events
async def query_adk_sever(
        agent_server_origin: str, agent_name: str, user_id: str, message: str, session_id: str,
        image_base64: Optional[str] = None, image_mime_type: Optional[str] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    httpx_client = await get_client(agent_server_origin)
    
    parts = [{"text": message}]
    if image_base64 and image_mime_type:
        parts.append({
            "inline_data": {
                "mime_type": image_mime_type,
                "data": image_base64
            }
        })
        
    # Construct the payload for the agent run
    request = {
        "appName": agent_name,
        "userId": user_id,
        "sessionId": session_id,
        "newMessage": {
            "role": "user",
            "parts": parts
        },
        "streaming": False
    }
    # Open an SSE connection to stream events back to the client
    async with aconnect_sse(
        httpx_client,
        "POST",
        f"{agent_server_origin}/run_sse",
        json=request
    ) as event_source:
        # Handle connection errors
        if event_source.response.is_error:
            event = {
                "author": agent_name,
                "content":{
                    "parts": [
                        {
                            "text": f"Error {event_source.response.text}"
                        }
                    ]
                }
            }
            yield event
        else:
            # Iterate through events produced by the agent pipeline
            async for server_event in event_source.aiter_sse():
                event = server_event.json()
                yield event

# Schema for the simplified chat request
class SimpleChatRequest(BaseModel):
    message: str
    user_id: str = "test_user"
    session_id: Optional[str] = None
    image_base64: Optional[str] = None
    image_mime_type: Optional[str] = None

# Primary API endpoint for streaming course generation progress and results
@app.post("/api/chat_stream")
async def chat_stream(request: SimpleChatRequest):
    """Streaming chat endpoint."""
    global agent_name, agent_server_url
    # Automatically select the first agent if not explicitly configured
    if not agent_name:
        agent_name = (await list_agents(agent_server_url))[0] # type: ignore

    session = None
    # Reconnect to an existing session if a session id is provided
    if request.session_id:
        session = await get_session(
            agent_server_url, # type: ignore
            agent_name,
            request.user_id,
            request.session_id
        )
    # Create a fresh session if no existing session is found or provided
    if session is None:
        session = await create_session(
            agent_server_url, # type: ignore
            agent_name,
            request.user_id
        )

    # Begin the agent pipeline execution
    events = query_adk_sever(
        agent_server_url, # type: ignore
        agent_name,
        request.user_id,
        request.message,
        session["id"],
        request.image_base64,
        request.image_mime_type
    )

    # Nested generator to process agent events and stream formatted updates
    async def event_generator():
        final_text = ""
        gatekeeper_rejected = False
        async for event in events:
            # Send progress updates based on which agent is active
            if event["author"] == "gatekeeper":
                 yield json.dumps({"type": "progress", "text": "🚪 Gatekeeper is checking visual context..."}) + "\n"
            elif event["author"] == "researcher":
                 yield json.dumps({"type": "progress", "text": "🔍 Researcher is gathering information..."}) + "\n"
            elif event["author"] == "judge":
                 yield json.dumps({"type": "progress", "text": "⚖️ Judge is evaluating findings..."}) + "\n"
            elif event["author"] == "content_builder":
                 yield json.dumps({"type": "progress", "text": "🦆 Our Duck is writing the repair tutorial..."}) + "\n"
            
            # Aggregate the final response content parts
            if "content" in event and event["content"]:
                content = genai_types.Content.model_validate(event["content"])
                for part in content.parts: # type: ignore
                    if part.text:
                        if event["author"] == "gatekeeper":
                            try:
                                gatekeeper_res = json.loads(part.text)
                                if not gatekeeper_res.get("enough_context", False):
                                    gatekeeper_rejected = True
                                    yield json.dumps({"type": "gatekeeper_reject", "text": "Sorry our duck 🦆 needs you to give further context of what needs to be fixed. Try typing or sending a better picture of the object to be fixed."}) + "\n"
                                    # We yield the reject and then can break so frontend stops waiting
                                else:
                                    recognized = gatekeeper_res.get("recognized_object", "issue")
                                    yield json.dumps({"type": "gatekeeper_accept", "text": f"Oh you have a broken {recognized}, let me tell you how to fix it 🦆"}) + "\n"
                            except json.JSONDecodeError:
                                pass
                        elif not gatekeeper_rejected: # Only append if gatekeeper passed
                            final_text += part.text
        
        # Deliver the complete result to the frontend
        if not gatekeeper_rejected:
            yield json.dumps({"type": "result", "text": final_text.strip()}) + "\n"

    # Return as an NDJSON stream for real time UI updates
    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

# Attach the static frontend files to the web server
frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

# Start the server if the script is executed directly
if __name__ == "__main__":
    import uvicorn
    # Use the port specified in environment variables or default to 8000
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
