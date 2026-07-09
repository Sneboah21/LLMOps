import React from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { Navbar } from "@/components/app/Navbar";
import { Sidebar } from "@/components/app/Sidebar";
import { cn } from "@/lib/utils";

interface AppLayoutProps {
  title: string;
  children: React.ReactNode;
  contentClassName?: string;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  title,
  children,
  contentClassName,
}) => {
  const { logout, state } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(34,211,238,0.16),_transparent_32%),linear-gradient(180deg,_#020617_0%,_#0f172a_46%,_#020617_100%)] p-4 text-slate-100 md:p-6">
      <div className="mx-auto grid min-h-[calc(100vh-2rem)] max-w-7xl gap-4 md:min-h-[calc(100vh-3rem)] md:grid-cols-[280px_minmax(0,1fr)]">
        <Sidebar onLogout={handleLogout} />
        <div className="flex min-h-0 flex-col gap-4">
          <Navbar
            title={title}
            email={state.email ?? "user@llmops.local"}
            onLogout={handleLogout}
          />
          <main
            className={cn(
              "flex-1 overflow-hidden rounded-3xl border border-white/10 bg-slate-950/55 p-4 backdrop-blur md:p-6",
              contentClassName
            )}
          >
            {children}
          </main>
        </div>
      </div>
    </div>
  );
};
