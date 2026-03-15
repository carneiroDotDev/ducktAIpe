# Objective: This file defines the master agent that coordinates the 
# multi agent workflow for repair tutorials.

import os
import json
import logging
from typing import AsyncGenerator
from google.adk.agents import BaseAgent, LoopAgent, SequentialAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext

# Import utility for authenticated communication
from authenticated_httpx import create_authenticated_client

logger = logging.getLogger(__name__)

# *** Callbacks Section ***

# Function to create callbacks that persist agent outputs to the session state
def create_save_output_callback(key: str):
    """Creates a callback to save the agent's final response to session state."""

    # Internal callback function invoked by the ADK framework
    def callback(callback_context: CallbackContext, **kwargs) -> None:
        # Capture the context of the current request
        ctx = callback_context

        # Iterate through session events in reverse to find the latest data
        for event in reversed(ctx.session.events):
            # Check if the event belongs to this agent and has content
            if event.author == ctx.agent_name and event.content and event.content.parts:
                # Extract the text component of the message
                text = event.content.parts[0].text
                if text:
                    # Special handling for judge feedback which is structured JSON
                    if key == "judge_feedback" and text.strip().startswith("{"):
                        try:
                            # Parse JSON string into a dictionary
                            ctx.state[key] = json.loads(text)
                        except json.JSONDecodeError:
                            # Fallback to raw text if parsing fails
                            ctx.state[key] = text
                    else:
                        # Store standard text outputs directly
                        ctx.state[key] = text

                    logger.info("Saved output to state['%s'] from agent '%s'", key, ctx.agent_name)
                    return
    return callback


def create_before_callback(step_label: str):
    """Creates a callback that logs when an agent step begins."""
    def callback(callback_context: CallbackContext, **kwargs) -> None:
        logger.info(">>> Step started: %s", step_label)
    return callback


# *** Remote Agents Section ***

# Define connections to remote agents
# Connect to Researcher, Judge, and Content Builder using RemoteA2aAgent.
# Remember to use the environment variables for URLs (or localhost defaults).

# Connect to the Gatekeeper (Localhost port 8005)
gatekeeper_url = os.environ.get("GATEKEEPER_AGENT_CARD_URL", "http://localhost:8005/a2a/agent/.well-known/agent-card.json")
gatekeeper = RemoteA2aAgent(
    name="gatekeeper",
    agent_card=gatekeeper_url,
    description="Evaluates context from the user.",
    before_agent_callback=create_before_callback("Gatekeeper: validating user input"),
    after_agent_callback=create_save_output_callback("gatekeeper_feedback"),
    httpx_client=create_authenticated_client(gatekeeper_url)
)

# Connect to the Researcher (Localhost port 8001)
researcher_url = os.environ.get("RESEARCHER_AGENT_CARD_URL", "http://localhost:8001/a2a/agent/.well-known/agent-card.json")
researcher = RemoteA2aAgent(
    name="researcher",
    agent_card=researcher_url,
    # IMPORTANT: Use authenticated client for communication
    description="Gathers information using web search.",
    before_agent_callback=create_before_callback("Researcher: searching and reading documentation"),
    after_agent_callback=create_save_output_callback("research_findings"),
    # IMPORTANT: Use authenticated client for communication
    httpx_client=create_authenticated_client(researcher_url)
)

# Connect to the Judge (Localhost port 8002)
judge_url = os.environ.get("JUDGE_AGENT_CARD_URL", "http://localhost:8002/a2a/agent/.well-known/agent-card.json")
judge = RemoteA2aAgent(
    name="judge",
    agent_card=judge_url,
    description="Evaluates research.",
    before_agent_callback=create_before_callback("Judge: evaluating research quality"),
    # IMPORTANT: callback after execution to save the feedback
    after_agent_callback=create_save_output_callback("judge_feedback"),
    # Attach identity tokens for secure service calls
    httpx_client=create_authenticated_client(judge_url)
)

