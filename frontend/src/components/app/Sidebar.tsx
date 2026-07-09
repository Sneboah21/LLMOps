import React from "react";
import {
  History,
  LogOut,
  MessageSquarePlus,
  PanelLeft,
  Settings,
  Upload,
} from "lucide-react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { AppLogo } from "./AppLogo";
import { PrimaryButton } from "./PrimaryButton";
import { cn } from "@/lib/utils";

interface SidebarProps {
  onLogout: () => void;
}

const navigationItems = [
  { to: "/sessions", label: "Sessions", icon: History },
  { to: "/upload", label: "Upload", icon: Upload },
  { to: "/settings", label: "Settings", icon: Settings },
];

export const Sidebar: React.FC<SidebarProps> = ({ onLogout }) => {
  const navigate = useNavigate();

  return (
    <aside className="flex h-full flex-col rounded-3xl border border-white/10 bg-slate-950/85 p-4 backdrop-blur">
      <div className="flex items-center justify-between gap-3 border-b border-white/10 pb-4">
        <Link to="/" className="min-w-0">
          <AppLogo />
        </Link>
        <button
          type="button"
          className="rounded-2xl border border-white/10 p-2 text-slate-400 md:hidden"
          aria-label="Sidebar"
        >
          <PanelLeft className="h-4 w-4" />
        </button>
      </div>

      <PrimaryButton
        className="mt-5 w-full justify-center"
        onClick={() => navigate("/upload")}
      >
        <MessageSquarePlus className="h-4 w-4" />
        New Chat
      </PrimaryButton>

      <nav className="mt-6 flex flex-1 flex-col gap-2">
        {navigationItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-2xl px-3 py-3 text-sm text-slate-300 transition hover:bg-white/5 hover:text-white",
                isActive && "bg-white/10 text-white"
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <button
        type="button"
        onClick={onLogout}
        className="mt-6 flex items-center gap-3 rounded-2xl px-3 py-3 text-sm text-rose-300 transition hover:bg-rose-500/10"
      >
        <LogOut className="h-4 w-4" />
        Logout
      </button>
    </aside>
  );
};