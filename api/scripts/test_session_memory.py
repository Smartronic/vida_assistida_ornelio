import json
import urllib.request
import urllib.error
import uuid
import sys

API_URL = "http://127.0.0.1:8000/chat"

def query_chat(session_id: str, message: str) -> str:
    payload = {
        "session_id": session_id,
        "message": message,
        "debug": False
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data.get("answer", "")
    except urllib.error.URLError as e:
        print(f"[ERRO] Falha ao conectar na API local na porta 8000: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERRO] Falha no processamento: {e}")
        sys.exit(1)

def run_tests():
    print("=== Iniciando Teste de Memória da Conversa ===")
    session_id = f"test_mem_{uuid.uuid4().hex[:6]}"
    
    # Passo 1: Enviar introdução
    intro_msg = "Olá, meu nome é Cassiano, tenho 48 anos e moro em Florianópolis."
    print(f"\n1. Enviando: '{intro_msg}'")
    ans1 = query_chat(session_id, intro_msg)
    print(f"Resposta:\n{ans1}")
    
    # Passo 2: Perguntar nome
    q_name = "Você sabe o meu nome?"
    print(f"\n2. Enviando: '{q_name}'")
    ans2 = query_chat(session_id, q_name)
    print(f"Resposta:\n{ans2}")
    
    # Passo 3: Perguntar idade
    q_age = "Qual a minha idade?"
    print(f"\n3. Enviando: '{q_age}'")
    ans3 = query_chat(session_id, q_age)
    print(f"Resposta:\n{ans3}")
    
    # Passo 4: Perguntar moradia
    q_city = "Onde eu moro?"
    print(f"\n4. Enviando: '{q_city}'")
    ans4 = query_chat(session_id, q_city)
    print(f"Resposta:\n{ans4}")
    
    # Passo 5: Perguntar profissão
    q_job = "Qual é a minha profissão?"
    print(f"\n5. Enviando: '{q_job}'")
    ans5 = query_chat(session_id, q_job)
    print(f"Resposta:\n{ans5}")
    
    # Asserções / Verificação
    print("\n=== Verificando Critérios de Aceite ===")
    
    success = True
    
    # 2. Deve saber o nome Cassiano
    if "cassiano" not in ans2.lower():
        print("[FALHA] O agente não soube o nome.")
        success = False
    else:
        print("[SUCESSO] O agente lembrou o nome.")
        
    # 3. Deve saber a idade 48 anos
    if "48" not in ans3.lower():
        print("[FALHA] O agente não soube a idade.")
        success = False
    else:
        print("[SUCESSO] O agente lembrou a idade.")
        
    # 4. Deve saber a cidade Florianópolis
    if "florianópolis" not in ans4.lower() and "florianopolis" not in ans4.lower():
        print("[FALHA] O agente não soube a cidade.")
        success = False
    else:
        print("[SUCESSO] O agente lembrou a cidade.")
        
    # 5. Deve dizer que a profissão não foi informada
    if "não" not in ans5.lower() and "ainda" not in ans5.lower():
        print("[FALHA] O agente não respondeu adequadamente sobre a profissão.")
        success = False
    else:
        print("[SUCESSO] O agente respondeu com naturalidade sobre a profissão não informada.")
        
    if success:
        print("\n=== TODOS OS TESTES DE MEMÓRIA PASSARAM! ===")
        sys.exit(0)
    else:
        print("\n=== FALHA EM UM OU MAIS TESTES DE MEMÓRIA ===")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
