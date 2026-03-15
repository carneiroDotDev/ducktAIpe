# AGENTS.md

## Project Overview
This project is a multi-agent **repair tutorial generation system** built using Google's **Agent Development Kit (ADK)** and the **Agent-to-Agent (A2A)** protocol. It is configured for local execution and deployment to Google Cloud Run.

## Project Structure
The application follows a distributed microservices architecture:

- **Orchestrator (`agents/orchestrator`)**: The master agent that coordinates the workflow. It uses a `SequentialAgent` to run a gatekeeper check, a research loop, and a content building phase.
- **Gatekeeper (`agents/gatekeeper`)**: A worker agent that validates whether the user's input (image or text) has enough context to generate a repair tutorial.
- **Researcher (`agents/researcher`)**: A worker agent that searches the web for repair information and reads technical documentation using MCP tools.
- **Judge (`agents/judge`)**: A worker agent that evaluates the quality and completeness of the research findings.
- **Content Builder (`agents/content_builder`)**: A worker agent that compiles the final repair tutorial, with images and a video link, from the approved research.
- **Web App (`app`)**: A FastAPI-based frontend and backend that provides a user interface to interact with the Orchestrator.
- **MCP Server (`mcp_server`)**: A Model Context Protocol server providing shared tools to the agents. **Note**: The `mcp_server` folder lives in the **root of the project**, not inside the `agents` folder.

> [!NOTE]
> Each agent, the MCP server, and the web app are **independent entities** built as microservices. They are designed to be started, tested, and deployed independently (e.g., to Google Cloud Run).

## MCP Tool Bindings

The MCP server exposes the following tools:

| Tool | Bound To | Purpose |
|---|---|---|
| `search_web` | Researcher | Searches the web via DuckDuckGo (no API key required) |
| `fetch_web_page_content` | Researcher | Scrapes a URL and returns its content as Markdown |
| `find_youtube_video` | Content Builder | Finds a relevant YouTube tutorial video URL |
| `fetch_stock_image` | Content Builder | Returns a AI-generated stock image URL for the tutorial |

> [!IMPORTANT]
> **Vertex AI Tool Compatibility**: Vertex AI's `generateContent` API does **not** support mixing its built-in search grounding tool (`google_search`) with custom function declarations (e.g., MCP tools) in the same request. To work around this constraint:
>
> - Web search capability was moved **into the MCP server** as the `search_web` tool (powered by `ddgs` / DuckDuckGo).
> - The Researcher agent now uses **only `McpToolset`** — a single homogeneous tool type — which is fully compatible with Vertex AI.
> - This design keeps all agents on Vertex AI and preserves the MCP-first architecture.

## Orchestration Logic
1. **Gating**: The Gatekeeper evaluates the input and returns `enough_context: true/false`.
2. **Research Loop**: The Orchestrator uses a `LoopAgent` to iterate between the **Researcher** and the **Judge**.
3. **Evaluation**: After each research step, the **Judge** provides feedback.
4. **Escalation**: An `EscalationChecker` breaks the loop if the Judge grants a "pass" or if the maximum iterations (3) are reached.
5. **Finalization**: The **Content Builder** takes the final research state and generates the tutorial with visuals and a video link.

## Local Execution
To run the project locally:
1. Ensure `uv` is installed.
2. Run `./run_local.sh` from the project root.
3. The services will start on the following ports:
   - Frontend: `http://localhost:8000`
   - Researcher: `http://localhost:8001`
   - Judge: `http://localhost:8002`
   - Content Builder: `http://localhost:8003`
   - Orchestrator: `http://localhost:8004`
   - Gatekeeper: `http://localhost:8005`
   - MCP Server: `http://localhost:8888`

## Note on Origin
> [!IMPORTANT]
> This project was copied from the **Google Cloud Console** and is being adapted for local development and testing.
