import React from "react";
import { Inbox } from "lucide-react";
import { Card } from "./Card";

interface EmptyStateProps {
  title: string;
  description: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
}) => {
  return (
    <Card className="flex min-h-52 flex-col items-center justify-center gap-3 text-center">
      <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-slate-300">
        <Inbox className="h-5 w-5" />
      </div>
      <div className="space-y-1">
        <h3 className="text-lg font-semibold text-white">{title}</h3>
        <p className="max-w-md text-sm text-slate-400">{description}</p>
      </div>
    </Card>
  );
};
