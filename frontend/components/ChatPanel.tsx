"use client";

import { useState } from "react";

import { sendFinancePrompt } from "@/lib/api";
import { appendHistory } from "@/lib/history";
import type { AppMode, AuthState, FinanceResponse, FinanceTask, HistoryEntry, ProviderOption } from "@/types";

import { ResponseCard } from "@/components/ResponseCard";

interface ChatPanelProps {
  auth: AuthState | null;
  mode: Exclude<AppMode, "compare">;
  task: FinanceTask;
  provider: ProviderOption;
  onModeChange: (mode: Exclude<AppMode, "compare">) => void;
  onTaskChange: (task: FinanceTask) => void;
  onProviderChange: (providerId: string) => void;
  onSaved?: (entry: HistoryEntry) => void;
}

function makeHistoryEntry(response: FinanceResponse, context?: string): HistoryEntry {
  return {
    ...response,
    sourcePrompt: response.prompt,
    context,
  };
}

export function ChatPanel({ auth, mode, task, provider, onModeChange, onTaskChange, onProviderChange, onSaved }: ChatPanelProps) {
  const [prompt, setPrompt] = useState(
    task === "qa"
      ? "What are the biggest balance-sheet and liquidity risks in the latest quarterly report?"
      : task === "risk-analysis"
        ? "Analyze the financial risks in the provided company text."
        : "Summarize the most important financial details in this excerpt.",
  );
  const [context, setContext] = useState("Revenue increased while free cash flow improved, but operating expenses and refinancing costs are still material.");
  const [temperature, setTemperature] = useState(provider.defaultTemperature);
  const [maxNewTokens, setMaxNewTokens] = useState(provider.defaultMaxNewTokens);
  const [response, setResponse] = useState<FinanceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!prompt.trim()) {
      setError("Add a prompt before submitting.");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const result = await sendFinancePrompt({
        task,
        prompt: prompt.trim(),
        context: context.trim() || undefined,
        provider,
        mode,
        accessToken: auth?.accessToken,
        temperature,
        maxNewTokens,
      });

      setResponse(result);

      const historyEntry = makeHistoryEntry(result, context.trim() || undefined);
      appendHistory(historyEntry);
      onSaved?.(historyEntry);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "The request failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
      <div className="space-y-5 rounded-[32px] border border-white/10 bg-panel/85 p-6 shadow-halo backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/70">Chat workspace</p>
            <h2 className="mt-2 text-2xl font-semibold text-white">{mode === "premium" ? "Premium route" : "Basic route"}</h2>
          </div>
          <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs tracking-[0.18em] text-slate-300">
            {provider.provider} · {provider.name}
          </div>
        </div>

        <label className="block space-y-2">
          <span className="text-sm font-medium text-slate-200">Prompt</span>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={6}
            className="w-full rounded-[24px] border border-white/10 bg-black/25 px-4 py-3 text-sm leading-7 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-400/20"
            placeholder="Ask for a summary, risk view, or financial Q&A answer..."
          />
        </label>

        <label className="block space-y-2">
          <span className="text-sm font-medium text-slate-200">Context</span>
          <textarea
            value={context}
            onChange={(event) => setContext(event.target.value)}
            rows={4}
            className="w-full rounded-[24px] border border-white/10 bg-black/25 px-4 py-3 text-sm leading-7 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-400/20"
            placeholder="Paste earnings text, memo excerpts, or other context..."
          />
        </label>

        <div className="grid gap-4 md:grid-cols-2">
          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-200">Temperature</span>
            <input
              type="range"
              min="0"
              max="1.5"
              step="0.05"
              value={temperature}
              onChange={(event) => setTemperature(Number(event.target.value))}
              className="w-full accent-cyan-400"
            />
            <p className="text-xs text-slate-400">{temperature.toFixed(2)}</p>
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-200">Max new tokens</span>
            <input
              type="range"
              min="32"
              max="1024"
              step="32"
              value={maxNewTokens}
              onChange={(event) => setMaxNewTokens(Number(event.target.value))}
              className="w-full accent-cyan-400"
            />
            <p className="text-xs text-slate-400">{maxNewTokens}</p>
          </label>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => void handleSubmit()}
            disabled={loading}
            className="rounded-2xl bg-gradient-to-r from-cyan-400 to-sky-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {loading ? "Running..." : "Run inference"}
          </button>
          <button
            type="button"
            onClick={() => {
              onModeChange(mode);
              onTaskChange(task);
            }}
            className="rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-medium text-white transition hover:border-white/20 hover:bg-white/10"
          >
            Keep settings
          </button>
          <button
            type="button"
            onClick={() => onProviderChange(provider.id)}
            className="rounded-2xl border border-white/10 bg-white/0 px-5 py-3 text-sm font-medium text-slate-300 transition hover:border-white/20 hover:bg-white/5 hover:text-white"
          >
            Refresh provider
          </button>
        </div>

        {error ? <p className="rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">{error}</p> : null}

        {!auth ? (
          <p className="rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
            No token loaded yet. The UI still works in mock mode, but live calls will need a token or API key.
          </p>
        ) : null}
      </div>

      <div className="space-y-5">
        {response ? (
          <ResponseCard response={response} />
        ) : (
          <div className="rounded-[32px] border border-white/10 bg-panel/80 p-6 shadow-halo backdrop-blur-xl">
            <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Output</p>
            <h3 className="mt-2 text-xl font-semibold text-white">Waiting for the first run</h3>
            <p className="mt-3 text-sm leading-7 text-slate-400">
              The response panel will show the generated summary, answer, or risk analysis, plus the token and latency metadata.
            </p>
          </div>
        )}

        <div className="rounded-[32px] border border-white/10 bg-white/5 p-6 text-sm text-slate-300">
          <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Current route</p>
          <p className="mt-2 text-white">{mode === "basic" ? "Basic" : "Premium"}</p>
          <p className="mt-3 leading-7">
            Basic mode is optimized for quick iterations. Premium mode leaves room for higher-quality providers and larger token budgets.
          </p>
        </div>
      </div>
    </section>
  );
}