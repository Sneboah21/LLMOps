export interface SessionCardItem {
  id: string;
  title: string;
  summary: string;
  updatedAt: string;
  documentCount: number;
}

export interface UploadFileItem {
  id: string;
  name: string;
  size: string;
  status: "Ready" | "Indexed" | "Pending";
}

export interface ChatBubble {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export const mockSessions: SessionCardItem[] = [
  {
    id: "session-q2",
    title: "Quarterly Ops Review",
    summary: "Discuss retrieval quality across uploaded policy and incident docs.",
    updatedAt: "Updated 2 hours ago",
    documentCount: 6,
  },
  {
    id: "session-rfp",
    title: "Vendor RFP Questions",
    summary: "Prepare answers grounded in procurement PDFs and meeting notes.",
    updatedAt: "Updated yesterday",
    documentCount: 3,
  },
  {
    id: "session-onboarding",
    title: "Onboarding Knowledge Base",
    summary: "Test assistant responses over HR handbooks and SOP references.",
    updatedAt: "Updated 3 days ago",
    documentCount: 8,
  },
];

export const mockUploadedFiles: UploadFileItem[] = [
  { id: "file-1", name: "employee-handbook.pdf", size: "2.1 MB", status: "Indexed" },
  { id: "file-2", name: "incident-response.docx", size: "860 KB", status: "Ready" },
  { id: "file-3", name: "quarterly-review-notes.txt", size: "140 KB", status: "Pending" },
];

export const mockChatMessages: ChatBubble[] = [
  {
    id: "chat-1",
    role: "assistant",
    content: "Your uploaded documents are ready. Ask a question when you want to test retrieval quality.",
    timestamp: "09:30 AM",
  },
  {
    id: "chat-2",
    role: "user",
    content: "Summarize the escalation policy changes from the latest handbook.",
    timestamp: "09:31 AM",
  },
  {
    id: "chat-3",
    role: "assistant",
    content: "Placeholder answer: this is where the backend response will appear once chat integration is connected.",
    timestamp: "09:31 AM",
  },
];
