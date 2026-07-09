import React from "react";
import type { ChatMessageItem } from "../../types/api";

export const ChatMessage: React.FC<{ message: ChatMessageItem }> = ({
  message,
}) => {
  const isUser = message.role === "user";
  return (
    <div
      className={`p-3 rounded-lg max-w-2xl mb-3 ${
        isUser ? "bg-blue-100 ml-auto" : "bg-gray-100 mr-auto"
      }`}
    >
      <p className="text-xs text-gray-500 mb-1">
        {isUser ? "You" : "Assistant"}
      </p>
      <p className="whitespace-pre-wrap">{message.content}</p>
    </div>
  );
};