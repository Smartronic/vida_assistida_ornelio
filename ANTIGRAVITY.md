# Oracle ILPI Ornélio / Vida Assistida

Este projeto é uma prova de conceito de um agente especializado no conteúdo do livro "Vida Assistida do Idoso e Seus Familiares – A Passagem pelo Túnel do Tempo", de Ornélio Dias de Moraes.

## Objetivo

Criar uma aplicação local com backend FastAPI, agente AGNO, base vetorial ChromaDB, memória SQLite e frontend React/Vite/TypeScript.

O agente deve responder prioritariamente com base no conteúdo do livro. Busca web só deve ser considerada em último caso, quando a resposta exigir informação atualizada ou externa.

## Stack

- Backend: FastAPI.
- Agente: AGNO.
- Embeddings: OpenAI text-embedding-3-small.
- Chat: modelo barato da OpenAI.
- Vetor: ChromaDB local.
- Sessões: SQLite.
- Frontend: React + Vite + TypeScript.
- Gerenciador Python: UV.

## Regras do agente

- Responder de forma humana, clara, objetiva e segura.
- Não repetir sempre frases como "com base no livro".
- Quando não houver contexto suficiente no livro, admitir com naturalidade.
- Em temas médicos, jurídicos ou clínicos, orientar consulta a profissionais qualificados.
- Manter tom acolhedor, confiável e prático.

## Próximas tarefas

1. Implementar ingestão do PDF.
2. Criar chunks do texto.
3. Gerar embeddings.
4. Salvar no ChromaDB.
5. Criar recuperação semântica.
6. Criar agente AGNO usando contexto recuperado.
7. Criar memória SQLite com resumo + últimas 3 mensagens.
8. Implementar streaming de resposta.
9. Melhorar UI minimalista.