import React from "react";
import { cn } from "@/lib/utils";

type SecondaryButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement>;

export const SecondaryButton: React.FC<SecondaryButtonProps> = ({
  className,
  children,
  ...props
}) => {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-100 transition hover:border-white/15 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
};
