"""Agent factory — no module-level side effects."""

from agno.agent import Agent
from agno.tools.reasoning import ReasoningTools

from production_rag.agent.knowledge import create_knowledge_base
from production_rag.agent.prompts import AGENT_INSTRUCTIONS
from production_rag.integrations.mlflow import setup_mlflow, get_gateway_llm
from production_rag.config import llm as llm_cfg
from agno.models.openai import OpenAIChat

def create_rag_agent(autolog: bool = True) -> Agent:
    """Create and return the RAG agent.

    Nothing happens at import time — call this function to wire everything up.
    """
    setup_mlflow(autolog=autolog)
    kb = create_knowledge_base()
    #llm = get_gateway_llm("open-ai")
    "Use llm from your env variables"
    llm = OpenAIChat(id = llm_cfg.model_id, temperature = llm_cfg.temperature, api_key = llm_cfg.api_key)
    

    return Agent(
        description="Expert Financial Analyst",
        model=llm,
        tools=[ReasoningTools(add_instructions=True)],
        search_knowledge=True,
        debug_mode=True,
        knowledge=kb,
        enable_agentic_knowledge_filters=True,
        instructions=AGENT_INSTRUCTIONS,
    )
