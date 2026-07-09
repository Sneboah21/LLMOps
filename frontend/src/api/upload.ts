import api from "./client";
import type { UploadResponse } from "../types/api";

type RetrievalBackend = "FAISS" | "PageIndex";

export const uploadFiles = (files: File[], retrievalBackend: RetrievalBackend) => {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  formData.append("retrieval_backend", retrievalBackend.toLowerCase());

  return api
    .post<UploadResponse>("/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((res) => res.data);
};