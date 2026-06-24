from __future__ import annotations
import os
from pathlib import Path
from typing import Annotated, Dict, List

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from multi_doc_chat.src.document_ingestion.data_ingestion import ChatIngestor
from multi_doc_chat.src.document_chat.retrieval import ConversationalRAG
from langchain_core.messages import HumanMessage, AIMessage
from multi_doc_chat.exception.custom_exception import DocumentPortalException
from multi_doc_chat.model.models import UploadResponse, ChatRequest, ChatResponse
from multi_doc_chat.utils.document_ops import FastAPIFileAdapter


app = FastAPI(title="MultiDocChat")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

SESSIONS: Dict[str, List[Dict]] = {}


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/upload-page", response_class=HTMLResponse)
async def upload_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Upload Documents — MultiDocChat</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 60px auto; padding: 20px; background: #f9f9f9; }
            h2 { margin-bottom: 20px; }
            .card { background: #fff; border: 1px solid #ddd; border-radius: 10px; padding: 28px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
            label { font-weight: bold; display: block; margin-bottom: 8px; }
            input[type="file"] { display: block; margin-bottom: 16px; width: 100%; }
            button {
                padding: 10px 22px; background: #0d6efd; color: #fff;
                border: none; border-radius: 7px; cursor: pointer; font-size: 15px;
            }
            button:disabled { background: #aaa; cursor: not-allowed; }
            button:hover:not(:disabled) { background: #0b5ed7; }
            #status { margin-top: 18px; font-size: 14px; color: #555; }
            #result {
                margin-top: 12px; white-space: pre-wrap; background: #f4f4f4;
                padding: 14px; border-radius: 8px; font-size: 13px;
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Upload Documents</h2>
            <form id="uploadForm">
                <label for="files">Choose files (.pdf, .docx, .txt)</label>
                <input type="file" id="files" name="files" multiple accept=".pdf,.docx,.txt" required />
                <button type="submit" id="submitBtn">Upload</button>
            </form>
            <div id="status"></div>
            <pre id="result"></pre>
        </div>

        <script>
            const form = document.getElementById("uploadForm");
            const statusEl = document.getElementById("status");
            const resultEl = document.getElementById("result");
            const submitBtn = document.getElementById("submitBtn");

            form.addEventListener("submit", async (e) => {
                e.preventDefault();

                const fileInput = document.getElementById("files");
                if (!fileInput.files.length) {
                    statusEl.textContent = "Please select at least one file.";
                    return;
                }

                const formData = new FormData();
                for (const file of fileInput.files) {
                    formData.append("files", file);
                }

                submitBtn.disabled = true;
                statusEl.textContent = "Uploading...";
                resultEl.style.display = "none";

                try {
                    const response = await fetch("/upload", {
                        method: "POST",
                        body: formData
                        // DO NOT set Content-Type header — browser sets it with boundary
                    });

                    const text = await response.text();
                    let data;
                    try { data = JSON.parse(text); } catch { data = text; }

                    resultEl.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
                    resultEl.style.display = "block";

                    if (response.ok) {
                        statusEl.textContent = "✅ Upload successful!";
                    } else {
                        statusEl.textContent = "❌ Upload failed. See details below.";
                    }
                } catch (err) {
                    statusEl.textContent = "❌ Network error: " + err;
                } finally {
                    submitBtn.disabled = false;
                }
            });
        </script>
    </body>
    </html>
    """


@app.post("/upload", response_model=UploadResponse)
async def upload(
    files: Annotated[list[UploadFile], File(description="Select one or more files")]
) -> UploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    try:
        wrapped_files = [FastAPIFileAdapter(f) for f in files]
        ingestor = ChatIngestor(use_session_dirs=True)
        session_id = ingestor.session_id
        ingestor.built_retriever(uploaded_files=wrapped_files)
        SESSIONS[session_id] = []
        return UploadResponse(
            session_id=session_id,
            indexed=True,
            message="Files uploaded and indexed successfully."
        )
    except DocumentPortalException as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    session_id = req.session_id
    message = req.message.strip()
    if not session_id or session_id not in SESSIONS:
        raise HTTPException(status_code=400, detail="Invalid or expired session_id. Reupload documents.")
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    try:
        rag = ConversationalRAG(session_id=session_id)
        index_path = f"faiss_index/{session_id}"
        rag.load_retriever_from_faiss(index_path=index_path)

        simple = SESSIONS.get(session_id, [])
        lc_history = []
        for m in simple:
            role = m.get("role")
            content = m.get("content", "")
            if role == "user":
                lc_history.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_history.append(AIMessage(content=content))

        answer = rag.invoke(message, chat_history=lc_history)
        simple.append({"role": "user", "content": message})
        simple.append({"role": "assistant", "content": answer})
        SESSIONS[session_id] = simple
        return ChatResponse(answer=answer)
    except DocumentPortalException as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
