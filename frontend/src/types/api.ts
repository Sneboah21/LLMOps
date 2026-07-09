export interface RegisterPayload {
  email: string;
  password: string;
  confirm_password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserResponse {
  id: number;
  email: string;
  created_at: string;
}

export interface SessionSummary {
  session_id: string;
  display_name: string;
  created_at: string;
  document_count: number;
  message_count: number;
  backend: "faiss" | "pageindex";
  is_active: boolean;
}

export interface RenameSessionPayload {
  display_name: string;
}

export interface RenameSessionResponse {
  session_id: string;
  display_name: string;
}

export interface DocumentItem {
  filename: string;
  file_type: string;
  file_path: string;
  faiss_index_path: string | null;
  pageindex_doc_id: string | null;
  created_at: string;
}

export interface ChatMessageItem {
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatResponse {
  answer: string;
}

export interface UploadResponse {
  session_id: string;
  indexed: boolean;
  message: string;
}

export interface DeleteSessionResponse {
  session_id: string;
  deleted: boolean;
  message: string;
  deleted_document_rows: number;
  deleted_pageindex_docs: number;
  deleted_files: number;
  deleted_faiss_dirs: number;
  warnings: string[];
}
