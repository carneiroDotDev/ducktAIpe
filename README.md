# 🦆 ducktAIpe

<p align="center">
  <img src="app/frontend/logo.png" alt="ducktAIpe Logo" width="300">
</p>

[![Live Demo](https://img.shields.io/badge/Live%20Demo-ducktAIpe-FFD700?style=for-the-badge&logo=google-cloud&logoColor=white)](https://ducktaipe-frontend-979138472410.us-central1.run.app/)

**ducktAIpe** is a multi-agent repair tutorial generator that takes your "uh-oh" moments and turns them into "I fixed it!" guides. Whether it's a cracked phone screen or a leaky faucet, our team of specialized AI agents works together to find the best documentation, verify its quality, and build a beautiful step-by-step tutorial for you.

Built with Google's **Agent Development Kit (ADK)** and the **Agent-to-Agent (A2A)** protocol, this project showcases a distributed microservices architecture where each agent has a specific job.

---

## 🛠 How it Works (The Workflow)

When you ask for a repair guide, our "Duck" starts a coordinated pipeline:

1.  **🚪 Gatekeeper**: The bouncer of the system. It checks your input (text or image) to ensure there's enough context to actually help.
2.  **🔍 Researcher**: The librarian. Using DuckDuckGo and technical scraping, it gathers real-world repair data from across the web.
3.  **⚖️ Judge**: The quality control expert. It reviews the research and decides if it's "gold standard" or needs another pass.
4.  **🦆 Content Builder**: The storyteller. It takes the approved research and compiles a tutorial with images, clear steps, and even a relevant YouTube video.
5.  **🎭 Orchestrator**: The conductor. It coordinates the entire flow, making sure every agent plays its part at the right time.

---

## 🚀 Getting Started

### Prerequisites

*   **[uv](https://docs.astral.sh/uv/)**: Our preferred Python package manager.
*   **Google Cloud Project**: To use Vertex AI (Gemini).
*   **gcloud CLI**: Logged in and configured to your project.

### Local Setup

1.  **Initialize the project**:
    ```bash
    ./init.sh
    ```

2.  **Run everything**:
    ```bash
    ./run_local.sh
    ```
    This script will fire up all 6 agents and the MCP server. Once it's running, head over to:
    👉 **[http://localhost:8000](http://localhost:8000)**

---

## 🧪 Testing

We have a few ways to make sure the "Duck" is in tip-top shape:

*   **MCP Server Test**: Check if the tools (search, image fetching, etc.) are working:
    ```bash
    uv run test_mcp.py
    ```
*   **Individual Agents**: Each agent is an independent service. You can run them separately by heading into their directory (e.g., `agents/researcher`) and running `uv run adk_app.py`.
*   **The Frontend**: The easiest way to test is to use the UI and watch the logs in your terminal as the agents talk to each other.

---

## 🏗 Architecture & Tech Stack

*   **Core Logic**: Python + Google ADK + A2A SDK.
*   **AI Models**: Gemini (via Vertex AI).
*   **Microservices**: FastAPI.
*   **Server Communication**: Model Context Protocol (MCP) for tool sharing.
*   **Deployment**: containerized services running on Google Cloud Run.

---

## ☁️ Deployment

If you want to deploy your own version of ducktAIpe:
```bash
./deploy.sh
```
This will push all services to Cloud Run and wire them up automatically.

---

*Made with ❤️ and a lot of 🦆 by the ducktAIpe team.*

*I'm kidding its solo dev thing: carneiro.dev/about*