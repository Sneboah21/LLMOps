import api from "./client";
import type {
  SessionSummary,
  DocumentItem,
  ChatMessageItem,
  RenameSessionPayload,
  RenameSessionResponse,
} from "../types/api";

export const listSessions = () =>
  api.get<SessionSummary[]>("/sessions").then((res) => res.data);

export const getSessionDocuments = (sessionId: string) =>
  api
    .get<DocumentItem[]>(`/sessions/${sessionId}/documents`)
    .then((res) => res.data);

export const getSessionMessages = (sessionId: string) =>
  api
    .get<ChatMessageItem[]>(`/sessions/${sessionId}/messages`)
    .then((res) => res.data);

import type { DeleteSessionResponse } from "../types/api";

export const deleteSession = (sessionId: string) =>
  api
    .delete<DeleteSessionResponse>(`/sessions/${sessionId}`)
    .then((res) => res.data);

export const renameSession = (
  sessionId: string,
  payload: RenameSessionPayload
) =>
  api
    .patch<RenameSessionResponse>(`/sessions/${sessionId}/rename`, payload)
    .then((res) => res.data);
