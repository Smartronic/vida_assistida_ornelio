import chromadb
from chromadb.utils import embedding_functions

from app.config import settings

def query_book(query_text: str, n_results: int = 5) -> list[dict]:
    """
    Busca os trechos mais relevantes do livro com base em uma consulta semântica.
    """
    if not settings.openai_api_key or settings.openai_api_key == "sua_chave_aqui":
        raise ValueError("OPENAI_API_KEY não configurada no .env.")

    # Inicializar cliente ChromaDB
    client = chromadb.PersistentClient(path=settings.chroma_path)
    
    # Configurar embedding da OpenAI
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=settings.openai_api_key,
        model_name=settings.openai_embedding_model
    )
    
    # Obter a coleção
    collection = client.get_collection(
        name="vida_assistida",
        embedding_function=openai_ef
    )
    
    # Realizar a consulta
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results
    )
    
    # Formatar o retorno
    formatted_results = []
    if results and "documents" in results and results["documents"]:
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)
        ids = results["ids"][0]
        
        for idx in range(len(docs)):
            formatted_results.append({
                "id": ids[idx],
                "content": docs[idx],
                "metadata": metas[idx],
                "distance": distances[idx]
            })
            
    return formatted_results

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: uv run python -m app.rag.retriever 'Sua pergunta aqui'")
        sys.exit(0)
        
    query = sys.argv[1]
    print(f"Buscando por: '{query}'...")
    try:
        res = query_book(query)
        print(f"\nResultados encontrados ({len(res)}):")
        for i, item in enumerate(res):
            print(f"\n--- Resultado {i+1} (Página {item['metadata']['page']}, Distância: {item['distance']:.4f}) ---")
            print(item["content"])
    except Exception as e:
        print(f"Erro ao buscar: {e}")
