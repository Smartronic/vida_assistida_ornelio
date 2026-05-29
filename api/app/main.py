from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.services.chat_service import process_chat_message


app = FastAPI(
    title="Vida Assistida API",
    description="API do oráculo especializado no livro do Professor Ornélio.",
    version="0.1.0",
)

origins = [origin.strip() for origin in settings.allowed_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from typing import Optional

class ChatRequest(BaseModel):
    session_id: str
    message: str
    debug: bool = False


class ChatResponse(BaseModel):
    answer: str
    debug: Optional[dict] = None


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    answer, debug_info = process_chat_message(
        request.session_id, 
        request.message, 
        request.debug
    )
    return ChatResponse(answer=answer, debug=debug_info)


from fastapi.responses import StreamingResponse
from app.services.chat_service import generate_chat_stream

@app.post("/api/chat/stream")
def chat_stream(request: ChatRequest):
    generator = generate_chat_stream(
        request.session_id, 
        request.message, 
        request.debug
    )
    return StreamingResponse(generator, media_type="application/x-ndjson")


# Servir arquivos estáticos do frontend caso configurado (SERVE_FRONTEND=True)
if settings.serve_frontend:
    from pathlib import Path
    from fastapi.responses import FileResponse
    from fastapi import HTTPException

    # Obter o caminho absoluto do build do frontend (web/dist)
    BASE_DIR = Path(__file__).resolve().parent.parent # pasta api
    FRONTEND_DIR = (BASE_DIR.parent / "web" / "dist").resolve()

    # Validar no startup se o diretório existe
    if not FRONTEND_DIR.exists():
        print("\n" + "="*80)
        print(f"ERRO DE CONFIGURAÇÃO: O diretório de build do frontend não foi encontrado em: {FRONTEND_DIR}")
        print("Como SERVE_FRONTEND=True está ativado, você precisa gerar o build primeiro:")
        print("    cd ../web && npm run build")
        print("="*80 + "\n")
        raise RuntimeError(
            f"Pasta de build do frontend não encontrada em: {FRONTEND_DIR}. Execute 'cd ../web && npm run build' primeiro."
        )

    # Rota catch-all para arquivos estáticos e fallback SPA
    @app.get("/{catchall:path}")
    def serve_frontend(catchall: str):
        # Não interceptar rotas que começam com api/
        if catchall.startswith("api"):
            raise HTTPException(status_code=404, detail="API route not found")

        # Verificar se o arquivo estático correspondente existe em dist
        file_path = FRONTEND_DIR / catchall
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)

        # Fallback SPA para index.html
        return FileResponse(FRONTEND_DIR / "index.html")