import React from "react";
import { AppLogo } from "@/components/app/AppLogo";

interface AuthLayoutProps {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({
  title,
  subtitle,
  children,
}) => {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(34,211,238,0.16),_transparent_30%),linear-gradient(180deg,_#020617_0%,_#0f172a_100%)] px-4 py-10">
      <div className="w-full max-w-md rounded-[2rem] border border-white/10 bg-slate-950/80 p-8 shadow-[0_32px_80px_-32px_rgba(8,145,178,0.45)] backdrop-blur">
        <AppLogo className="mb-8" />
        <div className="mb-8 space-y-2">
          <h1 className="text-3xl font-semibold text-white">{title}</h1>
          <p className="text-sm text-slate-400">{subtitle}</p>
        </div>
        {children}
      </div>
    </div>
  );
};
