from __future__ import annotations
import os
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from multi_doc_chat.src.document_chat.retrieval import ConversationalRAG
from multi_doc_chat.exception.custom_exception import DocumentPortalException
from multi_doc_chat.model.models import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    DocumentResponse,
    LoginRequest,
    RegisterRequest,
    SessionSummaryResponse,
    TokenResponse,
    UploadResponse,
    UserResponse,
)
from multi_doc_chat.utils.document_ops import FastAPIFileAdapter
from multi_doc_chat.utils.config_loader import load_config

from multi_doc_chat.auth.dependencies import get_current_user

from multi_doc_chat.db import models as db_models

from multi_doc_chat.services.auth_service import (
    AuthService,
    AuthenticationError,
    DuplicateUserError,
)


from sqlalchemy.orm import Session
from multi_doc_chat.db.database import get_db
from multi_doc_chat.services import session_service
from multi_doc_chat.services.upload_service import UploadService
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

#----------------------------------------------------
from pydantic import BaseModel
from multi_doc_chat.services.session_delete_service import (
    ExternalCleanupError,
    SessionDeletionService,
    SessionNotFoundError,
)
#----------------------------------------------------

CONFIG = load_config()

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


@app.get("/health")
def health() -> dict:
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
            button { padding: 10px 22px; background: #0d6efd; color: #fff; border: none; border-radius: 7px; cursor: pointer; font-size: 15px; }
            button:disabled { background: #aaa; cursor: not-allowed; }
            button:hover:not(:disabled) { background: #0b5ed7; }
            #status { margin-top: 18px; font-size: 14px; color: #555; }
            #result { margin-top: 12px; white-space: pre-wrap; background: #f4f4f4; padding: 14px; border-radius: 8px; font-size: 13px; display: none; }
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
                if (!fileInput.files.length) { statusEl.textContent = "Please select at least one file."; return; }
                const formData = new FormData();
                for (const file of fileInput.files) { formData.append("files", file); }
                submitBtn.disabled = true;
                statusEl.textContent = "Uploading...";
                resultEl.style.display = "none";
                try {
                    const response = await fetch("/upload", { method: "POST", body: formData });
                    const text = await response.text();
                    let data;
                    try { data = JSON.parse(text); } catch { data = text; }
                    resultEl.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
                    resultEl.style.display = "block";
                    statusEl.textContent = response.ok ? "✅ Upload successful!" : "❌ Upload failed. See details below.";
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


@app.post("/register", response_model=UserResponse, status_code=201)
async def register(
    req: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    try:
        service = AuthService(db=db, cfg=CONFIG)
        user = service.register_user(
            email=req.email,
            password=req.password,
            confirm_password=req.confirm_password,
        )
        db.commit()

        return UserResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at,
        )

    except DuplicateUserError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except DocumentPortalException as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        service = AuthService(db=db, cfg=CONFIG)
        user = service.authenticate_user(
            email=req.email,
            password=req.password,
        )
        access_token, expires_in = service.create_access_token(user)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
        )

    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except DocumentPortalException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")



@app.post("/upload", response_model=UploadResponse)
async def upload(
    files: Annotated[list[UploadFile], File(description="Select one or more files")],
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
) -> UploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    try:
        wrapped_files = []
        filenames = []
        for f in files:
            contents = await f.read()
            await f.seek(0)
            wrapped_files.append(FastAPIFileAdapter(f, prefetched=contents))
            filenames.append(f.filename)

        service = UploadService(db=db, cfg=CONFIG)
        session_id = service.process_upload(
            wrapped_files=wrapped_files,
            original_filenames=filenames,
            user_id=current_user.id,
        )

        return UploadResponse(
            session_id=session_id,
            indexed=True,
            message="Files uploaded and indexed successfully.",
        )

    except DocumentPortalException as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/sessions", response_model=list[SessionSummaryResponse])
async def list_sessions(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
) -> list[SessionSummaryResponse]:
    try:
        rows = session_service.list_sessions(db, user_id=current_user.id)

        return [
            SessionSummaryResponse(
                session_id=row["session_id"],
                created_at=row["created_at"],
                document_count=row["document_count"],
                message_count=row["message_count"],
                backend=row["backend"],
                is_active=row["is_active"],
            )
            for row in rows
        ]

    except DocumentPortalException as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sessions: {str(e)}",
        )

@app.get("/sessions/{session_id}/documents", response_model=list[DocumentResponse])
async def get_session_documents(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
) -> list[DocumentResponse]:
    try:
        session_obj = session_service.get_session_by_session_id(
            db,
            session_id,
            user_id=current_user.id,
        )
        if session_obj is None:
            raise HTTPException(
                status_code=404,
                detail="Session not found.",
            )

        documents = session_service.get_session_documents(
            db,
            session_id,
            user_id=current_user.id,
        )

        return [
            DocumentResponse(
                filename=doc.filename,
                file_type=doc.file_type,
                file_path=doc.file_path,
                faiss_index_path=doc.faiss_index_path,
                pageindex_doc_id=doc.pageindex_doc_id,
                created_at=doc.created_at,
            )
            for doc in documents
        ]

    except HTTPException:
        raise
    except DocumentPortalException as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load session documents: {str(e)}",
        )


@app.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def get_session_messages(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
) -> list[ChatMessageResponse]:
    try:
        session_obj = session_service.get_session_by_session_id(
            db,
            session_id,
            user_id=current_user.id,
        )
        if session_obj is None:
            raise HTTPException(status_code=404, detail="Session not found.")

        messages = session_service.get_session_messages(
            db,
            session_id,
            user_id=current_user.id,
        )

        return [
            ChatMessageResponse(
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
            )
            for msg in messages
        ]

    except HTTPException:
        raise
    except DocumentPortalException as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load session messages: {str(e)}",
        )

