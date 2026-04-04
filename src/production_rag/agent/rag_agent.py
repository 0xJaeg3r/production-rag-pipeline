"""Agent factory — no module-level side effects."""

from agno.agent import Agent
from agno.tools.reasoning import ReasoningTools

from production_rag.agent.knowledge import create_knowledge_base
from production_rag.agent.prompts import AGENT_INSTRUCTIONS
import os

from dotenv import load_dotenv, find_dotenv

from production_rag.integrations.mlflow import setup_mlflow, get_gateway_llm
from production_rag.agent.config.config_loader import llm
from agno.models.openai import OpenAIChat

load_dotenv(find_dotenv())

def create_rag_agent(autolog: bool = True) -> Agent:
    """Create and return the RAG agent.

    Nothing happens at import time — call this function to wire everything up.
    """
    setup_mlflow(autolog=autolog)
    kb = create_knowledge_base()
    #llm = get_gateway_llm("open-ai")
    "Use llm from your env variables"
    llm_client = OpenAIChat(id=llm["model_id"], temperature=llm["temperature"], api_key=os.environ["OPENAI_API_KEY"])
    

    return Agent(
        description="Expert Financial Analyst",
        model=llm_client,
        tools=[ReasoningTools(add_instructions=True)],
        search_knowledge=True,
        debug_mode=True,
        knowledge=kb,
        enable_agentic_knowledge_filters=True,
        instructions=AGENT_INSTRUCTIONS,
    )
