import React, { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, SendHorizontal, X } from "lucide-react";
import { isAxiosError } from "axios";
import { AppLayout } from "@/layouts/AppLayout";
import { Card } from "@/components/app/Card";
import { PageContainer } from "@/components/app/PageContainer";
import { PrimaryButton } from "@/components/app/PrimaryButton";
import {
  getSessionDocuments,
  getSessionMessages,
  listSessions,
} from "@/api/sessions";
import { sendChatMessage } from "@/api/chat";
import type { ChatMessageItem } from "@/types/api";
import { cn } from "@/lib/utils";

export const ChatPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId?: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [message, setMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showDocuments, setShowDocuments] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // If no sessionId in the URL, redirect to the latest session (or /sessions if none exist).
  const { data: allSessions } = useQuery({
    queryKey: ["sessions"],
    queryFn: listSessions,
  });
  const activeSession = allSessions?.find(
    (session) => session.session_id === sessionId
  );

  useEffect(() => {
    if (sessionId) return;
    if (allSessions === undefined) return;

    if (allSessions.length > 0) {
      const latest = allSessions[0];
      navigate(`/chat/${latest.session_id}`, { replace: true });
    } else {
      navigate("/sessions", { replace: true });
    }
  }, [sessionId, allSessions, navigate]);

  const { data: messages, isLoading: messagesLoading } = useQuery({
    queryKey: ["messages", sessionId],
    queryFn: () => getSessionMessages(sessionId!),
    enabled: !!sessionId,
  });

  const { data: documents } = useQuery({
    queryKey: ["documents", sessionId],
    queryFn: () => getSessionDocuments(sessionId!),
    enabled: !!sessionId,
  });

  const chatMutation = useMutation({
    mutationFn: () => sendChatMessage(sessionId!, message),
    onSuccess: (data) => {
      const now = new Date().toISOString();
      queryClient.setQueryData<ChatMessageItem[]>(
        ["messages", sessionId],
        (old) => [
          ...(old ?? []),
          { role: "user", content: message, created_at: now },
          { role: "assistant", content: data.answer, created_at: now },
        ]
      );
      setMessage("");
    },
    onError: (error: unknown) => {
      if (isAxiosError(error) && error.response?.data?.detail) {
        setErrorMessage(String(error.response.data.detail));
      } else {
        setErrorMessage("Failed to send message. Please try again.");
      }
    },
  });

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  useEffect(() => {
    setShowDocuments(false);
  }, [sessionId]);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!message.trim() || !sessionId) return;
    setErrorMessage(null);
    chatMutation.mutate();
  };

  if (!sessionId) {
    return (
      <AppLayout title="Chat">
        <PageContainer>
          <p className="text-sm text-slate-400">Loading session...</p>
        </PageContainer>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Chat" contentClassName="flex min-h-0 flex-col">
      <PageContainer className="flex h-full min-h-0 flex-col gap-4">
        <Card glow className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
              Active session
            </p>
            <h2 className="mt-2 text-xl font-semibold text-white">
              {activeSession?.display_name || sessionId}
            </h2>
          </div>
          <button
            type="button"
            onClick={() => setShowDocuments((current) => !current)}
            className="rounded-2xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300 transition hover:border-cyan-400/40 hover:text-white"
          >
            {documents?.length ?? 0} docs
          </button>
        </Card>

        {showDocuments && (
          <Card className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold text-white">
                  Uploaded documents
                </h3>
                <p className="mt-1 text-sm text-slate-400">
                  Files available in this session.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowDocuments(false)}
                className="rounded-xl border border-white/10 bg-white/5 p-2 text-slate-400 transition hover:text-white"
                aria-label="Close document list"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {documents && documents.length > 0 ? (
              <div className="space-y-3">
                {documents.map((document) => (
                  <div
                    key={`${document.file_path}-${document.created_at}`}
                    className="flex items-center justify-between gap-4 rounded-2xl border border-white/10 bg-white/5 px-4 py-3"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="rounded-xl border border-white/10 bg-slate-950 p-2 text-cyan-300">
                        <FileText className="h-4 w-4" />
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-white">
                          {document.filename}
                        </p>
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                          {document.file_type}
                        </p>
                      </div>
                    </div>
                    <span className="shrink-0 text-xs text-slate-500">
                      {new Date(document.created_at).toLocaleDateString()}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-400">
                No documents found for this session.
              </p>
            )}
          </Card>
        )}

        <Card className="flex min-h-0 flex-1 flex-col p-0">
          <div
            ref={scrollRef}
            className="flex-1 space-y-4 overflow-y-auto p-5"
          >
            {messagesLoading && (
              <p className="text-sm text-slate-400">Loading messages...</p>
            )}

            {messages?.map((chatMessage, index) => {
              const isUser = chatMessage.role === "user";
              return (
                <div
                  key={`${chatMessage.created_at}-${index}`}
                  className={cn(
                    "flex",
                    isUser ? "justify-end" : "justify-start"
                  )}
                >
                  <div
                    className={cn(
                      "max-w-2xl rounded-3xl px-4 py-3 text-sm shadow-sm",
                      isUser
                        ? "bg-cyan-400 text-slate-950"
                        : "border border-white/10 bg-white/5 text-slate-100"
                    )}
                  >
                    <p className="mb-2 text-xs opacity-70">
                      {isUser ? "You" : "Assistant"}
                    </p>
                    <p className="whitespace-pre-wrap leading-6">
                      {chatMessage.content}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="border-t border-white/10 p-4">
            {errorMessage && (
              <p className="mb-3 text-sm text-red-400" role="alert">
                {errorMessage}
              </p>
            )}
            <form
              className="flex flex-col gap-3 md:flex-row"
              onSubmit={handleSubmit}
            >
              <textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                rows={3}
                placeholder="Ask a question about your uploaded documents..."
                className="min-h-24 flex-1 rounded-3xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-400/50"
              />
              <PrimaryButton
                type="submit"
                className="md:self-end"
                disabled={chatMutation.isPending || !message.trim()}
              >
                <SendHorizontal className="h-4 w-4" />
                {chatMutation.isPending ? "Sending..." : "Send"}
              </PrimaryButton>
            </form>
          </div>
        </Card>
      </PageContainer>
    </AppLayout>
  );
};
