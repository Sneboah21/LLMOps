import api from "./client";
import type { ChatResponse } from "../types/api";

export const sendChatMessage = (sessionId: string, message: string) =>
  api
    .post<ChatResponse>("/chat", { session_id: sessionId, message })
    .then((res) => res.data);