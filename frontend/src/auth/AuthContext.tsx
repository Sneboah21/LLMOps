/**
 * Global authentication context.
 * Stores the logged-in user's JWT and email, persists them in localStorage,
 * restores authentication on page refresh, and exposes login/logout
 * functions for use throughout the application.
 */

import React, { createContext, useContext, useState } from "react";

interface AuthState {
  token: string | null;
  email: string | null;
}

interface AuthContextValue {
  state: AuthState;
  login: (token: string, email: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [state, setState] = useState<AuthState>(() => ({
    token: localStorage.getItem("access_token"),
    email: localStorage.getItem("user_email"),
  }));

  const login = (token: string, email: string) => {
    localStorage.setItem("access_token", token);
    localStorage.setItem("user_email", email);
    setState({ token, email });
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_email");
    setState({ token: null, email: null });
  };

  return (
    <AuthContext.Provider value={{ state, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
};