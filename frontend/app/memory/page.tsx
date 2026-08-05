"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/Sidebar";
import { clearAuth, getDisplayName, loadAuth } from "@/lib/auth";
import type { AuthState } from "@/types";

type UserMemoryType =
  | "answer_style"
  | "chart_preference"
  | "domain_focus"
  | "risk_tone"
  | "provider_preference";

type UserMemoryRecord = {
  id: string;
  user_id: string;
  memory_type: UserMemoryType;
  memory_key: string;
  memory_value: string;
  confidence: number;
  source: string;
  status: "proposed" | "active" | "deleted";
  is_active: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  confirmed_at?: string | null;
  deleted_at?: string | null;
};

type MemoryListResponse = {
  ok: boolean;
  memories?: UserMemoryRecord[];
  error?: string;
};

const memoryTypeOptions: {
  value: UserMemoryType;
  label: string;
  description: string;
  defaultKey: string;
  defaultValue: string;
}[] = [
  {
    value: "answer_style",
    label: "Answer style",
    description: "How responses should be written.",
    defaultKey: "preferred_response_style",
    defaultValue:
      "Prefer concise finance answers with clear bullets and tables when useful.",
  },
  {
    value: "chart_preference",
    label: "Chart preference",
    description: "Preferred chart types for trends, comparisons, and ratios.",
    defaultKey: "preferred_chart_style",
    defaultValue:
      "Prefer line charts for trends and bar charts for company comparisons.",
  },
  {
    value: "domain_focus",
    label: "Domain focus",
    description: "General finance topics you often analyze.",
    defaultKey: "common_analysis_focus",
    defaultValue:
      "Often focuses on annual reports, revenue growth, margins, liquidity, and risk factors.",
  },
  {
    value: "risk_tone",
    label: "Risk tone",
    description: "How conservative or direct risk explanations should be.",
    defaultKey: "preferred_risk_tone",
    defaultValue:
      "Prefer conservative risk language and avoid overstating financial conclusions.",
  },
  {
    value: "provider_preference",
    label: "Provider preference",
    description: "Cost, speed, or quality preference for model routing.",
    defaultKey: "preferred_provider_routing",
    defaultValue:
      "Prefer cheaper premium providers unless higher quality is needed.",
  },
];

function getMemoryTypeLabel(type: UserMemoryType) {
  return (
    memoryTypeOptions.find((option) => option.value === type)?.label ?? type
  );
}

