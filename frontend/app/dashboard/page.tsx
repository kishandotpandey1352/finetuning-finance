"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ChatPanel } from "@/components/ChatPanel";
import { ModelSelector } from "@/components/ModelSelector";
import { Sidebar } from "@/components/Sidebar";
import { clearAuth, getDisplayName, loadAuth } from "@/lib/auth";
import { getProviderById, providerCatalog } from "@/lib/models";
import type { AppMode, AuthState, FinanceTask, HistoryEntry } from "@/types";

type DashboardTab = "dashboard" | "workflow" | "chat-workspace";

type BackendHealth = {
  status?: string;
  service?: string;
  model_id?: string;
};

type BackendReady = {
  ready?: boolean;
  model_loaded?: boolean;
  adapter_loaded?: boolean;
  model_id?: string;
};

const dashboardTabs: Array<{
  id: DashboardTab;
  label: string;
}> = [
  {
    id: "dashboard",
    label: "Dashboard",
  },
  {
    id: "workflow",
    label: "Workflow",
  },
  {
    id: "chat-workspace",
    label: "Chat Workspace",
  },
];

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8008";
const defaultApiKey = process.env.NEXT_PUBLIC_DEFAULT_API_KEY ?? "dev-finance-api-key";

function StatusPill({
  label,
  tone,
}: {
  label: string;
  tone: "good" | "warn" | "bad" | "neutral";
}) {
  const toneClass =
    tone === "good"
      ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
      : tone === "warn"
        ? "border-amber-400/30 bg-amber-400/10 text-amber-200"
        : tone === "bad"
          ? "border-rose-400/30 bg-rose-400/10 text-rose-200"
          : "border-white/10 bg-white/5 text-slate-300";

  return (
    <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${toneClass}`}>
      {label}
    </span>
  );
}

function InfoCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="frost-card p-4">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-400">{title}</p>
      <div className="mt-4 space-y-3">{children}</div>
    </div>
  );
}

function InfoRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-white/5 pb-2 last:border-b-0 last:pb-0">
      <span className="text-sm text-slate-400">{label}</span>
      <span className="max-w-[60%] break-words text-right text-sm font-semibold text-white">{value}</span>
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [mode, setMode] = useState<Exclude<AppMode, "compare">>("basic");
  const [task, setTask] = useState<FinanceTask>("summarize");
  const [providerId, setProviderId] = useState("finance-base");
  const [savedEntry, setSavedEntry] = useState<HistoryEntry | null>(null);
  const [activeTab, setActiveTab] = useState<DashboardTab>("dashboard");

  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [ready, setReady] = useState<BackendReady | null>(null);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [backendLoading, setBackendLoading] = useState(false);

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

  async function refreshBackendStatus() {
    setBackendLoading(true);
    setBackendError(null);

    try {
      const [healthResponse, readyResponse] = await Promise.all([
        fetch("/api/backend/health", {
          cache: "no-store",
        }),
        fetch("/api/backend/ready", {
          cache: "no-store",
        }),
      ]);

      if (!healthResponse.ok) {
        throw new Error(`/health returned ${healthResponse.status}`);
      }

      if (!readyResponse.ok) {
        throw new Error(`/ready returned ${readyResponse.status}`);
      }

      const healthPayload = (await healthResponse.json()) as BackendHealth;
      const readyPayload = (await readyResponse.json()) as BackendReady;

      setHealth(healthPayload);
      setReady(readyPayload);
    } catch (error) {
      setHealth(null);
      setReady(null);
      setBackendError(error instanceof Error ? error.message : "Backend status check failed");
    } finally {
      setBackendLoading(false);
    }
  }

  useEffect(() => {
  refreshBackendStatus();

  const intervalId = window.setInterval(() => {
        refreshBackendStatus();
      }, 5 * 60 * 1000);

      return () => {
        window.clearInterval(intervalId);
      };
    }, []);
                  
  function handleLogout() {
    clearAuth();
    setAuth(null);
    router.push("/login");
  }

  const provider = getProviderById(providerId);
  const displayName = getDisplayName(auth);
  const hasApiKey = Boolean(auth?.accessToken || defaultApiKey);
  const backendConnected = health?.status === "ok";
  const modelId = ready?.model_id ?? health?.model_id ?? provider.modelId;
  const lastUsage = savedEntry?.usage;

  return (
    <main className="page-shell">
      <div className="app-grid">
        <Sidebar displayName={displayName} mode={mode} onLogout={handleLogout} />

        <div className="space-y-6">
          <section className="soft-panel p-4 sm:p-5">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10">
              <div className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto">
                {dashboardTabs.map((tab) => {
                  const isActive = activeTab === tab.id;

                  return (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setActiveTab(tab.id)}
                      className={[
                        "relative whitespace-nowrap px-4 py-4 text-sm font-semibold transition",
                        isActive ? "text-cyan-200" : "text-slate-400 hover:text-white",
                      ].join(" ")}
                    >
                      {tab.label}
                      {isActive ? (
                        <span className="absolute inset-x-3 bottom-0 h-0.5 rounded-full bg-cyan-300" />
                      ) : null}
                    </button>
                  );
                })}
              </div>

              <div className="hidden rounded-full border border-white/10 bg-black/20 px-4 py-2 text-xs text-slate-400 md:block">
                {displayName}
              </div>
            </div>

            <div className="pt-6">
              {activeTab === "dashboard" ? (
                
                <section className="space-y-6">
                  <p className="mt-2 text-xs text-slate-500">
                    Backend status refreshes automatically every 5 minutes.
                  </p>
                  <div className="flex flex-wrap items-end justify-between gap-4">
                    <div>
                      <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/70">Dashboard</p>
                      <h1 className="mt-2 text-3xl font-semibold text-white">
                        Finance LLM control center
                      </h1>
                      <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
                        Check backend readiness, current workflow settings, model status, session state, and the latest inference result before running prompts.
                      </p>
                      <p className="mt-2 text-xs text-slate-500">
                        Backend status refreshes automatically every 5 minutes.
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={refreshBackendStatus}
                      disabled={backendLoading}
                      className="rounded-2xl border border-cyan-300/30 bg-cyan-300/10 px-4 py-3 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-300/20 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {backendLoading ? "Refreshing..." : "Refresh backend"}
                    </button>
                  </div>

                  <div className="grid w-full grid-cols-1 gap-4 lg:grid-cols-2">
                    <InfoCard title="Backend status">
                      <InfoRow label="API URL" value={apiBaseUrl} />
                      <InfoRow
                        label="/health status"
                        value={
                          backendError ? (
                            <StatusPill label="Error" tone="bad" />
                          ) : backendConnected ? (
                            <StatusPill label="ok" tone="good" />
                          ) : backendLoading ? (
                            <StatusPill label="Checking" tone="warn" />
                          ) : (
                            <StatusPill label="Unknown" tone="neutral" />
                          )
                        }
                      />
                      <InfoRow
                        label="/ready status"
                        value={
                          ready?.ready ? (
                            <StatusPill label="ready" tone="good" />
                          ) : ready ? (
                            <StatusPill label="not ready" tone="warn" />
                          ) : backendError ? (
                            <StatusPill label="unreachable" tone="bad" />
                          ) : (
                            <StatusPill label="Unknown" tone="neutral" />
                          )
                        }
                      />
                      {backendError ? <InfoRow label="Error" value={backendError} /> : null}
                    </InfoCard>

                    <InfoCard title="Current configuration">
                      <InfoRow label="Mode" value={<span className="capitalize">{mode}</span>} />
                      <InfoRow label="Task" value={task} />
                      <InfoRow label="Provider" value={provider.name} />
                    </InfoCard>

                    <InfoCard title="Model status">
                      <InfoRow label="Model ID" value={modelId} />
                      <InfoRow
                        label="Model loaded"
                        value={
                          ready?.model_loaded ? (
                            <StatusPill label="true" tone="good" />
                          ) : ready ? (
                            <StatusPill label="false" tone="warn" />
                          ) : (
                            <StatusPill label="Unknown" tone="neutral" />
                          )
                        }
                      />
                      <InfoRow
                        label="Adapter loaded"
                        value={
                          ready?.adapter_loaded ? (
                            <StatusPill label="true" tone="good" />
                          ) : ready ? (
                            <StatusPill label="false" tone="warn" />
                          ) : (
                            <StatusPill label="Unknown" tone="neutral" />
                          )
                        }
                      />
                    </InfoCard>

                    <InfoCard title="Session">
                      <InfoRow label="User" value={displayName} />
                      <InfoRow
                        label="API key/token present"
                        value={
                          hasApiKey ? (
                            <StatusPill label="present" tone="good" />
                          ) : (
                            <StatusPill label="missing" tone="bad" />
                          )
                        }
                      />
                    </InfoCard>

                    <InfoCard title="Last run">
                      <InfoRow
                        label="Stored output"
                        value={
                          savedEntry ? (
                            <StatusPill label="Saved" tone="good" />
                          ) : (
                            <StatusPill label="Waiting" tone="neutral" />
                          )
                        }
                      />
                      <InfoRow label="Last task" value={savedEntry?.task ?? "None yet"} />
                      <InfoRow
                        label="Latency/tokens"
                        value={
                          lastUsage
                            ? `${lastUsage.latencyMs} ms / ${lastUsage.totalTokens} tokens`
                            : "Not available"
                        }
                      />
                    </InfoCard>

                    <InfoCard title="Quick actions">
                      <div className="grid gap-3 sm:grid-cols-2">
                        <button
                          type="button"
                          onClick={() => setActiveTab("workflow")}
                          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-left text-sm font-semibold text-white transition hover:border-cyan-300/40 hover:bg-cyan-300/10"
                        >
                          Workflow
                          <span className="mt-1 block text-xs font-normal text-slate-400">
                            Choose mode, task, and provider.
                          </span>
                        </button>

                        <button
                          type="button"
                          onClick={() => setActiveTab("chat-workspace")}
                          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-left text-sm font-semibold text-white transition hover:border-cyan-300/40 hover:bg-cyan-300/10"
                        >
                          Chat Workspace
                          <span className="mt-1 block text-xs font-normal text-slate-400">
                            Run summarize, Q&A, and risk analysis.
                          </span>
                        </button>

                        <button
                          type="button"
                          onClick={() => router.push("/compare")}
                          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-left text-sm font-semibold text-white transition hover:border-cyan-300/40 hover:bg-cyan-300/10"
                        >
                          Compare
                          <span className="mt-1 block text-xs font-normal text-slate-400">
                            Compare two providers side by side.
                          </span>
                        </button>

                        <button
                          type="button"
                          onClick={() => router.push("/history")}
                          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-left text-sm font-semibold text-white transition hover:border-cyan-300/40 hover:bg-cyan-300/10"
                        >
                          History
                          <span className="mt-1 block text-xs font-normal text-slate-400">
                            Review saved inference outputs.
                          </span>
                        </button>
                      </div>
                    </InfoCard>
                  </div>
                </section>
              ) : null}

              {activeTab === "workflow" ? (
                <section>
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
                </section>
              ) : null}

              {activeTab === "chat-workspace" ? (
                <section>
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
                </section>
              ) : null}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
