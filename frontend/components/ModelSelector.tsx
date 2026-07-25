"use client";

import type { FinanceTask, ProviderOption, AppMode } from "@/types";
import { comparisonPairs, getProvidersByTier, tasks } from "@/lib/models";

interface ModelSelectorProps {
  mode: AppMode;
  task: FinanceTask;
  providerId: string;
  comparisonProviderId?: string;
  onModeChange: (mode: AppMode) => void;
  onTaskChange: (task: FinanceTask) => void;
  onProviderChange: (providerId: string) => void;
  onComparisonProviderChange?: (providerId: string) => void;
  providers: ProviderOption[];
}

export function ModelSelector({
  mode,
  task,
  providerId,
  comparisonProviderId,
  onModeChange,
  onTaskChange,
  onProviderChange,
  onComparisonProviderChange,
  providers,
}: ModelSelectorProps) {
  const basicProviders = getProvidersByTier("basic");
  const premiumProviders = getProvidersByTier("premium");
  const activeProvider = providers.find((provider) => provider.id === providerId) ?? providers[0];
  const activeComparisonProvider = providers.find((provider) => provider.id === comparisonProviderId) ?? providers[1] ?? providers[0];

  return (
    <section className="space-y-5 rounded-[32px] border border-white/10 bg-panel/85 p-6 shadow-halo backdrop-blur-xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/70">Workflow</p>
          <h2 className="mt-2 text-3xl font-semibold text-white">
            Choose the mode, task, and provider
          </h2>    
          <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
            Select the operating mode, finance task type, and provider route before running the configured request in Chat Workspace.
          </p>    
        </div>
        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs tracking-[0.18em] text-slate-300">
          {activeProvider.name}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {(["basic", "premium", "compare"] as AppMode[]).map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => onModeChange(item)}
            className={`rounded-2xl border px-4 py-3 text-left transition ${mode === item ? "border-cyan-300/40 bg-cyan-300/10 text-white" : "border-white/10 bg-black/10 text-slate-300 hover:border-white/20 hover:bg-white/5"}`}
          >
            <p className="text-sm font-semibold capitalize">{item}</p>
            <p className="mt-1 text-xs text-slate-400">
              {item === "basic" ? "Low-friction daily usage" : item === "premium" ? "Higher-quality provider routes" : "Side-by-side inference comparison"}
            </p>
          </button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-4 rounded-3xl border border-white/10 bg-black/15 p-4">
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Task</p>
              <p className="text-sm text-slate-300">The backend routes to summarize, QA, or risk analysis endpoints.</p>
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            {tasks.map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => onTaskChange(item.value)}
                className={`rounded-2xl border px-4 py-4 text-left transition ${task === item.value ? "border-cyan-300/40 bg-cyan-300/10 text-white" : "border-white/10 bg-white/0 text-slate-300 hover:border-white/20 hover:bg-white/5"}`}
              >
                <p className="font-semibold">{item.label}</p>
                <p className="mt-1 text-xs text-slate-400">{item.description}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-4 rounded-3xl border border-white/10 bg-black/15 p-4">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Provider</p>
            <select
              value={providerId}
              onChange={(event) => onProviderChange(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-white/10 bg-panel/95 px-4 py-3 text-sm text-white outline-none focus:border-cyan-300/50"
            >
              <optgroup label="Basic">
                {basicProviders.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.provider} · {provider.name}
                  </option>
                ))}
              </optgroup>
              <optgroup label="Premium">
                {premiumProviders.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.provider} · {provider.name}
                  </option>
                ))}
              </optgroup>
            </select>
          </div>

          {mode === "compare" && onComparisonProviderChange ? (
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Comparison provider</p>
              <select
                value={comparisonProviderId}
                onChange={(event) => onComparisonProviderChange(event.target.value)}
                className="mt-2 w-full rounded-2xl border border-white/10 bg-panel/95 px-4 py-3 text-sm text-white outline-none focus:border-cyan-300/50"
              >
                {providers.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.provider} · {provider.name}
                  </option>
                ))}
              </select>
              <div className="mt-3 rounded-2xl border border-white/10 bg-white/5 p-3 text-xs text-slate-300">
                <p className="uppercase tracking-[0.18em] text-slate-500">Preset</p>
                <p className="mt-1">{comparisonPairs.find((pair) => pair.left === providerId && pair.right === comparisonProviderId)?.label ?? "Custom pair"}</p>
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Current comparison: {activeProvider.name} vs {activeComparisonProvider.name}
              </p>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}