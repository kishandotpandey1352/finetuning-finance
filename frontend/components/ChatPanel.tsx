"use client";

import { useEffect, useState } from "react";

import { ResponseCard } from "@/components/ResponseCard";
import { sendFinancePrompt } from "@/lib/api";
import { appendHistory } from "@/lib/history";
import type {
  AppMode,
  AuthState,
  FinanceResponse,
  FinanceTask,
  HistoryEntry,
  ProviderOption,
} from "@/types";

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

const taskCopy: Record<
  FinanceTask,
  {
    route: string;
    primaryLabel: string;
    primaryPlaceholder: string;
    secondaryLabel: string;
    secondaryPlaceholder: string;
    defaultPrompt: string;
    defaultContext: string;
    runLabel: string;
    helperText: string;
  }
> = {
  summarize: {
    route: "POST /summarize",
    primaryLabel: "Text to summarize",
    primaryPlaceholder:
      "Paste the financial text, earnings update, filing excerpt, or news paragraph you want summarized...",
    secondaryLabel: "Optional instructions",
    secondaryPlaceholder:
      "Example: Summarize in 3 bullets, focus on revenue and margin trends, keep it executive-friendly...",
    defaultPrompt:
      "Revenue increased 12 percent, but margins declined because input costs and interest expense rose. Operating cash flow improved, while management warned that higher interest rates may pressure demand next quarter.",
    defaultContext:
      "Summarize in 3 concise bullets. Focus on revenue growth, margin pressure, cash flow, and forward-looking risks.",
    runLabel: "Run summarization",
    helperText:
      "Use this when you want a concise summary of a financial update, filing excerpt, earnings paragraph, or market note.",
  },
  qa: {
    route: "POST /qa",
    primaryLabel: "Question",
    primaryPlaceholder:
      "Ask a question about the financial context, for example: What caused margin pressure?",
    secondaryLabel: "Context",
    secondaryPlaceholder:
      "Paste the source material the model should use to answer the question...",
    defaultPrompt:
      "What caused margin pressure, and what should investors monitor next quarter?",
    defaultContext:
      "Revenue increased 12 percent, but margins declined because input costs and interest expense rose. Operating cash flow improved, while management warned that higher interest rates may pressure demand next quarter.",
    runLabel: "Run Q&A",
    helperText:
      "Use this when you have source material and want the model to answer a specific finance question from that context.",
  },
  "risk-analysis": {
    route: "POST /risk-analysis",
    primaryLabel: "Text to analyze",
    primaryPlaceholder:
      "Paste the company update, filing excerpt, earnings commentary, or financial disclosure to analyze for risks...",
    secondaryLabel: "Optional risk focus",
    secondaryPlaceholder:
      "Example: Focus on liquidity risk, margin pressure, interest expense, refinancing risk, or demand slowdown...",
    defaultPrompt:
      "The company has rising revenue, declining margins, higher interest expense, improved operating cash flow, and a weaker demand outlook for next quarter.",
    defaultContext:
      "Focus on liquidity risk, margin pressure, interest expense, refinancing risk, and demand slowdown.",
    runLabel: "Run risk analysis",
    helperText:
      "Use this when you want the model to identify financial, operating, liquidity, demand, or refinancing risks.",
  },
};

function makeHistoryEntry(
  response: FinanceResponse,
  context?: string,
): HistoryEntry {
  return {
    ...response,
    sourcePrompt: response.prompt,
    context,
  };
}

function getTaskLabel(task: FinanceTask) {
  if (task === "summarize") {
    return "Summarize";
  }

  if (task === "qa") {
    return "Q&A";
  }

  return "Risk Analysis";
}

