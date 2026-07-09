import React from "react";
import { BotMessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";

interface AppLogoProps {
  compact?: boolean;
  className?: string;
}

export const AppLogo: React.FC<AppLogoProps> = ({ compact, className }) => {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-cyan-400/10 text-cyan-300 ring-1 ring-cyan-400/20">
        <BotMessageSquare className="h-5 w-5" />
      </div>
      {!compact && (
        <div>
          <p className="text-sm font-semibold tracking-wide text-white">
            LLMOps
          </p>
          <p className="text-xs text-slate-400">
            Document chat workspace
          </p>
        </div>
      )}
    </div>
  );
};
