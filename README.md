# Vida Assistida

O Vida Assistida é um oráculo prático e humanizado projetado para acolher familiares, apoiar cuidadores e orientar gestores de ILPIs (Instituições de Longa Permanência para Idosos), baseado no livro do Professor Ornélio Dias de Moraes.

---

## Modos de Execução

O projeto possui dois modos principais de execução configuráveis através das variáveis de ambiente do backend.

### 1. Modo Desenvolvimento (Padrão)

Neste modo, o frontend e o backend rodam de forma independente, facilitando o desenvolvimento com recarregamento rápido (HMR).

#### Configuração
- **Backend (`api/.env`)**:
  ```env
  SERVE_FRONTEND=false
  ```
- **Frontend (`web/.env`)**:
  ```env
  VITE_API_URL=http://localhost:8000/api
  ```

#### Como Executar
1. **Iniciar a API (Backend)**:
   ```bash
   cd api
   uv run uvicorn app.main:app --reload
   ```
   A API estará disponível em `http://localhost:8000`.

2. **Iniciar o Servidor Dev (Frontend)**:
   ```bash
   cd web
   npm run dev
   ```
   O frontend estará disponível em `http://localhost:5173`.

---

### 2. Modo Demonstração / ngrok (Porta Única)

Neste modo, o FastAPI serve tanto os endpoints da API (sob o prefixo `/api`) quanto a aplicação estática do React compilada no mesmo servidor. Útil para demonstrações distribuídas com um único túnel ngrok.

#### Configuração
- **Backend (`api/.env`)**:
  ```env
  SERVE_FRONTEND=true
  ```
- **Frontend (`web/.env.local`)**:
  Defina a senha de demonstração no frontend antes de gerar o build:
  ```env
  VITE_DEMO_ACCESS_PASSWORD=sua-senha-de-demonstracao
  ```

#### Como Executar
1. **Gerar o Build do Frontend**:
   Navegue até a pasta `web` e compile a aplicação:
   ```bash
   cd web
   npm run build
   ```
   Isso criará a pasta `web/dist`.

2. **Iniciar o Servidor Unificado**:
   Navegue até a pasta `api` e execute o servidor:
   ```bash
   cd api
   uv run uvicorn app.main:app
   ```
   *Nota: Se a pasta `web/dist` não existir, o servidor emitirá um erro impeditivo no console.*

3. **Acessar e Compartilhar**:
   O aplicativo inteiro estará rodando em:
   - `http://localhost:8000` (tela de senha e chat)
   - `http://localhost:8000/api/...` (rotas do backend)

   Para expor a demonstração publicamente via ngrok, basta executar:
   ```bash
   ngrok http 8000
   ```
   Compartilhe a URL pública gerada pelo ngrok. Ao acessá-la, os usuários verão a tela de proteção por senha antes de acessar o chat.

---

## Observações de Segurança
* **Portão de Senha**: A senha definida em `VITE_DEMO_ACCESS_PASSWORD` é embutida no build final de client-side (React/Vite). Esta proteção serve apenas como barreira simples para demonstração (PoC) local e **não substitui** uma infraestrutura definitiva de autenticação de produção (ex: JWT, Supabase, etc.).

## Modos de execução para exibir data, hora, nível, IP, rota e status HTTP

   ```bash
   uv run uvicorn app.main:app --log-config logging.ini
   ```