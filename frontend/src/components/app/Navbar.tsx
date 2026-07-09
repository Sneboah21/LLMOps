import React from "react";
import { LogOut } from "lucide-react";
import { SecondaryButton } from "./SecondaryButton";

interface NavbarProps {
  title: string;
  email: string;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ title, email, onLogout }) => {
  return (
    <header className="sticky top-0 z-10 flex items-center justify-between rounded-3xl border border-white/10 bg-slate-950/80 px-5 py-4 backdrop-blur">
      <div>
        <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
          Workspace
        </p>
        <h1 className="mt-1 text-2xl font-semibold text-white">{title}</h1>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden rounded-2xl border border-white/10 bg-white/5 px-4 py-2 text-right sm:block">
          <p className="text-xs text-slate-500">Signed in as</p>
          <p className="text-sm text-slate-100">{email}</p>
        </div>
        <SecondaryButton onClick={onLogout}>
          <LogOut className="h-4 w-4" />
          Logout
        </SecondaryButton>
      </div>
    </header>
  );
};
