import React from "react";
import { cn } from "@/lib/utils";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  glow?: boolean;
}

export const Card: React.FC<CardProps> = ({
  className,
  children,
  glow,
  ...props
}) => {
  return (
    <div
      className={cn(
        "rounded-3xl border border-white/10 bg-slate-900/75 p-5 shadow-[0_24px_80px_-36px_rgba(34,211,238,0.35)] backdrop-blur",
        glow && "ring-1 ring-cyan-400/20",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};
