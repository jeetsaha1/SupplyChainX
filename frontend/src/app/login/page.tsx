"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { getCurrentUser, login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const session = await login(email.trim(), password);
      const currentUser = await getCurrentUser(session.access_token);
      localStorage.setItem("scx_access_token", session.access_token);
      localStorage.setItem("scx_user", JSON.stringify(currentUser.user));
      router.push("/");
    } catch {
      setError("Login failed. Check the email and password and try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#071018] px-6 py-16 text-slate-100">
      <div className="mx-auto max-w-md">
        <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">SupplyChainX</p>
        <h1 className="mt-4 text-3xl font-semibold">Operator sign in</h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">Authenticate to access role-aware supply-chain operations.</p>
        <form className="mt-8 border border-slate-800 bg-slate-900/70 p-6" onSubmit={submit}>
          <label className="block text-sm text-slate-300">
            Email
            <input
              className="mt-2 w-full border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none focus:border-cyan-300"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label className="mt-5 block text-sm text-slate-300">
            Password
            <input
              className="mt-2 w-full border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none focus:border-cyan-300"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          {error && <p className="mt-5 border border-rose-400/30 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">{error}</p>}
          <button
            className="mt-6 w-full border border-cyan-300/50 px-4 py-2 text-sm font-medium text-cyan-200 transition hover:bg-cyan-300/10 disabled:cursor-wait disabled:opacity-50"
            type="submit"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <a className="mt-5 inline-block text-sm text-cyan-300 hover:text-cyan-200" href="/">
          Continue to public verification
        </a>
      </div>
    </main>
  );
}
