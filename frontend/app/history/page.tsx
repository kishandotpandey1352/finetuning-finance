"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ResponseCard } from "@/components/ResponseCard";
import { Sidebar } from "@/components/Sidebar";
import { clearAuth, getDisplayName, loadAuth } from "@/lib/auth";
import { clearHistory, loadHistory } from "@/lib/history";
import type { AuthState, HistoryEntry } from "@/types";

export default function HistoryPage() {
  const router = useRouter();
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    setAuth(loadAuth());
    setHistory(loadHistory());
  }, []);

  function handleRefresh() {
    setHistory(loadHistory());
  }

  function handleClear() {
    clearHistory();
    setHistory([]);
  }

  function handleLogout() {
    clearAuth();
    setAuth(null);
    router.push("/login");
  }

  return (
    <main className="page-shell">
      <div className="app-grid">
        <Sidebar displayName={getDisplayName(auth)} mode="basic" onLogout={handleLogout} />

        <div className="space-y-6">
          <section className="soft-panel flex flex-wrap items-center justify-between gap-4 p-6 sm:p-8">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/70">History</p>
              <h1 className="mt-2 text-3xl font-semibold text-white">Recent inference runs</h1>
              <p className="mt-3 text-sm leading-7 text-slate-300">
                The frontend stores recent responses locally for quick recall until the backend ships a persisted history API.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <button type="button" onClick={handleRefresh} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-white transition hover:border-white/20 hover:bg-white/10">
                Refresh
              </button>
              <button type="button" onClick={handleClear} className="rounded-2xl border border-white/10 bg-white/0 px-4 py-3 text-sm font-medium text-slate-300 transition hover:border-white/20 hover:bg-white/5 hover:text-white">
                Clear history
              </button>
            </div>
          </section>

          <div className="space-y-5">
            {history.length ? (
              history.map((entry) => <ResponseCard key={entry.id} response={entry} />)
            ) : (
              <div className="soft-panel p-10 text-center text-sm text-slate-400">
                No saved runs yet. Generate a summary or comparison and it will appear here.
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}