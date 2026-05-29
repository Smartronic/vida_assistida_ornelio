import os
import re
import sys
import pypdf
import chromadb
from chromadb.utils import embedding_functions

from app.config import settings

def clean_text(text: str) -> str:
    """Sanitiza o texto removendo quebras de linha e espaços extras."""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Divide o texto em chunks sem quebrar palavras no meio."""
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        # +1 para contar o espaço
        word_len = len(word) + 1
        if current_length + word_len > chunk_size:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            
            # Reconstrói os elementos de overlap com base nas últimas palavras do chunk atual
            overlap_words = []
            overlap_len = 0
            for w in reversed(current_chunk):
                if overlap_len + len(w) + 1 > overlap:
                    break
                overlap_words.insert(0, w)
                overlap_len += len(w) + 1
            
            current_chunk = overlap_words + [word]
            current_length = sum(len(w) + 1 for w in current_chunk)
        else:
            current_chunk.append(word)
            current_length += word_len
            
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

def ingest_pdf():
    print("=== Iniciando o Pipeline de Ingestão ===")
    
    # 1. Validar Chave da OpenAI
    if not settings.openai_api_key or settings.openai_api_key == "sua_chave_aqui":
        print("[ERRO] A variável OPENAI_API_KEY não está configurada no seu arquivo .env.")
        print("Por favor, adicione uma chave da OpenAI válida e execute novamente.")
        sys.exit(1)
        
    pdf_path = settings.pdf_path
    
    # 2. Verificar existência do PDF
    if not os.path.exists(pdf_path):
        # Se estiver rodando do diretório raiz da API, pode ser relativo. 
        # Vamos verificar se o caminho absoluto existe
        abs_pdf_path = os.path.abspath(pdf_path)
        if not os.path.exists(abs_pdf_path):
            print(f"[ERRO] O arquivo PDF não foi encontrado no caminho: {pdf_path}")
            print(f"Caminho absoluto tentado: {abs_pdf_path}")
            sys.exit(1)
        pdf_path = abs_pdf_path

    print(f"Lendo o arquivo PDF: {pdf_path}")
    
    # 3. Ler o PDF e extrair texto
    try:
        reader = pypdf.PdfReader(pdf_path)
        total_pages = len(reader.pages)
        print(f"Total de páginas no PDF: {total_pages}")
    except Exception as e:
        print(f"[ERRO] Falha ao ler o PDF: {e}")
        sys.exit(1)
        
    documents = []
    metadatas = []
    ids = []
    
    print("Processando páginas e gerando chunks...")
    for page_idx in range(total_pages):
        page = reader.pages[page_idx]
        raw_text = page.extract_text()
        if not raw_text:
            continue
            
        cleaned_text = clean_text(raw_text)
        if not cleaned_text:
            continue
            
        page_chunks = chunk_text(cleaned_text, chunk_size=1000, overlap=150)
        
        for i, chunk in enumerate(page_chunks):
            documents.append(chunk)
            metadatas.append({
                "page": page_idx + 1,
                "chunk_idx": i,
                "source": os.path.basename(pdf_path)
            })
            ids.append(f"page_{page_idx + 1}_chunk_{i}")
            
    print(f"Gerados {len(documents)} chunks de texto das {total_pages} páginas.")

    # 4. Configurar ChromaDB
    print(f"Inicializando ChromaDB local em: {settings.chroma_path}")
    try:
        # Garantir que o diretório pai do chroma existe
        chroma_dir = os.path.dirname(settings.chroma_path)
        if chroma_dir:
            os.makedirs(chroma_dir, exist_ok=True)
            
        client = chromadb.PersistentClient(path=settings.chroma_path)
        
        # Configurar embedding da OpenAI
        openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key,
            model_name=settings.openai_embedding_model
        )
        
        # 5. Criar/Sobrescrever coleção
        collection_name = "vida_assistida"
        try:
            client.delete_collection(name=collection_name)
            print(f"Coleção antiga '{collection_name}' removida.")
        except Exception:
            # A coleção não existia, normal
            pass
            
        collection = client.create_collection(
            name=collection_name,
            embedding_function=openai_ef
        )
    except Exception as e:
        print(f"[ERRO] Falha ao configurar o ChromaDB: {e}")
        sys.exit(1)

    # 6. Salvar no ChromaDB em lotes (Chroma suporta inserções em lotes)
    print("Enviando chunks para o ChromaDB (isso pode levar alguns instantes devido à geração dos embeddings)...")
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i + batch_size]
        batch_metas = metadatas[i:i + batch_size]
        batch_ids = ids[i:i + batch_size]
        
        try:
            collection.add(
                documents=batch_docs,
                metadatas=batch_metas,
                ids=batch_ids
            )
            print(f"Inseridos chunks {i} a {min(i + batch_size, len(documents))}...")
        except Exception as e:
            print(f"[ERRO] Falha ao inserir lote no ChromaDB: {e}")
            sys.exit(1)

    print("=== Ingestão concluída com sucesso! ===")
    print(f"Banco vetorial criado/atualizado com {len(documents)} documentos.")

if __name__ == "__main__":
    ingest_pdf()
