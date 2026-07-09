import React, { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { AuthLayout } from "@/layouts/AuthLayout";
import { PrimaryButton } from "@/components/app/PrimaryButton";
import { useAuth } from "@/auth/AuthContext";
import { loginUser } from "@/api/auth";
import { isAxiosError } from "axios";

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("demo@llmops.ai");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => loginUser({ email, password }),
    onSuccess: (data) => {
      login(data.access_token, email);
      navigate("/");
    },
    onError: (error: unknown) => {
      if (isAxiosError(error) && error.response?.data?.detail) {
        setErrorMessage(String(error.response.data.detail));
      } else {
        setErrorMessage("Login failed. Please try again.");
      }
    },
  });

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setErrorMessage(null);
    mutation.mutate();
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to continue to your sessions."
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-2">
          <label htmlFor="email" className="text-sm text-slate-300">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-cyan-400/50"
            placeholder="you@example.com"
            required
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="password" className="text-sm text-slate-300">
            Password
          </label>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 pr-12 text-sm text-slate-100 outline-none transition focus:border-cyan-400/50"
              placeholder="Enter password"
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword((current) => !current)}
              className="absolute inset-y-0 right-3 flex items-center text-slate-400 transition hover:text-slate-200"
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>

        {errorMessage && (
          <p className="text-sm text-red-400" role="alert">
            {errorMessage}
          </p>
        )}

        <PrimaryButton
          type="submit"
          className="w-full"
          disabled={mutation.isPending}
        >
          {mutation.isPending ? "Signing in..." : "Sign In"}
        </PrimaryButton>

        <p className="text-center text-sm text-slate-400">
          Need an account?{" "}
          <Link to="/register" className="text-cyan-300 hover:text-cyan-200">
            Register
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
};
