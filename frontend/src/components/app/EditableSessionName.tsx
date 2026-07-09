import React, { useEffect, useRef, useState } from "react";
import { Pencil } from "lucide-react";
import { cn } from "@/lib/utils";

interface EditableSessionNameProps {
  value: string;
  sessionId: string;
  onSave: (nextValue: string) => Promise<void> | void;
  className?: string;
}

export const EditableSessionName: React.FC<EditableSessionNameProps> = ({
  value,
  sessionId,
  onSave,
  className,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const inputRef = useRef<HTMLInputElement>(null);
  const cancelRef = useRef(false);
  const saveInFlightRef = useRef(false);

  useEffect(() => {
    if (!isEditing) {
      setDraft(value);
    }
  }, [isEditing, value]);

  useEffect(() => {
    if (isEditing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isEditing]);

  const cancelEditing = () => {
    cancelRef.current = true;
    setDraft(value);
    setIsEditing(false);

    window.setTimeout(() => {
      cancelRef.current = false;
    }, 0);
  };

  const commitChanges = async () => {
    const trimmed = draft.trim();

    if (!trimmed) {
      setDraft(value);
      setIsEditing(false);
      return;
    }

    if (trimmed === value.trim()) {
      setDraft(trimmed);
      setIsEditing(false);
      return;
    }

    if (saveInFlightRef.current) {
      return;
    }

    saveInFlightRef.current = true;
    try {
      await onSave(trimmed);
      setIsEditing(false);
    } finally {
      saveInFlightRef.current = false;
    }
  };

  if (isEditing) {
    return (
      <input
        ref={inputRef}
        value={draft}
        maxLength={255}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={() => {
          if (!cancelRef.current) {
            void commitChanges();
          }
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            void commitChanges();
          }

          if (event.key === "Escape") {
            event.preventDefault();
            cancelEditing();
          }
        }}
        aria-label={`Rename session ${sessionId}`}
        className={cn(
          "w-full rounded-xl border border-cyan-400/40 bg-slate-950 px-3 py-2 text-lg font-semibold text-white outline-none",
          className
        )}
      />
    );
  }

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span className="truncate">{value}</span>
      <button
        type="button"
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          setIsEditing(true);
        }}
        className="rounded-lg p-1 text-slate-400 transition hover:bg-white/10 hover:text-cyan-300"
        aria-label={`Edit session name for ${sessionId}`}
      >
        <Pencil className="h-4 w-4" />
      </button>
    </div>
  );
};
