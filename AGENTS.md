# AGENTS.md

## Project Overview
This project is a multi-agent course creation system built using Google's **Agent Development Kit (ADK)** and the **Agent-to-Agent (A2A)** protocol. It was originally copied from the Google Cloud Console and is configured for local execution and development.

## Project Structure
The application follows a distributed microservices architecture:

- **Orchestrator (`agents/orchestrator`)**: The master agent that coordinates the workflow. It uses a `SequentialAgent` to run a research loop followed by a content building phase.
- **Researcher (`agents/researcher`)**: A worker agent that uses Google Search to gather information on the requested topic.
- **Judge (`agents/judge`)**: A worker agent that evaluates the quality of the research findings.
- **Content Builder (`agents/content_builder`)**: A worker agent that compiles the final course content once the research is approved.
- **Web App (`app`)**: A FastAPI-based frontend and backend that provides a user interface to interact with the Orchestrator.

## Orchestration Logic
1. **Research Loop**: The Orchestrator uses a `LoopAgent` to iterate between the **Researcher** and the **Judge**.
2. **Evaluation**: After each research step, the **Judge** provides feedback.
3. **Escalation**: An `EscalationChecker` breaks the loop if the Judge grants a "pass" or if the maximum iterations (3) are reached.
4. **Finalization**: The **Content Builder** takes the final research state and generates the course.

## Local Execution
To run the project locally:
1. Ensure `uv` is installed.
2. Run `./run_local.sh`.
3. The services will start on the following ports:
   - Frontend: `http://localhost:8000`
   - Researcher: `http://localhost:8001`
   - Judge: `http://localhost:8002`
   - Content Builder: `http://localhost:8003`
   - Orchestrator: `http://localhost:8004`

## Note on Origin
> [!IMPORTANT]
> This project was copied from the **Google Cloud Console** and is being adapted for local development and testing.
