"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ComparePanel } from "@/components/ComparePanel";
import { Sidebar } from "@/components/Sidebar";
import { clearAuth, getDisplayName, loadAuth } from "@/lib/auth";
import { getProviderById, providerCatalog } from "@/lib/models";
import type { AppMode, AuthState, FinanceTask, HistoryEntry } from "@/types";

export default function ComparePage() {
  const router = useRouter();
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [task, setTask] = useState<FinanceTask>("risk-analysis");
  const [leftProviderId, setLeftProviderId] = useState("finance-adapter");
  const [rightProviderId, setRightProviderId] = useState("openai-4_1");

  useEffect(() => {
    const storedAuth = loadAuth();
    setAuth(storedAuth);
  }, []);

  function handleLogout() {
    clearAuth();
    setAuth(null);
    router.push("/login");
  }

  return (
    <main className="page-shell">
      <div className="app-grid">
        <Sidebar displayName={getDisplayName(auth)} mode="compare" onLogout={handleLogout} />

        <div className="space-y-6">
          <section className="soft-panel p-6 sm:p-8">
            <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/70">Compare</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">Side-by-side provider evaluation</h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-300">
              Choose two providers and run the same finance prompt against both. The current implementation uses the local mock fallback if the gateway is not reachable.
            </p>
          </section>

          <ComparePanel
            auth={auth}
            task={task}
            providers={providerCatalog}
            leftProvider={getProviderById(leftProviderId)}
            rightProvider={getProviderById(rightProviderId)}
            onLeftProviderChange={setLeftProviderId}
            onRightProviderChange={setRightProviderId}
            onTaskChange={setTask}
          />
        </div>
      </div>
    </main>
  );
}