function formatDate(value?: string | null) {
  if (!value) return "Not confirmed";

  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function MiniPill({
  children,
  tone = "slate",
}: {
  children: React.ReactNode;
  tone?: "emerald" | "cyan" | "amber" | "rose" | "slate";
}) {
  const toneClass =
    tone === "emerald"
      ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100"
      : tone === "cyan"
        ? "border-cyan-300/20 bg-cyan-300/10 text-cyan-100"
        : tone === "amber"
          ? "border-amber-300/20 bg-amber-300/10 text-amber-100"
          : tone === "rose"
            ? "border-rose-300/20 bg-rose-300/10 text-rose-100"
            : "border-white/10 bg-white/5 text-slate-300";

  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold ${toneClass}`}
    >
      {children}
    </span>
  );
}

export default function MemoryPage() {
  const router = useRouter();

  const [auth, setAuth] = useState<AuthState | null>(null);
  const [memories, setMemories] = useState<UserMemoryRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const [memoryType, setMemoryType] =
    useState<UserMemoryType>("answer_style");
  const [memoryKey, setMemoryKey] = useState("preferred_response_style");
  const [memoryValue, setMemoryValue] = useState(
    "Prefer concise finance answers with clear bullets and tables when useful.",
  );

  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    setAuth(loadAuth());
    void loadMemories();
  }, []);

  const activeMemories = useMemo(
    () =>
      memories.filter(
        (memory) => memory.status === "active" && memory.is_active,
      ),
    [memories],
  );

  const proposedMemories = useMemo(
    () => memories.filter((memory) => memory.status === "proposed"),
    [memories],
  );

  function handleMemoryTypeChange(nextType: UserMemoryType) {
    const option = memoryTypeOptions.find((item) => item.value === nextType);

    setMemoryType(nextType);

    if (option) {
      setMemoryKey(option.defaultKey);
      setMemoryValue(option.defaultValue);
    }
  }

  async function loadMemories() {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/agent-memory/list", {
        cache: "no-store",
      });

      const payload = (await response.json()) as MemoryListResponse;

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ?? "Failed to load memory.");
      }

      setMemories(payload.memories ?? []);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Failed to load memory.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function proposeMemory() {
    setSaving(true);
    setError(null);
    setStatusMessage(null);

    try {
      const response = await fetch("/api/agent-memory/propose", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          memory_type: memoryType,
          memory_key: memoryKey,
          memory_value: memoryValue,
          confidence: 0.8,
          source: "user-entered",
          metadata: {
            created_from: "next_memory_center",
          },
        }),
      });

      const payload = (await response.json()) as {
        ok: boolean;
        error?: string;
        detail?: string;
      };

      if (!response.ok || !payload.ok) {
        throw new Error(
          payload.error ?? payload.detail ?? "Failed to propose memory.",
        );
      }

      setStatusMessage(
        "Memory proposed. Confirm it before the app can use it.",
      );
      await loadMemories();
    } catch (saveError) {
      setError(
        saveError instanceof Error
          ? saveError.message
          : "Failed to propose memory.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function confirmMemory(memoryId: string) {
    setError(null);
    setStatusMessage(null);

    try {
      const response = await fetch("/api/agent-memory/confirm", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          memory_id: memoryId,
        }),
      });

      const payload = (await response.json()) as {
        ok: boolean;
        error?: string;
        detail?: string;
      };

      if (!response.ok || !payload.ok) {
        throw new Error(
          payload.error ?? payload.detail ?? "Failed to confirm memory.",
        );
      }

      setStatusMessage("Memory confirmed and active.");
      await loadMemories();
    } catch (confirmError) {
      setError(
        confirmError instanceof Error
          ? confirmError.message
          : "Failed to confirm memory.",
      );
    }
  }

  async function deleteMemory(memoryId: string) {
    const confirmed = window.confirm("Delete this saved memory?");

    if (!confirmed) return;

    setError(null);
    setStatusMessage(null);

    try {
      const response = await fetch("/api/agent-memory/delete", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          memory_id: memoryId,
        }),
      });

      const payload = (await response.json()) as {
        ok: boolean;
        error?: string;
        detail?: string;
      };

      if (!response.ok || !payload.ok) {
        throw new Error(
          payload.error ?? payload.detail ?? "Failed to delete memory.",
        );
      }

      setStatusMessage("Memory deleted.");
      await loadMemories();
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "Failed to delete memory.",
      );
    }
  }

  function handleLogout() {
    clearAuth();
    setAuth(null);
    router.push("/login");
  }

  return (
    <main className="page-shell">
      <div className="app-grid">
        <Sidebar
          displayName={getDisplayName(auth)}
          mode="basic"
          onLogout={handleLogout}
        />

        <div className="mx-auto w-full max-w-7xl space-y-4 px-3 pb-8">
          <section className="rounded-3xl border border-white/10 bg-slate-950/80 p-5 shadow-xl shadow-black/20">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="max-w-3xl">
                <p className="text-xs uppercase tracking-[0.24em] text-cyan-200/70">
                  Memory Center
                </p>

                <h1 className="mt-2 text-2xl font-semibold text-white">
                  User-approved finance preferences
                </h1>

                <p className="mt-2 text-sm leading-6 text-slate-300">
                  Save only stable preferences that you explicitly approve. This
                  memory lives in the FastAPI agent service and is separate from
                  document memory.
                </p>

                <div className="mt-3 flex flex-wrap gap-2">
                  <MiniPill tone="emerald">
                    {activeMemories.length} active
                  </MiniPill>
                  <MiniPill tone="amber">
                    {proposedMemories.length} proposed
                  </MiniPill>
                  <MiniPill>Explicit approval required</MiniPill>
                </div>
              </div>

              <button
                type="button"
                onClick={() => void loadMemories()}
                disabled={loading}
                className="rounded-xl border border-cyan-300/20 bg-cyan-300/10 px-4 py-2.5 text-sm font-semibold text-cyan-50 transition hover:border-cyan-200/40 hover:bg-cyan-300/20 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Refreshing..." : "Refresh"}
              </button>
            </div>
          </section>

          {error ? (
            <p className="rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
              {error}
            </p>
          ) : null}

          {statusMessage ? (
            <p className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
              {statusMessage}
            </p>
          ) : null}

          <div className="grid gap-4 lg:grid-cols-[390px_minmax(0,1fr)]">
            <section className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15">
              <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/70">
                Propose Memory
              </p>

              <h2 className="mt-2 text-lg font-semibold text-white">
                Add a preference
              </h2>

              <p className="mt-1 text-sm leading-6 text-slate-400">
                A proposed memory is not used by agents until you confirm it.
              </p>

              <div className="mt-4 space-y-4">
                <label className="block space-y-2">
                  <span className="text-sm font-semibold text-slate-200">
                    Memory type
                  </span>
                  <select
                    value={memoryType}
                    onChange={(event) =>
                      handleMemoryTypeChange(
                        event.target.value as UserMemoryType,
                      )
                    }
                    className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-white outline-none focus:border-cyan-300/40"
                  >
                    {memoryTypeOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs leading-5 text-slate-500">
                    {
                      memoryTypeOptions.find(
                        (option) => option.value === memoryType,
                      )?.description
                    }
                  </p>
                </label>

                <label className="block space-y-2">
                  <span className="text-sm font-semibold text-slate-200">
                    Memory key
                  </span>
                  <input
                    value={memoryKey}
                    onChange={(event) => setMemoryKey(event.target.value)}
                    className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-300/40"
                    placeholder="preferred_response_style"
                  />
                </label>

                <label className="block space-y-2">
                  <span className="text-sm font-semibold text-slate-200">
                    Preference
                  </span>
                  <textarea
                    value={memoryValue}
                    onChange={(event) => setMemoryValue(event.target.value)}
                    rows={5}
                    className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 text-sm leading-6 text-white outline-none placeholder:text-slate-500 focus:border-cyan-300/40"
                    placeholder="Example: Prefer concise answers with tables and charts when helpful."
                  />
                </label>

                <button
                  type="button"
                  onClick={() => void proposeMemory()}
                  disabled={saving}
                  className="w-full rounded-xl bg-cyan-300 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {saving ? "Saving..." : "Propose memory"}
                </button>
              </div>
            </section>

            <section className="space-y-4">
              <div className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-emerald-200/70">
                      Active Memories
                    </p>
                    <h2 className="mt-2 text-lg font-semibold text-white">
                      Confirmed preferences used by agents
                    </h2>
                  </div>

                  <MiniPill tone="emerald">
                    {activeMemories.length} active
                  </MiniPill>
                </div>

                <div className="mt-4 space-y-3">
                  {activeMemories.length ? (
                    activeMemories.map((memory) => (
                      <div
                        key={memory.id}
                        className="rounded-2xl border border-emerald-300/20 bg-emerald-300/10 p-3"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex flex-wrap gap-2">
                              <MiniPill tone="emerald">Active</MiniPill>
                              <MiniPill>
                                {getMemoryTypeLabel(memory.memory_type)}
                              </MiniPill>
                            </div>

                            <p className="mt-3 text-sm font-semibold text-white">
                              {memory.memory_value}
                            </p>

                            <p className="mt-2 text-xs text-slate-400">
                              Key: {memory.memory_key} · Confirmed:{" "}
                              {formatDate(memory.confirmed_at)}
                            </p>
                          </div>

                          <button
                            type="button"
                            onClick={() => void deleteMemory(memory.id)}
                            className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-xs font-semibold text-slate-300 transition hover:border-rose-300/30 hover:bg-rose-300/10 hover:text-rose-100"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-2xl border border-dashed border-white/15 bg-black/20 p-6 text-center">
                      <p className="text-sm font-medium text-slate-300">
                        No active memories yet.
                      </p>
                      <p className="mt-2 text-xs leading-5 text-slate-500">
                        Propose a memory and confirm it before agents can use
                        it.
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <div className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-amber-200/70">
                      Proposed Memories
                    </p>
                    <h2 className="mt-2 text-lg font-semibold text-white">
                      Waiting for confirmation
                    </h2>
                  </div>

                  <MiniPill tone="amber">
                    {proposedMemories.length} proposed
                  </MiniPill>
                </div>

                <div className="mt-4 space-y-3">
                  {proposedMemories.length ? (
                    proposedMemories.map((memory) => (
                      <div
                        key={memory.id}
                        className="rounded-2xl border border-amber-300/20 bg-amber-300/10 p-3"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex flex-wrap gap-2">
                              <MiniPill tone="amber">Needs approval</MiniPill>
                              <MiniPill>
                                {getMemoryTypeLabel(memory.memory_type)}
                              </MiniPill>
                            </div>

                            <p className="mt-3 text-sm font-semibold text-white">
                              {memory.memory_value}
                            </p>

                            <p className="mt-2 text-xs text-slate-400">
                              Key: {memory.memory_key} · Proposed:{" "}
                              {formatDate(memory.created_at)}
                            </p>
                          </div>

                          <div className="flex flex-wrap gap-2">
                            <button
                              type="button"
                              onClick={() => void confirmMemory(memory.id)}
                              className="rounded-xl border border-emerald-300/30 bg-emerald-300/10 px-3 py-2 text-xs font-semibold text-emerald-100 transition hover:bg-emerald-300/20"
                            >
                              Confirm
                            </button>

                            <button
                              type="button"
                              onClick={() => void deleteMemory(memory.id)}
                              className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-xs font-semibold text-slate-300 transition hover:border-rose-300/30 hover:bg-rose-300/10 hover:text-rose-100"
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-2xl border border-dashed border-white/15 bg-black/20 p-6 text-center">
                      <p className="text-sm font-medium text-slate-300">
                        No proposed memories.
                      </p>
                      <p className="mt-2 text-xs leading-5 text-slate-500">
                        New memory suggestions will appear here before they are
                        allowed to influence agent answers.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}