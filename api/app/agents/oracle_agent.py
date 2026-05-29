import contextvars
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb

from app.config import settings

# Variável de contexto segura contra concorrência para coletar os chunks recuperados no RAG
retrieved_chunks_var: contextvars.ContextVar[list] = contextvars.ContextVar("retrieved_chunks", default=[])

def get_oracle_agent(session_id: str, instructions: str) -> Agent:
    """
    Retorna uma instância configurada do agente AGNO.
    Utiliza a persistência nativa do AGNO (SqliteDb), resumos automáticos
    da sessão e recebe as instruções dinamicamente pré-calculadas.
    """
    db = SqliteDb(db_file=settings.sqlite_path)
    
    return Agent(
        model=OpenAIChat(id=settings.openai_chat_model, api_key=settings.openai_api_key),
        db=db,
        session_id=session_id,
        instructions=instructions,
        read_chat_history=True,
        num_history_messages=15,
        add_history_to_context=True,
        enable_session_summaries=True,
        add_session_summary_to_context=True,
        markdown=True
    )
