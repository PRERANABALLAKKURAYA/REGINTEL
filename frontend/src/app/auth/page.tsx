"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import Link from "next/link";

export default function AuthPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      let response;
      if (mode === "login") {
        const formData = new FormData();
        formData.append("username", email);
        formData.append("password", password);
        response = await api.post("/login/access-token", formData);
      } else {
        response = await api.post("/register", {
          email,
          name,
          password,
        });
      }

      if (response.data && response.data.access_token) {
        localStorage.setItem("token", response.data.access_token);
        console.log("Auth successful, redirecting to dashboard");
        router.push("/dashboard");
      } else {
        setError("No token received from server");
      }
    } catch (err: any) {
      // Handle various error formats
      let errorMsg = "Authentication failed";
      if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === "string") {
          errorMsg = err.response.data.detail;
        } else if (Array.isArray(err.response.data.detail)) {
          errorMsg = err.response.data.detail[0]?.msg || "Validation error";
        }
      } else if (err.response?.status === 404) {
        errorMsg = "Endpoint not found - check backend configuration";
      } else if (err.response?.status === 422) {
        errorMsg = "Invalid input - please check email and password";
      } else if (err.message) {
        errorMsg = err.message;
      }
      console.error("Auth error:", err);
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-aurora flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-grid opacity-40" />
      <div className="relative max-w-md w-full">
        <div className="card p-8 md:p-10">
          <div className="text-center mb-8">
            <p className="text-xs uppercase tracking-[0.3em] text-[var(--muted)]">RegIntel Atlas</p>
            <h1 className="mt-2 font-[var(--font-display)] text-3xl font-bold">
              {mode === "login" ? "Welcome Back" : "Join Us"}
            </h1>
            <p className="mt-2 text-sm text-[var(--muted)]">
              Global pharmaceutical regulatory intelligence
            </p>
          </div>

          <form onSubmit={handleAuth} className="space-y-4">
            {mode === "register" && (
              <div>
                <label className="block text-sm font-medium mb-2">Full Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="John Regulatory Expert"
                  className="w-full border border-black/10 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                  required
                />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium mb-2">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="w-full border border-black/10 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full border border-black/10 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700"
                >
                  {showPassword ? "👁️" : "👁️‍🗨️"}
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[var(--accent)] text-white py-2.5 rounded-xl font-semibold text-sm hover:opacity-90 disabled:opacity-50 transition"
            >
              {loading ? "Processing..." : mode === "login" ? "Sign In" : "Create Account"}
            </button>
          </form>

          <div className="mt-6 border-t border-black/10 pt-6">
            <p className="text-center text-sm text-[var(--muted)]">
              {mode === "login" ? "Don't have an account?" : "Already have an account?"}
              <button
                onClick={() => {
                  setMode(mode === "login" ? "register" : "login");
                  setError("");
                }}
                className="ml-2 text-[var(--accent)] font-semibold hover:underline"
              >
                {mode === "login" ? "Sign up" : "Sign in"}
              </button>
            </p>
          </div>

          <div className="mt-6 pt-6 border-t border-black/10 text-center text-xs text-[var(--muted)]">
            This platform is an independent regulatory intelligence tool and is not affiliated with any regulatory authority.
          </div>
        </div>
      </div>
    </div>
  );
}
