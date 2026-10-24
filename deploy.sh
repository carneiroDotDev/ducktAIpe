#!/bin/bash

# Objective: This script automates the deployment of the multi agent 
# services to Google Cloud Run.

set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "${SCRIPT_DIR}"

if [ -f ".env" ]; then
  source .env
fi

if [[ "${GOOGLE_CLOUD_PROJECT}" == "" ]]; then
  GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project -q)
fi
if [[ "${GOOGLE_CLOUD_PROJECT}" == "" ]]; then
  echo "ERROR: Run 'gcloud config set project' command to set active project, or set GOOGLE_CLOUD_PROJECT environment variable."
  exit 1
fi

REGION="${GOOGLE_CLOUD_LOCATION}"
if [[ "${REGION}" == "global" ]]; then
  echo "GOOGLE_CLOUD_LOCATION is set to 'global'. Getting a default location for Cloud Run."
  REGION=""
fi

if [[ "${REGION}" == "" ]]; then
  REGION=$(gcloud config get-value compute/region -q)
  if [[ "${REGION}" == "" ]]; then
    REGION="us-central1"
    echo "WARNING: Cannot get a configured compute region. Defaulting to ${REGION}."
  fi
fi
echo "Using project ${GOOGLE_CLOUD_PROJECT}."
echo "Using compute region ${REGION}."
GEMINI_MODEL="${GEMINI_MODEL:-gemini-3.8-flash}"
echo "Using Gemini model ${GEMINI_MODEL}."

gcloud run deploy gatekeeper \
  --source agents/gatekeeper \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --no-allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true" \
  --set-env-vars GEMINI_MODEL="${GEMINI_MODEL}"
GATEKEEPER_URL=$(gcloud run services describe gatekeeper --project $GOOGLE_CLOUD_PROJECT --region $REGION --format='value(status.url)')

gcloud run deploy mcp-server \
  --source mcp_server \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --allow-unauthenticated
MCP_URL=$(gcloud run services describe mcp-server --project $GOOGLE_CLOUD_PROJECT --region $REGION --format='value(status.url)')

# Wait for MCP server cold start / warm up
echo "Waiting for MCP server to wake up at $MCP_URL..."
MAX_RETRIES=20
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$MCP_URL/sse")
  
  if [[ "$STATUS" == "200" || "$STATUS" == "404" || "$STATUS" == "405" ]]; then
    echo "MCP server is awake! (Status: $STATUS)"
    break
  fi
  
  RETRY_COUNT=$((RETRY_COUNT+1))
  echo "Still waiting for MCP... status $STATUS ($RETRY_COUNT/$MAX_RETRIES)"
  sleep 3
done

gcloud run deploy researcher \
  --source agents/researcher \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --no-allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true" \
  --set-env-vars MCP_SERVER_URL="$MCP_URL/sse" \
  --set-env-vars GEMINI_MODEL="${GEMINI_MODEL}"
RESEARCHER_URL=$(gcloud run services describe researcher --project $GOOGLE_CLOUD_PROJECT --region $REGION --format='value(status.url)')

gcloud run deploy content-builder \
  --source agents/content_builder \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --no-allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true" \
  --set-env-vars MCP_SERVER_URL="$MCP_URL/sse" \
  --set-env-vars GEMINI_MODEL="${GEMINI_MODEL}"
CONTENT_BUILDER_URL=$(gcloud run services describe content-builder --project $GOOGLE_CLOUD_PROJECT --region $REGION --format='value(status.url)')

gcloud run deploy judge \
  --source agents/judge \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --no-allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true" \
  --set-env-vars GEMINI_MODEL="${GEMINI_MODEL}"
JUDGE_URL=$(gcloud run services describe judge --project $GOOGLE_CLOUD_PROJECT --region $REGION --format='value(status.url)')

gcloud run deploy orchestrator \
  --source agents/orchestrator \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --no-allow-unauthenticated \
  --set-env-vars GATEKEEPER_AGENT_CARD_URL=$GATEKEEPER_URL/a2a/agent/.well-known/agent-card.json \
  --set-env-vars RESEARCHER_AGENT_CARD_URL=$RESEARCHER_URL/a2a/agent/.well-known/agent-card.json \
  --set-env-vars JUDGE_AGENT_CARD_URL=$JUDGE_URL/a2a/agent/.well-known/agent-card.json \
  --set-env-vars CONTENT_BUILDER_AGENT_CARD_URL=$CONTENT_BUILDER_URL/a2a/agent/.well-known/agent-card.json \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true"
ORCHESTRATOR_URL=$(gcloud run services describe orchestrator --project $GOOGLE_CLOUD_PROJECT --region $REGION --format='value(status.url)')

gcloud run deploy ducktaipe-frontend \
  --source app \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars AGENT_SERVER_URL=$ORCHESTRATOR_URL \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}"

FRONTEND_URL=$(gcloud run services describe ducktaipe-frontend --project $GOOGLE_CLOUD_PROJECT --region $REGION --format='value(status.url)')
echo "--------------------------------------------------------"
echo "Deployment Complete! Frontend is live at: $FRONTEND_URL"
echo "--------------------------------------------------------"

