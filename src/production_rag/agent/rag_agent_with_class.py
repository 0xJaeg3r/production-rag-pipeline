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
from agno.db.sqlite import SqliteDb
from pathlib import Path
from agno.memory import MemoryManager
from agno.models.openai import OpenAIResponses
from agno.models.deepseek import DeepSeek
from agno.models.anthropic import Claude
from agno.tools.visualization import VisualizationTools
from agno.team.team import Team
from agno.team.mode import TeamMode
from agno.tools.knowledge import KnowledgeTools
from agno.db.postgres import AsyncPostgresDb
import uuid

from production_rag.agent.promptsV2 import *

load_dotenv(find_dotenv())

RAG_DIR = Path(os.environ["RAG_DATA_DIR"])
RAG_DIR.mkdir(exist_ok=True)

db_url = os.environ["DATABASE_URL"]

class RagAgent:
    """
    Complete RAG agent for Bank of Ghana Financial Analysis
    """

    def __init__(
            self,
            model_name: str = "gpt-5.2",
            evaluation: bool = False,
            use_memory: bool = True,
            use_storage: bool = True,


    ):
        
        self.model_name = model_name
        self.model = self._get_model(model_name)
        self.evaluation = evaluation
        self.use_memory = use_memory
        self.use_storage = use_storage


        
        if self.evaluation:
            setup_mlflow(autolog=True)

        self.db = None
        self.memory_manager = None
        if use_storage or use_memory:
            # self.db = SqliteDb(db_file=str(RAG_DIR / "rag_agent.db"))
            self.db = AsyncPostgresDb(db_url=db_url, db_schema="agent")

        if use_memory:
            self.memory_manager = MemoryManager(
                model=OpenAIResponses(self.model_name),
                db=self.db,
            )    

#Initialize all tools 
        
#Initialize knowledgebase
        self.knowledgebase = self._create_knowledgebase()

        self._create_all_agents()
        self._create_rag_team()

        

    def _get_model(self, model_id: str):
        """
        Gets model based on model id
        """
        if "claude" in model_id.lower():
            return Claude(id=model_id)
        elif "deepseek" in model_id.lower():
            return DeepSeek(id=model_id)
        elif "gpt" in model_id.lower() or "o1" in model_id.lower(
        ) or "o3" in model_id.lower():
            return OpenAIChat(id=model_id)
        else:
            try:
                from agno.models.litellm import LiteLLM
                return LiteLLM(id=model_id, name="LiteLLM")
            except ImportError:
                #Fallback to OpenAI
                return OpenAIChat(id=model_id)
            
    def _create_knowledgebase(self):
        kb = create_knowledge_base()
        return kb
    

    
    def _create_all_agents(self):
        """
        Create specialized agents
        """

        agent_kwargs = {
            "model": self.model,
        }

        if self.db:
            agent_kwargs["db"] = self.db
            agent_kwargs["add_history_to_context"] = True

        if self.memory_manager:
            agent_kwargs["enable_user_memories"] = True
            agent_kwargs["memory_manager"] = self.memory_manager
            agent_kwargs["enable_agentic_memory"] = True




        self.financial_analyst_agent = Agent(
            name="Financial Analyst Agent",
            role="Financial Analyst",
            instructions = [FINANCIAL_ANALYST_AGENT],
            knowledge= self.knowledgebase,
            enable_agentic_knowledge_filters=True,
            search_knowledge=True,
            tools=[ReasoningTools(add_instructions=True)],
            **agent_kwargs

        )


        self.chart_agent = Agent(
            name="Chart Agent",
            role="Visualization specialist.",
            instructions = [CHART_AGENT],
            knowledge=self.knowledgebase,
            enable_agentic_knowledge_filters=True,
            search_knowledge=True,
            tools=[VisualizationTools(), ReasoningTools(add_instructions=True)],
            **agent_kwargs

        )

    



    def _create_rag_team(self):
        """
        
        """
        self.session_id = str(uuid.uuid4())

        # Team configuration
        team_kwargs = {
            "name": "Financial Analyst Team",
            "mode": TeamMode.coordinate,
            "model": self.model,
            "respond_directly": False,
            "members": [
                self.chart_agent,
                self.financial_analyst_agent
               
            ],
            "markdown": True,
            "instructions": [FINANCIAL_AGENT_MANAGER_PROMPT],
            "show_members_responses": True,
            "share_member_interactions": True,
            "add_history_to_context": True,
            "debug_mode": True,
            "debug_level": 2,


        }

        if self.db:
            team_kwargs["db"] = self.db
        if self.memory_manager:
            team_kwargs["enable_user_memories"] = True
        
        self.rag_team = Team(**team_kwargs)

    def perform_rag_analysis(self, task: str, stream: bool = True,
                             show_full_reasoning: bool = True, stream_events: bool = True):
        
        """
        
        """
        
        self.rag_team.print_response(
            task,
            stream=stream,
            session_id=self.session_id,
            show_full_reasoning=show_full_reasoning,
            stream_events=stream_events,
        )
