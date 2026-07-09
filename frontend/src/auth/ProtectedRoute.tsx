import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

export const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { state } = useAuth();

  if (!state.token) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};