export function ChatPanel({
  auth,
  mode,
  task,
  provider,
  onModeChange,
  onTaskChange,
  onProviderChange,
  onSaved,
}: ChatPanelProps) {
  const currentTaskCopy = taskCopy[task];

  const [prompt, setPrompt] = useState(currentTaskCopy.defaultPrompt);
  const [context, setContext] = useState(currentTaskCopy.defaultContext);
  const [temperature, setTemperature] = useState(provider.defaultTemperature);
  const [maxNewTokens, setMaxNewTokens] = useState(
    provider.defaultMaxNewTokens,
  );
  const [response, setResponse] = useState<FinanceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPrompt(taskCopy[task].defaultPrompt);
    setContext(taskCopy[task].defaultContext);
    setResponse(null);
    setError(null);
  }, [task]);

  useEffect(() => {
    setTemperature(provider.defaultTemperature);
    setMaxNewTokens(provider.defaultMaxNewTokens);
  }, [provider.defaultTemperature, provider.defaultMaxNewTokens]);

  async function handleSubmit() {
    if (!prompt.trim()) {
      setError(
        `Add ${currentTaskCopy.primaryLabel.toLowerCase()} before submitting.`,
      );
      return;
    }

    if (task === "qa" && !context.trim()) {
      setError("Add context before running Q&A.");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const result = await sendFinancePrompt({
        task,
        prompt,
        context,
        provider,
        mode,
        accessToken: auth?.accessToken,
        temperature,
        maxNewTokens,
      });

      setResponse(result);

      const historyEntry = makeHistoryEntry(
        result,
        context.trim() || undefined,
      );
      appendHistory(historyEntry);
      onSaved?.(historyEntry);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "The request failed.",
      );
    } finally {
      setLoading(false);
    }
  }

  function handleClear() {
    setPrompt("");
    setContext("");
    setResponse(null);
    setError(null);
  }

  function handleLoadExample() {
    setPrompt(currentTaskCopy.defaultPrompt);
    setContext(currentTaskCopy.defaultContext);
    setResponse(null);
    setError(null);
  }

  return (
    <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
      <div className="space-y-5 rounded-[32px] border border-white/10 bg-panel/85 p-6 shadow-halo backdrop-blur-xl">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/70">
            Prompt console
          </p>
          <h2 className="mt-2 text-3xl font-semibold text-white">
            Run the selected finance task
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
            Enter finance text, add instructions or context, and run the selected
            task with the model chosen from the workflow dropdown.
          </p>
        </div>

        <div className="space-y-3 rounded-3xl border border-white/10 bg-black/20 p-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-cyan-200/70">
              Finance task
            </p>
            <p className="mt-1 text-sm text-slate-400">
              Choose what the selected model should do with your finance input.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            {(["summarize", "qa", "risk-analysis"] as FinanceTask[]).map(
              (item) => {
                const isActive = task === item;

                return (
                  <button
                    key={item}
                    type="button"
                    onClick={() => onTaskChange(item)}
                    className={[
                      "rounded-2xl border px-5 py-2.5 text-sm font-semibold transition",
                      isActive
                        ? "border-cyan-300/50 bg-cyan-300/15 text-cyan-50 shadow-[0_0_24px_rgba(103,232,249,0.12)]"
                        : "border-white/10 bg-white/0 text-slate-300 hover:border-cyan-300/30 hover:bg-cyan-300/10 hover:text-white",
                    ].join(" ")}
                  >
                    {getTaskLabel(item)}
                  </button>
                );
              },
            )}
          </div>
        </div>

        <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
          <p className="text-xs uppercase tracking-[0.22em] text-slate-500">
            Task guidance
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            {currentTaskCopy.helperText}
          </p>
        </div>

        <label className="block space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-sm font-medium text-slate-200">
              {currentTaskCopy.primaryLabel}
            </span>
            <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-slate-400">
              Required
            </span>
          </div>

          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={7}
            className="w-full rounded-[24px] border border-white/10 bg-black/25 px-4 py-3 text-sm leading-7 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-400/20"
            placeholder={currentTaskCopy.primaryPlaceholder}
          />
        </label>

        <label className="block space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-sm font-medium text-slate-200">
              {currentTaskCopy.secondaryLabel}
            </span>
            <span
              className={[
                "rounded-full border px-3 py-1 text-xs",
                task === "qa"
                  ? "border-amber-300/30 bg-amber-300/10 text-amber-100"
                  : "border-white/10 bg-black/20 text-slate-400",
              ].join(" ")}
            >
              {task === "qa" ? "Required for Q&A" : "Optional"}
            </span>
          </div>

          <textarea
            value={context}
            onChange={(event) => setContext(event.target.value)}
            rows={5}
            className="w-full rounded-[24px] border border-white/10 bg-black/25 px-4 py-3 text-sm leading-7 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-400/20"
            placeholder={currentTaskCopy.secondaryPlaceholder}
          />
        </label>

        <div className="grid gap-4 md:grid-cols-2">
          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-200">
              Temperature
            </span>
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
            <span className="text-sm font-medium text-slate-200">
              Max new tokens
            </span>
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
            {loading ? "Running..." : currentTaskCopy.runLabel}
          </button>

          <button
            type="button"
            onClick={handleLoadExample}
            disabled={loading}
            className="rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-medium text-white transition hover:border-white/20 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-70"
          >
            Load example
          </button>

          <button
            type="button"
            onClick={handleClear}
            disabled={loading}
            className="rounded-2xl border border-white/10 bg-white/0 px-5 py-3 text-sm font-medium text-slate-300 transition hover:border-white/20 hover:bg-white/5 hover:text-white disabled:cursor-not-allowed disabled:opacity-70"
          >
            Clear
          </button>

          <button
            type="button"
            onClick={() => {
              onModeChange(mode);
              onTaskChange(task);
              onProviderChange(provider.id);
            }}
            disabled={loading}
            className="rounded-2xl border border-white/10 bg-white/0 px-5 py-3 text-sm font-medium text-slate-300 transition hover:border-white/20 hover:bg-white/5 hover:text-white disabled:cursor-not-allowed disabled:opacity-70"
          >
            Keep settings
          </button>
        </div>

        {error ? (
          <p className="rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
            {error}
          </p>
        ) : null}
      </div>

      <div className="space-y-5">
        {response ? (
          <ResponseCard response={response} />
        ) : (
          <div className="rounded-[32px] border border-white/10 bg-panel/80 p-6 shadow-halo backdrop-blur-xl">
            <p className="text-xs uppercase tracking-[0.28em] text-slate-400">
              Output
            </p>
            <h3 className="mt-2 text-xl font-semibold text-white">
              Waiting for the first run
            </h3>
            <p className="mt-3 text-sm leading-7 text-slate-400">
              The response panel will show the generated summary, answer, or
              risk analysis, plus token and latency metadata.
            </p>
          </div>
        )}

        <div className="rounded-[32px] border border-white/10 bg-white/5 p-6 text-sm text-slate-300">
          <p className="text-xs uppercase tracking-[0.28em] text-slate-400">
            Current route
          </p>
          <p className="mt-2 text-white">{currentTaskCopy.route}</p>
          <p className="mt-3 leading-7">
            {mode === "basic" ? "Basic" : "Premium"} mode will run the selected{" "}
            <span className="font-semibold text-white">{getTaskLabel(task)}</span>{" "}
            task through{" "}
            <span className="font-semibold text-white">{provider.name}</span>.
          </p>
        </div>
      </div>
    </section>
  );
}