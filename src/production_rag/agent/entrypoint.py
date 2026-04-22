from production_rag.agent.rag_agent import RagAgent
#from production_rag.agent.rag_agent import create_rag_agent
from agno.os import AgentOS
from agno.os.interfaces.telegram import Telegram
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

rag = RagAgent()
agent_os = AgentOS(
    teams=[rag.rag_team],
    interfaces=[Telegram(team=rag.rag_team)],
    )

#agent_os = AgentOS(agents=[create_rag_agent()])

app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="production_rag.agent.entrypoint:app", port=7777, reload=True)