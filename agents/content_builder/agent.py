# Objective: This file defines the content builder agent that compiles 
# final research into structured course modules.

from google.adk.agents import Agent

# Define the model version for content generation
MODEL = "gemini-2.5-pro"

# Define the Content Builder Agent
# This agent should take approved research and format it into a course module.
content_builder = Agent(
    name="content_builder",
    model=MODEL,
    description="Transforms research findings into a structured repair tutorial.",
    instruction="""
    You are the Expert Repair Guide Creator for ducktAIpe.
    Take the approved 'research_findings' and transform them into a well-structured, easy-to-follow repair tutorial.

    **Formatting Rules:**
    1. Start with a main title using a single `#` (H1).
    2. Include a "Safety Warning" section first if the repair has any risks.
    3. Use `##` (H2) for sections like "Required Tools," "Step-by-Step Instructions," and "Final Testing."
    4. Use bold text for tool names and key safety actions.
    5. Maintain a helpful, encouraging, and clear tone.

    Ensure the content is safe and directly addresses the user's broken object.
    """,
)
# Export the content builder as the root for this service
root_agent = content_builder