# LLMOps – Multi‑Document Conversational RAG

LLMOps is a multi‑document Retrieval‑Augmented Generation (RAG) platform that lets you:

- Upload multiple documents (PDF, DOCX, TXT)
- Build a **session‑specific knowledge base** using FAISS (vector DB) or **PageIndex** (vectorless reasoning‑based retrieval)
- Chat with your documents via a FastAPI backend or directly from the terminal

---

## 1. Prerequisites

- Python 3.10+ installed
- Git installed
- (Optional) `uv` or `pip` for dependency management
- An `.env` file with your API keys

Clone the repo:

```bash
git clone https://github.com/Sneboah21/LLMOps.git
cd LLMOps
```

Create and activate a virtual environment (example with `venv`):

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 2. Environment configuration (`.env`)

Create a `.env` file in the project root (same folder as `main.py`, `config.yaml`, `requirements.txt`).

At minimum you’ll typically need:

```env
# LLM providers (use only the ones you actually configure in config.yaml)
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here
GROQ_API_KEY=your_groq_key_here

# LangSmith / LangChain tracing (optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langsmith_key_here
LANGCHAIN_PROJECT=llmops

# PageIndex (for vectorless retrieval)
PAGEINDEX_API_KEY=your_pageindex_key_here
```

Match these to the providers you enable in `config/config.yaml` (for example, if you’re using only Ollama and PageIndex locally, you may not need OpenAI keys).

> **Note:** Never commit your real `.env` to Git. `.env` is already ignored by `.gitignore`.

---

## 3. Configuring retrieval (`config/config.yaml`)

The retrieval behavior is controlled by the `retrieval` section in `config/config.yaml`:

```yaml
retrieval:
  mode: "mmr"        # "similarity" | "mmr" | "pageindex"
  top_k: 5
```

- `similarity` – FAISS + standard similarity search  
- `mmr` – FAISS + Maximal Marginal Relevance (better diversity)  
- `pageindex` – **PageIndex vectorless DB** (no embeddings, tree‑based reasoning)

The FAISS retriever tuning lives under `retriever`:

```yaml
retriever:
  top_k: 10
  search_type: "mmr"    # "similarity" or "mmr" (used only in FAISS modes)
  fetch_k: 20
  lambda_mult: 0.5
```

In PageIndex mode, `retriever.search_type` is ignored; `retrieval.mode: "pageindex"` is the main switch.

PageIndex settings:

```yaml
pageindex:
  enabled: true
  api_key: "env:PAGEINDEX_API_KEY"
  base_url: "https://api.pageindex.ai"
  doc_namespace: "session"
```

---

## 4. Preparing documents (RAG context)

For both the API and terminal script, documents should be in the `data/` folder:

- **FAISS mode (similarity / MMR)**:
  - Documents are uploaded via the `/upload` endpoint or via your helper scripts.
  - They are saved into `data/<session_id>/` and indexed into FAISS.

- **PageIndex mode**:
  - Only **PDFs** are supported (PageIndex ingests PDFs and builds a tree index).
  - These PDFs are uploaded for the current session and submitted to PageIndex; the resulting `doc_id`s are stored session‑wise.

You can also place “static” docs directly under `data/` if your scripts read them (e.g. for `test.py`).

---

## 5. Running the FastAPI app

From the project root:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Then:

- Open `http://localhost:8000` in your browser for the main UI.
- Or open `http://localhost:8000/upload-page` to use the upload form:
  1. Select one or more `.pdf`, `.docx` or `.txt` files.
  2. Click **Upload**.
  3. The response will include a `session_id`.

Use that `session_id` in your frontend or API client when calling `/chat`:

- `POST /chat` with JSON body:
  ```json
  {
    "session_id": "session_20260626150953_e1249710",
    "message": "Your question about the documents"
  }
  ```

The backend will:

- In **FAISS mode**: load the session FAISS index and run the LCEL RAG pipeline.  
- In **PageIndex mode**: call PageIndex with the session’s `doc_id`s and use the retrieved context to answer.

---

## 6. Running from the terminal (`test.py`)

If you want to chat from the terminal instead of hitting the FastAPI endpoints:

1. Make sure your documents are in the `data/` directory and that `retrieval.mode` in `config.yaml` is set as desired:
   - `"similarity"` or `"mmr"` for FAISS
   - `"pageindex"` for PageIndex

2. Run:

```bash
python test.py
```

A typical `test.py` flow is:

- Load config and models.
- Load documents from `data/`.
- Build the retriever based on `retrieval.mode`.
- Enter a loop where you type questions and get answers from the RAG pipeline.

(Adjust this description to match the exact behavior of your `test.py`.)

---

## 7. Switching retrieval strategies

To switch RAG behavior, you only edit `config/config.yaml`:

- **Vector RAG with FAISS (similarity)**:
  ```yaml
  retrieval:
    mode: "similarity"
    top_k: 5
  retriever:
    search_type: "similarity"
  ```

- **Vector RAG with FAISS (MMR)**:
  ```yaml
  retrieval:
    mode: "mmr"
    top_k: 5
  retriever:
    search_type: "mmr"
    fetch_k: 20
    lambda_mult: 0.5
  ```

- **Vectorless RAG with PageIndex**:
  ```yaml
  retrieval:
    mode: "pageindex"
    top_k: 5
  pageindex:
    enabled: true
    api_key: "env:PAGEINDEX_API_KEY"
  ```

Restart the app or rerun `test.py` after changing modes.

---

## 8. Logging and troubleshooting

- Logs are written under `logs/` and include:
  - Session IDs
  - Ingestion status
  - Retrieval mode used
  - PageIndex `doc_id`s and retrieval IDs (when enabled)

If you see messages like `"No relevant context found in documents."`, it means:

- The system ran successfully, but retrieval didn’t find any sections in the uploaded docs that answer your question.  
- Check that:
  - The answer is actually present in the uploaded documents.
  - You’re in the right mode (FAISS vs PageIndex) for your use case.
  - In PageIndex mode, you uploaded PDFs, not DOCX/TXT.

---

If you tell what you expect `test.py` to do exactly (interactive loop, single-shot Q&A, etc.), this README can be refined further to match your script’s options and arguments.