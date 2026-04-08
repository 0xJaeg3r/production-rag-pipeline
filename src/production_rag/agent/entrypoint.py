from production_rag.agent.rag_agent_with_class import RagAgent
#from production_rag.agent.rag_agent import create_rag_agent
from agno.os import AgentOS

rag = RagAgent()
agent_os = AgentOS(teams=[rag.rag_team])

#agent_os = AgentOS(agents=[create_rag_agent()])

app = agent_os.get_app()