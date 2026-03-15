# Objective: This script manages the local execution of 
# the researcher, judge, content builder, orchestrator, 
# and web application services.

#!/bin/bash

# Kill any existing processes on these ports
echo "Stopping any existing processes on ports 8000-8005, 8888..."
lsof -ti:8000,8001,8002,8003,8004,8005,8888 | xargs kill -9 2>/dev/null

# Set common environment variables for local development
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_GENAI_USE_VERTEXAI="True" # Use Gemini API locally
export GOOGLE_API_KEY="<your-key-here>" # Use if not using Vertex AI

echo "Starting Researcher Agent on port 8001..."
pushd agents/researcher
SERVICE_NAME="Researcher AG" uv run adk_app.py --host 0.0.0.0 --port 8001 --a2a . &
RESEARCHER_PID=$!
popd

echo "Starting Gatekeeper Agent on port 8005..."
pushd agents/gatekeeper
SERVICE_NAME="Gatekeeper AG" uv run adk_app.py --host 0.0.0.0 --port 8005 --a2a . &
GATEKEEPER_PID=$!
popd

echo "Starting Judge Agent on port 8002..."
pushd agents/judge
SERVICE_NAME="Judge AG" uv run adk_app.py --host 0.0.0.0 --port 8002 --a2a . &
JUDGE_PID=$!
popd

echo "Starting Content Builder Agent on port 8003..."
pushd agents/content_builder
SERVICE_NAME="Content Builder AG" uv run adk_app.py --host 0.0.0.0 --port 8003 --a2a . &
CONTENT_BUILDER_PID=$!
popd

echo "Starting MCP Server on port 8888..."
pushd mcp_server
uv run main.py &
MCP_PID=$!
popd

export RESEARCHER_AGENT_CARD_URL=http://localhost:8001/a2a/agent/.well-known/agent-card.json
export JUDGE_AGENT_CARD_URL=http://localhost:8002/a2a/agent/.well-known/agent-card.json
export CONTENT_BUILDER_AGENT_CARD_URL=http://localhost:8003/a2a/agent/.well-known/agent-card.json
export GATEKEEPER_AGENT_CARD_URL=http://localhost:8005/a2a/agent/.well-known/agent-card.json
export MCP_SERVER_URL="http://localhost:8888/sse"

echo "Starting Orchestrator Agent on port 8004..."
pushd agents/orchestrator
SERVICE_NAME="Orchestrator AG" uv run adk_app.py --host 0.0.0.0 --port 8004 . &
ORCHESTRATOR_PID=$!
popd

# Wait a bit for them to start up
sleep 5

echo "Starting Frontend-App on port 8000..."
pushd app
export AGENT_SERVER_URL=http://localhost:8004

uv run uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
popd

echo "All agents started!"
echo "Gatekeeper: http://localhost:8005"
echo "Researcher: http://localhost:8001"
echo "Judge: http://localhost:8002"
echo "Content Builder: http://localhost:8003"
echo "Orchestrator: http://localhost:8004"
echo "----------------------------------------"
echo "MCP Server: http://localhost:8888"
echo "App Server (Frontend): http://localhost:8000"
echo "----------------------------------------"
echo "Press Ctrl+C to stop all agents."

# Wait for all processes
trap "kill $GATEKEEPER_PID $RESEARCHER_PID $JUDGE_PID $CONTENT_BUILDER_PID $ORCHESTRATOR_PID $BACKEND_PID $MCP_PID; exit" INT
wait