# @app.post("/chat", response_model=ChatResponse)
# async def chat(req: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
#     session_id = req.session_id
#     message = req.message.strip()

#     db_session = session_service.get_session_by_session_id(db, session_id)
#     if not session_id or db_session is None:
#         raise HTTPException(status_code=400, detail="Invalid or expired session_id. Reupload documents.")
#     if not message:
#         raise HTTPException(status_code=400, detail="Message cannot be empty.")

#     try:
#         retrieval_cfg = CONFIG.get("retrieval", {})
#         mode = retrieval_cfg.get("mode", "mmr")
#         top_k = retrieval_cfg.get("top_k", 5)

#         rag = ConversationalRAG(session_id=session_id)

#         history_rows = session_service.get_chat_history(db, db_session.id)
#         lc_history = []
#         for row in history_rows:
#             if row.role == "user":
#                 lc_history.append(HumanMessage(content=row.content))
#             elif row.role == "assistant":
#                 lc_history.append(AIMessage(content=row.content))

#         if mode in ("similarity", "mmr"):
#             index_path = f"faiss_index/{session_id}"
#             rag.load_retriever_from_faiss(index_path=index_path, k=top_k, search_type=mode)
#             answer = rag.invoke(message, chat_history=lc_history)
#         elif mode == "pageindex":
#             answer = rag.invoke_with_pageindex(user_input=message, chat_history=lc_history, top_k=top_k)
#         else:
#             raise HTTPException(status_code=400, detail=f"Unsupported retrieval mode: {mode}")

#         # Attach both messages, then commit ONCE
#         session_service.record_chat_turn(
#             db=db,
#             session_pk=db_session.id,
#             user_message=message,
#             assistant_message=answer,
#         )
#         db.commit()

#         return ChatResponse(answer=answer)

#     except DocumentPortalException as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=str(e))
#     except HTTPException:
#         raise
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
) -> ChatResponse:
    session_id = req.session_id
    message = req.message.strip()

    db_session = session_service.get_session_by_session_id(db, session_id, user_id=current_user.id)
    if not session_id or db_session is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired session_id. Reupload documents.",
        )
    if not db_session.is_active:
        raise HTTPException(
            status_code=400,
            detail="This session is inactive and cannot be restored.",
        )
    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    try:
        retrieval_cfg = CONFIG.get("retrieval", {})
        doc_ids = session_service.get_pageindex_doc_ids_for_session(
            db, db_session.id
        )
        mode = "pageindex" if doc_ids else "faiss"
        top_k = retrieval_cfg.get("top_k", 5)

        rag = ConversationalRAG(session_id=session_id)

        # Build LangChain-style history from DB
        history_rows = session_service.get_chat_history(db, db_session.id)
        lc_history: list[BaseMessage] = []
        for row in history_rows:
            if row.role == "user":
                lc_history.append(HumanMessage(content=row.content))
            elif row.role == "assistant":
                lc_history.append(AIMessage(content=row.content))

        if mode == "faiss":
            # FAISS-based retrieval
            index_path = f"faiss_index/{session_id}"
            search_type = retrieval_cfg.get("mode", "mmr")
            if search_type not in ("similarity", "mmr"):
                search_type = "mmr"
            rag.load_retriever_from_faiss(
                index_path=index_path,
                k=top_k,
                search_type=search_type,
            )
            answer = rag.invoke(message, chat_history=lc_history)

        elif mode == "pageindex":
            # PageIndex-based retrieval using doc_ids from Postgres
            if not doc_ids:
                raise HTTPException(
                    status_code=400,
                    detail="No PageIndex documents found for this session. Reupload documents.",
                )

            answer = rag.invoke_with_pageindex(
                user_input=message,
                chat_history=lc_history,
                top_k=top_k,
                doc_ids=doc_ids,
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported retrieval mode: {mode}",
            )

        # Attach both messages, then commit ONCE
        session_service.record_chat_turn(
            db=db,
            session_pk=db_session.id,
            user_message=message,
            assistant_message=answer,
        )
        db.commit()

        return ChatResponse(answer=answer)

    except DocumentPortalException as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        # Do not swallow FastAPI HTTP errors
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Chat failed: {str(e)}",
        )
#----------------------------------------------------------
class DeleteSessionResponse(BaseModel):
    session_id: str
    deleted: bool
    message: str
    deleted_document_rows: int
    deleted_pageindex_docs: int
    deleted_files: int
    deleted_faiss_dirs: int
    warnings: list[str] = []

    
@app.delete("/sessions/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
) -> DeleteSessionResponse:
    try:
        service = SessionDeletionService(db=db, cfg=CONFIG)
        result = service.delete_session(
            session_id,
            user_id=current_user.id,
        )

        return DeleteSessionResponse(
            session_id=result.session_id,
            deleted=True,
            message="Session and associated resources deleted successfully.",
            deleted_document_rows=result.deleted_document_rows,
            deleted_pageindex_docs=result.deleted_pageindex_docs,
            deleted_files=result.deleted_files,
            deleted_faiss_dirs=result.deleted_faiss_dirs,
            warnings=result.warnings,
        )

    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except ExternalCleanupError as e:
        raise HTTPException(status_code=502, detail=str(e))

    except DocumentPortalException as e:
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Session deletion failed: {str(e)}",
        )
    
#----------------------------------------------------------


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