# Content Builder (Localhost port 8003)
content_builder_url = os.environ.get("CONTENT_BUILDER_AGENT_CARD_URL", "http://localhost:8003/a2a/agent/.well-known/agent-card.json")
content_builder = RemoteA2aAgent(
    name="content_builder",
    agent_card=content_builder_url,
    description="Builds the tutorial.",
    before_agent_callback=create_before_callback("Content Builder: assembling tutorial with images and video"),
    httpx_client=create_authenticated_client(content_builder_url)
)

# --- Escalation Checker ---

# This agent should check the status of the judge's feedback.
# If status is "pass", it should escalate (break the loop).

class EscalationChecker(BaseAgent):
    """Checks the judge's feedback and escalates (breaks the loop) if it passed."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # Retrieve the feedback saved by the Judge
        feedback = ctx.session.state.get("judge_feedback")
        logger.info("Judge feedback received: %s", feedback)

        # Check for 'pass' status
        is_pass = False
        if isinstance(feedback, dict) and feedback.get("status") == "pass":
            is_pass = True
        # Handle string fallback if JSON parsing failed
        elif isinstance(feedback, str) and '"status": "pass"' in feedback:
            is_pass = True

        if is_pass:
            # 'escalate=True' tells the parent LoopAgent to stop looping
            logger.info(">>> Judge verdict: PASS — research approved, exiting loop")
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            # Otherwise, continue the loop
            logger.info(">>> Judge verdict: FAIL — looping back for another research iteration")
            yield Event(author=self.name)

# Instantiate the checker agent
escalation_checker = EscalationChecker(name="escalation_checker")

class GatekeeperChecker(BaseAgent):
    """Checks the gatekeeper's feedback and stops the pipeline if there is not enough context."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # Retrieve the feedback saved by the Gatekeeper
        feedback = ctx.session.state.get("gatekeeper_feedback")
        logger.info("Gatekeeper feedback received: %s", feedback)

        # Check if enough_context is false
        has_context = False
        if isinstance(feedback, dict) and feedback.get("enough_context") is True:
            has_context = True
        elif isinstance(feedback, str) and '"enough_context": true' in feedback.lower():
            has_context = True

        if not has_context:
            # 'escalate=True' tells the parent LoopAgent to stop looping
            logger.info(">>> Gatekeeper verdict: NOT ENOUGH CONTEXT — aborting pipeline")
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            # Otherwise, continue the loop
            logger.info(">>> Gatekeeper verdict: CONTEXT OK — proceeding to research")
            yield Event(author=self.name)

# Instantiate the gatekeeper checker
gatekeeper_checker = GatekeeperChecker(name="gatekeeper_checker")

class TopicEnricher(BaseAgent):
    """Enriches the user's prompt with the object recognized by the gatekeeper."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # Retrieve the recognized object from the Gatekeeper
        feedback = ctx.session.state.get("gatekeeper_feedback")

        recognized_object = "this item"
        if isinstance(feedback, dict) and feedback.get("recognized_object"):
            recognized_object = feedback.get("recognized_object")
        
        # We don't yield a message to the UI here, we just want to ensure
        # the model knows what object we are talking about.
        # But we can yield an event to provide context for the models in the loop.
        logger.info(">>> Topic enriched: '%s'", recognized_object)
        enrichment_msg = f"\n[Context: The object to fix is a {recognized_object}.]"
        yield Event(author=self.name, content={"parts": [{"text": enrichment_msg}]})

# Instantiate the topic enricher
topic_enricher = TopicEnricher(name="topic_enricher")

# *** Orchestration Section ***
# Defines the multi agent workflow logic
# Research loop that runs the search and evaluation cycle
research_loop = LoopAgent(
    name="research_loop",
    description="Iteratively researches and judges until quality standards are met.",
    # Sub agents involved in the loop
    sub_agents=[researcher, judge, escalation_checker],
    # Maximum number of attempts allowed
    max_iterations=3,
)

# Root Agent (Pipeline)
# Use SequentialAgent to run the Research Loop followed by the Content Builder.
root_agent = SequentialAgent(
    name="repair_tutorial_pipeline",
    description="A pipeline that identifies a broken object, researches how to fix it, and builds a guide.",
    # Sub agents executed in order
    sub_agents=[gatekeeper, gatekeeper_checker, topic_enricher, research_loop, content_builder],
)
