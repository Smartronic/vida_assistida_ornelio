import json
import re
import asyncio
from app.rag.retriever import query_book
from app.agents.oracle_agent import get_oracle_agent, retrieved_chunks_var
import app.agents.prompts as prompts

def clean_agent_response(text: str) -> str:
    """
    Remove qualquer ocorrência acidental da diretriz de confiança do RAG
    da resposta final de texto que é enviada ao usuário.
    """
    # Remove marcas como [DIRETRIZ DE CONFIANÇA DO RAG: ...]
    cleaned = re.sub(r'\s*\[DIRETRIZ DE CONFIANÇA DO RAG:\s*\w+\]\s*', '\n\n', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()

def process_chat_message(session_id: str, message: str, debug: bool = False) -> tuple[str, dict | None]:
    """
    Processa a mensagem do usuário utilizando o AGNO, RAG e política de confiança.
    Retorna uma tupla (resposta, informacao_de_debug).
    """
    retrieved_chunks_var.set([])
    
    try:
        # 1. Busca trechos no RAG primeiro
        chunks = query_book(message, n_results=5)
        retrieved_chunks_var.set(chunks)
        
        # 2. Avalia nível de confiança
        if chunks:
            best_distance = min(chunk.get("distance", 1.0) for chunk in chunks)
        else:
            best_distance = 1.0
            
        if best_distance < 0.60:
            confidence_instruction = (
                "[DIRETRIZ DE CONFIANÇA DO RAG: ALTA]\n"
                "A busca semântica retornou dados altamente relevantes com score de distância excelente (baixo). "
                "Responda à pergunta do usuário de forma confiante, direta e precisa, baseando-se nos trechos recuperados."
            )
        elif best_distance < 0.78:
            confidence_instruction = (
                "[DIRETRIZ DE CONFIANÇA DO RAG: MÉDIA]\n"
                "A busca semântica retornou relevância moderada (distância média). "
                "No entanto, isso não significa ausência de informação. Antes de declarar que o material não detalha ou não traz o assunto, verifique atentamente se há elementos concretos ou diretrizes úteis nos trechos. "
                "Se houver trechos ou elementos úteis, responda de forma parcial e cautelosa com expressões como 'O material recuperado indica...', 'Pelos trechos disponíveis, é possível afirmar...' ou 'A orientação central apresentada é...', indicando o limite com naturalidade. Não negue a existência do conteúdo recuperado. "
                "Se e somente se não houver dados relevantes nos trechos, informe de forma acolhedora que o livro não detalha o tema e ofereça orientações gerais e seguras."
            )
        else:
            confidence_instruction = (
                "[DIRETRIZ DE CONFIANÇA DO RAG: BAIXA]\n"
                "A busca semântica retornou um score de distância matemática alto (baixa similaridade). "
                "No entanto, isso não significa ausência de informação. Antes de declarar que o material não traz informações detalhadas, você DEVE analisar se os trechos contêm elementos ou diretrizes úteis sobre a pergunta. "
                "Se houver trechos ou elementos úteis, responda de forma parcial e muito cautelosa (ex.: 'O material recuperado indica...', 'Pelos trechos disponíveis...', 'A orientação central apresentada é...'), indicando o limite com naturalidade. Não negue a existência de conteúdo quando houver trechos úteis recuperados. "
                "Se não houver nenhuma informação sobre o assunto nos trechos, informe de forma acolhedora que o livro não detalha este tema e dê apenas orientações seguras e gerais."
            )
            
        # 3. Compila trechos do RAG
        context_parts = []
        for chunk in chunks:
            page = chunk["metadata"].get("page", "desconhecida")
            content = chunk["content"]
            context_parts.append(f"[Trecho da Página {page}]: {content}")
            
        # 4. Constrói instrução combinada
        base_prompt = prompts.__doc__ or "Você é o assistente Vida Assistida."
        context_text = "\n".join(context_parts)
        if debug:
            mode_instruction = (
                "[INSTRUÇÃO DE MODO DE AVALIAÇÃO/DEBUG ATIVO]\n"
                "Você está rodando no modo de depuração/bateria de testes automáticos. "
                "Para certificar a fidelidade do RAG, você PODE e DEVE usar expressões explícitas como "
                "'Pelos trechos disponíveis...', 'O material indica...', 'Segundo o livro do Professor...', etc., "
                "conforme descrito nas diretrizes do MODO DE AVALIAÇÃO/DEBUG."
            )
        else:
            mode_instruction = (
                "[INSTRUÇÃO DE MODO CONVERSA NORMAL ATIVO]\n"
                "Você está conversando diretamente com um usuário final na interface pública. "
                "Você NÃO deve citar o livro do Professor Ornélio, trechos do livro, RAG, base vetorial ou distância semântica na sua resposta, a menos que o usuário peça fontes explicitamente. "
                "Siga rigorosamente as diretrizes do MODO NORMAL no prompt do sistema: use aberturas naturais, consultivas e acolhedoras (como 'Essa decisão depende de alguns fatores...', 'Vamos organizar essa escolha por partes...', etc.), e forneça as informações de forma integrada à sua própria sabedoria."
            )
        combined_instructions = (
            f"{base_prompt}\n\n"
            f"{mode_instruction}\n\n"
            f"{confidence_instruction}\n\n"
            f"### CONTEXTO RECUPERADO DO LIVRO:\n"
            f"{context_text}"
        )
        
        # 5. Instancia agente com instruções do sistema contendo o RAG
        agent = get_oracle_agent(session_id, combined_instructions)
        response = agent.run(message)
        answer = response.content
        
        # 6. Limpeza final preventiva na resposta pública
        answer = clean_agent_response(answer)
        
        debug_info = None
        if debug:
            pages = sorted(list(set(
                chunk["metadata"].get("page")
                for chunk in chunks 
                if chunk.get("metadata") and "page" in chunk["metadata"]
            )))
            debug_info = {
                "chunks_count": len(chunks),
                "pages": pages,
                "scores": [chunk.get("distance", 0.0) for chunk in chunks],
                "previews": [chunk.get("content", "") for chunk in chunks]
            }
            
        return answer, debug_info
        
    except Exception as e:
        print(f"[Erro Serviço] Falha ao processar mensagem do chat: {e}")
        error_msg = (
            "Desculpe, ocorreu um erro interno ao processar sua pergunta. "
            "Certifique-se de que a API da OpenAI esteja acessível."
        )
        return error_msg, None

def generate_chat_stream(session_id: str, message: str, debug: bool = False):
    """
    Gerador de streaming em formato NDJSON (JSON por linha).
    Envia blocos progressivos de texto (tokens) do oráculo Vida Assistida.
    """
    retrieved_chunks_var.set([])
    
    try:
        # 1. Busca trechos no RAG primeiro
        chunks = query_book(message, n_results=5)
        retrieved_chunks_var.set(chunks)
        
        # 2. Avalia nível de confiança
        if chunks:
            best_distance = min(chunk.get("distance", 1.0) for chunk in chunks)
        else:
            best_distance = 1.0
            
        if best_distance < 0.60:
            confidence_instruction = (
                "[DIRETRIZ DE CONFIANÇA DO RAG: ALTA]\n"
                "A busca semântica retornou dados altamente relevantes com score de distância excelente (baixo). "
                "Responda à pergunta do usuário de forma confiante, direta e precisa, baseando-se nos trechos recuperados."
            )
        elif best_distance < 0.78:
            confidence_instruction = (
                "[DIRETRIZ DE CONFIANÇA DO RAG: MÉDIA]\n"
                "A busca semântica retornou relevância moderada (distância média). "
                "No entanto, isso não significa ausência de informação. Antes de declarar que o material não detalha ou não traz o assunto, verifique atentamente se há elementos concretos ou diretrizes úteis nos trechos. "
                "Se houver trechos ou elementos úteis, responda de forma parcial e cautelosa com expressões como 'O material recuperado indica...', 'Pelos trechos disponíveis, é possível afirmar...' ou 'A orientação central apresentada é...', indicando o limite com naturalidade. Não negue a existência do conteúdo recuperado. "
                "Se e somente se não houver dados relevantes nos trechos, informe de forma acolhedora que o livro não detalha o tema e ofereça orientações gerais e seguras."
            )
        else:
            confidence_instruction = (
                "[DIRETRIZ DE CONFIANÇA DO RAG: BAIXA]\n"
                "A busca semântica retornou um score de distância matemática alto (baixa similaridade). "
                "No entanto, isso não significa ausência de informação. Antes de declarar que o material não traz informações detalhadas, você DEVE analisar se os trechos contêm elementos ou diretrizes úteis sobre a pergunta. "
                "Se houver trechos ou elementos úteis, responda de forma parcial e muito cautelosa (ex.: 'O material recuperado indica...', 'Pelos trechos disponíveis...', 'A orientação central apresentada é...'), indicando o limite com naturalidade. Não negue a existência de conteúdo quando houver trechos úteis recuperados. "
                "Se não houver nenhuma informação sobre o assunto nos trechos, informe de forma acolhedora que o livro não detalha este tema e dê apenas orientações seguras e gerais."
            )
            
        # 3. Compila trechos do RAG
        context_parts = []
        for chunk in chunks:
            page = chunk["metadata"].get("page", "desconhecida")
            content = chunk["content"]
            context_parts.append(f"[Trecho da Página {page}]: {content}")
            
        # 4. Constrói instrução combinada
        base_prompt = prompts.__doc__ or "Você é o assistente Vida Assistida."
        context_text = "\n".join(context_parts)
        if debug:
            mode_instruction = (
                "[INSTRUÇÃO DE MODO DE AVALIAÇÃO/DEBUG ATIVO]\n"
                "Você está rodando no modo de depuração/bateria de testes automáticos. "
                "Para certificar a fidelidade do RAG, você PODE e DEVE usar expressões explícitas como "
                "'Pelos trechos disponíveis...', 'O material indica...', 'Segundo o livro do Professor...', etc., "
                "conforme descrito nas diretrizes do MODO DE AVALIAÇÃO/DEBUG."
            )
        else:
            mode_instruction = (
                "[INSTRUÇÃO DE MODO CONVERSA NORMAL ATIVO]\n"
                "Você está conversando diretamente com um usuário final na interface pública. "
                "Você NÃO deve citar o livro do Professor Ornélio, trechos do livro, RAG, base vetorial ou distância semântica na sua resposta, a menos que o usuário peça fontes explicitamente. "
                "Siga rigorosamente as diretrizes do MODO NORMAL no prompt do sistema: use aberturas naturais, consultivas e acolhedoras (como 'Essa decisão depende de alguns fatores...', 'Vamos organizar essa escolha por partes...', etc.), e forneça as informações de forma integrada à sua própria sabedoria."
            )
        combined_instructions = (
            f"{base_prompt}\n\n"
            f"{mode_instruction}\n\n"
            f"{confidence_instruction}\n\n"
            f"### CONTEXTO RECUPERADO DO LIVRO:\n"
            f"{context_text}"
        )
        
        # 5. Instancia agente com instruções do sistema
        agent = get_oracle_agent(session_id, combined_instructions)
        response_stream = agent.run(message, stream=True)
        
        # 6. Iterar e transmitir os tokens gerados
        for chunk in response_stream:
            if chunk.__class__.__name__ == "RunContentEvent":
                content = getattr(chunk, "content", None)
                if content:
                    yield json.dumps({"token": content}) + "\n"
                
        # 7. Transmitir informações de depuração no final, se solicitado
        if debug:
            pages = sorted(list(set(
                chunk["metadata"].get("page")
                for chunk in chunks 
                if chunk.get("metadata") and "page" in chunk["metadata"]
            )))
            debug_info = {
                "chunks_count": len(chunks),
                "pages": pages,
                "scores": [chunk.get("distance", 0.0) for chunk in chunks],
                "previews": [chunk.get("content", "") for chunk in chunks]
            }
            yield json.dumps({"debug": debug_info}) + "\n"
            
    except (asyncio.CancelledError, GeneratorExit):
        print(f"[Streaming] Conexão cancelada silenciosamente pelo cliente para a sessão: {session_id}")
        raise
    except Exception as e:
        print(f"[Erro Streaming] Ocorreu uma falha no stream: {e}")
        yield json.dumps({
            "token": "\n\n[Erro de Conexão] Desculpe, a geração foi interrompida devido a uma instabilidade temporária na API da OpenAI."
        }) + "\n"
