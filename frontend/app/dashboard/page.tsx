"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ChatPanel } from "@/components/ChatPanel";
import { Sidebar } from "@/components/Sidebar";
import { clearAuth, getDisplayName, loadAuth } from "@/lib/auth";
import { getProviderById, providerCatalog } from "@/lib/models";
import type { AppMode, AuthState, FinanceTask, HistoryEntry, ProviderOption } from "@/types";

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

function getProviderRouteLabel(provider: ProviderOption) {
  if (provider.tier === "basic") {
    return "Basic";
  }

  return "Premium";
}

export default function DashboardPage() {
  const router = useRouter();

  const [auth, setAuth] = useState<AuthState | null>(null);
  const [mode, setMode] = useState<Exclude<AppMode, "compare">>("basic");
  const [task, setTask] = useState<FinanceTask>("summarize");
  const [providerId, setProviderId] = useState("finance-base");
  const [savedEntry, setSavedEntry] = useState<HistoryEntry | null>(null);

  const [showDashboardStatus, setShowDashboardStatus] = useState(false);
  const [showWorkflowMenu, setShowWorkflowMenu] = useState(false);

  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [ready, setReady] = useState<BackendReady | null>(null);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [backendLoading, setBackendLoading] = useState(false);

  useEffect(() => {
    const storedAuth = loadAuth();
    setAuth(storedAuth);
  }, []);

  useEffect(() => {
    if (mode === "basic" && providerId !== "finance-base") {
      const selectedProvider = getProviderById(providerId);

      if (selectedProvider.tier !== "basic") {
        setProviderId("finance-base");
      }
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

  function handleProviderSelect(nextProviderId: string) {
    const nextProvider = getProviderById(nextProviderId);

    setProviderId(nextProvider.id);
    setMode(nextProvider.tier === "basic" ? "basic" : "premium");
    setShowWorkflowMenu(false);
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
            <div className="space-y-5">
              <div className="flex flex-col gap-4 border-b border-white/10 pb-5 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/70">
                    Chat Workspace
                  </p>
                  <h1 className="mt-2 text-3xl font-semibold text-white">
                    Run workflows with selected LLMs
                  </h1>
                  <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
                    Choose a model from the workflow dropdown, toggle dashboard status when needed,
                    and run summarization, Q&A, or risk-analysis prompts from one workspace.
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setShowDashboardStatus((value) => !value)}
                    className={[
                      "rounded-2xl border px-4 py-3 text-sm font-semibold transition",
                      showDashboardStatus
                        ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-100"
                        : "border-white/10 bg-white/5 text-slate-200 hover:border-cyan-300/40 hover:bg-cyan-300/10",
                    ].join(" ")}
                  >
                    {showDashboardStatus ? "Hide dashboard" : "Dashboard status"}
                  </button>

                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => setShowWorkflowMenu((value) => !value)}
                      className={[
                        "rounded-2xl border px-4 py-3 text-left text-sm font-semibold transition",
                        showWorkflowMenu
                          ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-100"
                          : "border-white/10 bg-white/5 text-slate-200 hover:border-cyan-300/40 hover:bg-cyan-300/10",
                      ].join(" ")}
                    >
                      <span className="block text-xs uppercase tracking-[0.18em] text-slate-400">
                        Workflow / Model
                      </span>
                      <span className="mt-1 block">
                        {getProviderRouteLabel(provider)} · {provider.name}
                      </span>
                    </button>

                    {showWorkflowMenu ? (
                      <div className="absolute right-0 z-30 mt-3 w-[min(92vw,420px)] overflow-hidden rounded-[28px] border border-white/10 bg-slate-950/95 p-3 shadow-halo backdrop-blur-xl">
                        <div className="mb-2 flex items-center justify-between px-2">
                          <p className="text-xs uppercase tracking-[0.22em] text-cyan-200/70">
                            Select LLM
                          </p>
                          <button
                            type="button"
                            onClick={() => setShowWorkflowMenu(false)}
                            className="text-xs font-semibold text-slate-400 transition hover:text-white"
                          >
                            Close
                          </button>
                        </div>

                        <div className="max-h-[420px] space-y-2 overflow-y-auto pr-1">
                          {providerCatalog.map((item) => {
                            const isSelected = item.id === providerId;

                            return (
                              <button
                                key={item.id}
                                type="button"
                                onClick={() => handleProviderSelect(item.id)}
                                className={[
                                  "w-full rounded-2xl border px-4 py-3 text-left transition",
                                  isSelected
                                    ? "border-cyan-300/40 bg-cyan-300/10"
                                    : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10",
                                ].join(" ")}
                              >
                                <div className="flex items-start justify-between gap-3">
                                  <div>
                                    <p className="text-sm font-semibold text-white">
                                      {item.name}
                                    </p>
                                    <p className="mt-1 text-xs text-slate-400">
                                      {item.provider} · {item.modelId}
                                    </p>
                                  </div>

                                  <span className="rounded-full border border-white/10 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-slate-300">
                                    {getProviderRouteLabel(item)}
                                  </span>
                                </div>

                                <p className="mt-2 text-xs leading-5 text-slate-400">
                                  {item.description}
                                </p>

                                <div className="mt-3 flex flex-wrap gap-2">
                                  <span className="rounded-full border border-white/10 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-slate-400">
                                    {item.costClass}
                                  </span>
                                  <span className="rounded-full border border-white/10 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-slate-400">
                                    {item.privacy}
                                  </span>
                                  <span className="rounded-full border border-white/10 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-slate-400">
                                    {item.latency}
                                  </span>
                                </div>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    ) : null}
                  </div>

                  <div className="hidden rounded-full border border-white/10 bg-black/20 px-4 py-2 text-xs text-slate-400 md:block">
                    {displayName}
                  </div>
                </div>
              </div>

              <div className="rounded-[28px] border border-cyan-300/15 bg-cyan-300/5 p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/70">
                      Current workflow
                    </p>
                    <p className="mt-2 text-sm font-semibold text-white">
                      {mode} · {task} · {provider.name}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">{provider.modelId}</p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <StatusPill
                      label={provider.enabled ? "enabled" : "disabled"}
                      tone={provider.enabled ? "good" : "warn"}
                    />
                    <StatusPill label={provider.costClass} tone="neutral" />
                    <StatusPill label={provider.privacy} tone="neutral" />
                  </div>
                </div>
              </div>

              {showDashboardStatus ? (
                <section className="space-y-5 rounded-[32px] border border-white/10 bg-black/10 p-5">
                  <div className="flex flex-wrap items-end justify-between gap-4">
                    <div>
                      <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/70">
                        Dashboard status
                      </p>
                      <h2 className="mt-2 text-2xl font-semibold text-white">
                        Finance LLM control center
                      </h2>
                      <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
                        Backend readiness, current workflow, model status, session state,
                        and latest inference metadata.
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
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}