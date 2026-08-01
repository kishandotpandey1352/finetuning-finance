"use client";

import { useState } from "react";

import { runComparison } from "@/lib/api";
import { appendHistory } from "@/lib/history";
import type {
  AuthState,
  ComparisonResult,
  FinanceTask,
  HistoryEntry,
  ProviderOption,
} from "@/types";

import { ResponseCard } from "@/components/ResponseCard";

interface ComparePanelProps {
  auth: AuthState | null;
  task: FinanceTask;
  providers: ProviderOption[];
  leftProvider: ProviderOption;
  rightProvider: ProviderOption;
  onLeftProviderChange: (providerId: string) => void;
  onRightProviderChange: (providerId: string) => void;
  onTaskChange: (task: FinanceTask) => void;
  onSaved?: (entry: HistoryEntry) => void;
}

function toHistoryEntry(
  response: ComparisonResult["left"],
  context?: string,
): HistoryEntry {
  return {
    ...response,
    sourcePrompt: response.prompt,
    context,
  };
}

export function ComparePanel({
  auth,
  task,
  providers,
  leftProvider,
  rightProvider,
  onLeftProviderChange,
  onRightProviderChange,
  onTaskChange,
  onSaved,
}: ComparePanelProps) {
  const [prompt, setPrompt] = useState(
    "Compare the risks and outlook in the following company excerpt.",
  );
  const [context, setContext] = useState(
    "Operating cash flow improved, but debt costs remain elevated and management signaled a cautious outlook.",
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ComparisonResult | null>(null);

  async function handleCompare() {
    if (!prompt.trim()) {
      setError("Add a prompt before comparing providers.");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const comparison = await runComparison({
        prompt: prompt.trim(),
        context: context.trim() || undefined,
        leftProvider,
        rightProvider,
        task,
        accessToken: auth?.accessToken,
      });

      setResult(comparison);

      const leftEntry = toHistoryEntry(
        comparison.left,
        context.trim() || undefined,
      );
      const rightEntry = toHistoryEntry(
        comparison.right,
        context.trim() || undefined,
      );

      appendHistory(leftEntry);
      appendHistory(rightEntry);
      onSaved?.(leftEntry);
      onSaved?.(rightEntry);
    } catch (compareError) {
      setError(
        compareError instanceof Error
          ? compareError.message
          : "Comparison failed.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-6 rounded-[32px] border border-white/10 bg-panel/85 p-6 shadow-halo backdrop-blur-xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/70">
            Compare mode
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-white">
            Run the same prompt against two providers
          </h2>
        </div>

        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs tracking-[0.18em] text-slate-300">
          {leftProvider.name} vs {rightProvider.name}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <label className="block space-y-2">
          <span className="text-sm font-medium text-slate-200">Prompt</span>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={5}
            className="w-full rounded-[24px] border border-white/10 bg-black/25 px-4 py-3 text-sm leading-7 text-white outline-none transition focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-400/20"
          />
        </label>

        <label className="block space-y-2">
          <span className="text-sm font-medium text-slate-200">Context</span>
          <textarea
            value={context}
            onChange={(event) => setContext(event.target.value)}
            rows={5}
            className="w-full rounded-[24px] border border-white/10 bg-black/25 px-4 py-3 text-sm leading-7 text-white outline-none transition focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-400/20"
          />
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="block space-y-2">
          <span className="text-sm font-medium text-slate-200">
            Left provider
          </span>
          <select
            value={leftProvider.id}
            onChange={(event) => onLeftProviderChange(event.target.value)}
            className="w-full rounded-2xl border border-white/10 bg-panel px-4 py-3 text-sm text-white outline-none"
          >
            {providers.map((provider) => (
              <option key={provider.id} value={provider.id}>
                {provider.provider} · {provider.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block space-y-2">
          <span className="text-sm font-medium text-slate-200">
            Right provider
          </span>
          <select
            value={rightProvider.id}
            onChange={(event) => onRightProviderChange(event.target.value)}
            className="w-full rounded-2xl border border-white/10 bg-panel px-4 py-3 text-sm text-white outline-none"
          >
            {providers.map((provider) => (
              <option key={provider.id} value={provider.id}>
                {provider.provider} · {provider.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="flex flex-wrap gap-3">
        {(["summarize", "qa", "risk-analysis"] as FinanceTask[]).map(
          (item) => (
            <button
              key={item}
              type="button"
              onClick={() => onTaskChange(item)}
              className={`rounded-2xl border px-4 py-2 text-sm transition ${
                task === item
                  ? "border-cyan-300/40 bg-cyan-300/10 text-white"
                  : "border-white/10 bg-white/0 text-slate-300 hover:border-white/20 hover:bg-white/5"
              }`}
            >
              {item}
            </button>
          ),
        )}

        <button
          type="button"
          onClick={() => void handleCompare()}
          disabled={loading}
          className="rounded-2xl bg-gradient-to-r from-cyan-400 to-sky-500 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70"
        >
          {loading ? "Comparing..." : "Run comparison"}
        </button>
      </div>

      {error ? (
        <p className="rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          {error}
        </p>
      ) : null}

      {result ? (
        <section className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/70">
                Comparison result
              </p>
              <h3 className="text-xl font-semibold text-white">
                Side-by-side model outputs
              </h3>
            </div>

            <p className="text-sm text-slate-400">
              {result.left.provider} vs {result.right.provider}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <div className="min-w-0 [&>*]:h-full">
              <ResponseCard
                response={result.left}
                accent="from-cyan-400/40 to-sky-500/20"
              />
            </div>

            <div className="min-w-0 [&>*]:h-full">
              <ResponseCard
                response={result.right}
                accent="from-fuchsia-400/30 to-amber-400/20"
              />
            </div>
          </div>
        </section>
      ) : (
        <div className="rounded-[32px] border border-dashed border-white/15 bg-black/10 p-10 text-center text-sm text-slate-400">
          Run a comparison to see both outputs side by side.
        </div>
      )}
    </section>
  );
}