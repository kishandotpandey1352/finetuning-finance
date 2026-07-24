"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ChatPanel } from "@/components/ChatPanel";
import { ModelSelector } from "@/components/ModelSelector";
import { Sidebar } from "@/components/Sidebar";
import { clearAuth, getDisplayName, loadAuth } from "@/lib/auth";
import { getProviderById, providerCatalog } from "@/lib/models";
import type { AppMode, AuthState, FinanceTask, HistoryEntry } from "@/types";

export default function DashboardPage() {
  const router = useRouter();
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [mode, setMode] = useState<Exclude<AppMode, "compare">>("basic");
  const [task, setTask] = useState<FinanceTask>("summarize");
  const [providerId, setProviderId] = useState("finance-base");
  const [savedEntry, setSavedEntry] = useState<HistoryEntry | null>(null);

  useEffect(() => {
    const storedAuth = loadAuth();
    setAuth(storedAuth);
  }, []);

  useEffect(() => {
    if (mode === "basic") {
      setProviderId("finance-base");
    }

    if (mode === "premium" && providerId === "finance-base") {
      setProviderId("finance-adapter");
    }
  }, [mode, providerId]);

  function handleLogout() {
    clearAuth();
    setAuth(null);
    router.push("/login");
  }

  const provider = getProviderById(providerId);

  return (
    <main className="page-shell">
      <div className="app-grid">
        <Sidebar displayName={getDisplayName(auth)} mode={mode} onLogout={handleLogout} />

        <div className="space-y-6">
          <section className="soft-panel p-6 sm:p-8">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/70">Dashboard</p>
                <h1 className="mt-2 text-3xl font-semibold text-white">Build, test, and compare finance prompts</h1>
                <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
                  Use the selected provider, task, and mode to drive summarization, Q&A, and risk-analysis requests through the FastAPI gateway or the mock fallback.
                </p>
              </div>
              <div className="rounded-3xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-slate-300">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Session</p>
                <p className="mt-1 text-white">{auth ? auth.displayName : "Demo mode"}</p>
              </div>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-3">
              <div className="frost-card p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Mode</p>
                <p className="mt-2 text-xl font-semibold text-white capitalize">{mode}</p>
              </div>
              <div className="frost-card p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Provider</p>
                <p className="mt-2 text-xl font-semibold text-white">{provider.name}</p>
              </div>
              <div className="frost-card p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Stored output</p>
                <p className="mt-2 text-xl font-semibold text-white">{savedEntry ? "Saved" : "Waiting"}</p>
              </div>
            </div>
          </section>

          <ModelSelector
            mode={mode}
            task={task}
            providerId={providerId}
            providers={providerCatalog}
            onModeChange={(nextMode) => {
              if (nextMode === "compare") {
                router.push("/compare");
                return;
              }

              setMode(nextMode);
            }}
            onTaskChange={setTask}
            onProviderChange={setProviderId}
          />

          <ChatPanel
            auth={auth}
            mode={mode}
            task={task}
            provider={provider}
            onModeChange={(nextMode) => setMode(nextMode)}
            onTaskChange={setTask}
            onProviderChange={setProviderId}
            onSaved={setSavedEntry}
          />
        </div>
      </div>
    </main>
  );
}