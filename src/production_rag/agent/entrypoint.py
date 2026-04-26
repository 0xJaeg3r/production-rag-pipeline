#from production_rag.agent.rag_agent import RagAgent
from production_rag.agent.rag_agent import RagAgent
from agno.os import AgentOS
#from agno.os.interfaces.telegram import Telegram
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

rag_agent = RagAgent()

agent_os = AgentOS(teams=[rag_agent.rag_team], db=rag_agent.db)

app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="production_rag.agent.entrypoint:app", port=7777, reload=False)
