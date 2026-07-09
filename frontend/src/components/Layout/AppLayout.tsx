import React from "react";
import { useAuth } from "../../auth/AuthContext";
import { useNavigate } from "react-router-dom";

export const AppLayout: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { state, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-3 flex justify-between items-center">
        <h1 className="text-lg font-semibold">MultiDocChat</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">{state.email}</span>
          <button
            onClick={handleLogout}
            className="text-sm text-red-600 hover:underline"
          >
            Logout
          </button>
        </div>
      </header>
      <main className="p-6">{children}</main>
    </div>
  );
};