import React, { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { AuthLayout } from "@/layouts/AuthLayout";
import { PrimaryButton } from "@/components/app/PrimaryButton";
import { registerUser } from "@/api/auth";

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      registerUser({
        email,
        password,
        confirm_password: confirmPassword,
      }),
    onSuccess: () => {
      navigate("/login");
    },
    onError: (error: unknown) => {
      if (isAxiosError(error) && error.response?.data?.detail) {
        setErrorMessage(String(error.response.data.detail));
      } else {
        setErrorMessage("Registration failed. Please try again.");
      }
    },
  });

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setErrorMessage(null);

    if (password !== confirmPassword) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    mutation.mutate();
  };

  return (
    <AuthLayout
      title="Create your workspace"
      subtitle="Register to start uploading documents and chatting with them."
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-2">
          <label htmlFor="register-email" className="text-sm text-slate-300">
            Email
          </label>
          <input
            id="register-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-cyan-400/50"
            placeholder="team@company.com"
            required
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="register-password" className="text-sm text-slate-300">
            Password
          </label>
          <div className="relative">
            <input
              id="register-password"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 pr-12 text-sm text-slate-100 outline-none transition focus:border-cyan-400/50"
              placeholder="Create password"
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

        <div className="space-y-2">
          <label htmlFor="register-confirm" className="text-sm text-slate-300">
            Confirm password
          </label>
          <div className="relative">
            <input
              id="register-confirm"
              type={showConfirmPassword ? "text" : "password"}
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              className="w-full rounded-2xl border border-white/10 bg-slate-900 px-4 py-3 pr-12 text-sm text-slate-100 outline-none transition focus:border-cyan-400/50"
              placeholder="Repeat password"
              required
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword((current) => !current)}
              className="absolute inset-y-0 right-3 flex items-center text-slate-400 transition hover:text-slate-200"
              aria-label={
                showConfirmPassword ? "Hide confirm password" : "Show confirm password"
              }
            >
              {showConfirmPassword ? (
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
          {mutation.isPending ? "Creating account..." : "Create Account"}
        </PrimaryButton>

        <p className="text-center text-sm text-slate-400">
          Already have an account?{" "}
          <Link to="/login" className="text-cyan-300 hover:text-cyan-200">
            Login
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
};
