"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ResponseCard } from "@/components/ResponseCard";
import { Sidebar } from "@/components/Sidebar";
import { clearAuth, getDisplayName, loadAuth } from "@/lib/auth";
import { clearHistory, loadHistory } from "@/lib/history";
import type { AuthState, HistoryEntry } from "@/types";

function formatFileSize(size: number) {
  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function getAttachmentLabel(kind: string) {
  if (kind === "pdf") return "PDF";
  if (kind === "docx") return "DOCX";
  if (kind === "text") return "TEXT";
  if (kind === "csv") return "CSV";
  if (kind === "image") return "IMAGE";
  return kind.toUpperCase();
}

function FilesUsedPanel({ entry }: { entry: HistoryEntry }) {
  const attachments = entry.attachments ?? [];

  if (!attachments.length) {
    return (
      <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
        <p className="text-xs uppercase tracking-[0.22em] text-slate-500">
          Files used
        </p>
        <p className="mt-2 text-sm text-slate-400">
          No attached files were used for this run.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-3xl border border-emerald-300/20 bg-emerald-300/10 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-emerald-100/70">
            Files used
          </p>
          <p className="mt-1 text-sm text-slate-300">
            {attachments.length} attachment
            {attachments.length === 1 ? "" : "s"} included in this query.
          </p>
        </div>

        <span className="rounded-full border border-emerald-300/20 bg-black/20 px-3 py-1 text-xs font-semibold text-emerald-100">
          Document-aware run
        </span>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {attachments.map((attachment) => (
          <div
            key={attachment.id}
            className="rounded-2xl border border-white/10 bg-black/25 px-4 py-3"
            title={`${attachment.name} · ${attachment.type}`}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">
                  {attachment.name}
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  {getAttachmentLabel(attachment.kind)} ·{" "}
                  {formatFileSize(attachment.size)}
                  {attachment.pageCount
                    ? ` · ${attachment.pageCount} pages`
                    : ""}
                </p>
              </div>

              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] font-semibold text-slate-300">
                {getAttachmentLabel(attachment.kind)}
              </span>
            </div>

            <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
              {typeof attachment.extractedChars === "number" ? (
                <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-slate-300">
                  {attachment.extractedChars.toLocaleString()} extracted chars
                </span>
              ) : null}

              {attachment.truncated ? (
                <span className="rounded-full border border-amber-300/20 bg-amber-300/10 px-2.5 py-1 text-amber-100">
                  Truncated
                </span>
              ) : (
                <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-2.5 py-1 text-emerald-100">
                  Full extract
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

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

  const totalAttachments = history.reduce(
    (count, entry) => count + (entry.attachments?.length ?? 0),
    0,
  );

  return (
    <main className="page-shell">
      <div className="app-grid">
        <Sidebar
          displayName={getDisplayName(auth)}
          mode="basic"
          onLogout={handleLogout}
        />

        <div className="space-y-6">
          <section className="soft-panel flex flex-wrap items-center justify-between gap-4 p-6 sm:p-8">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-emerald-200/70">
                History
              </p>
              <h1 className="mt-2 text-3xl font-semibold text-white">
                Recent inference runs
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-300">
                Review recent finance AI runs, including the model response and
                the files that were attached to each query. File contents are
                not stored here, only safe attachment metadata.
              </p>

              <div className="mt-4 flex flex-wrap gap-3 text-xs">
                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-slate-300">
                  {history.length} saved run{history.length === 1 ? "" : "s"}
                </span>
                <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1 text-emerald-100">
                  {totalAttachments} file reference
                  {totalAttachments === 1 ? "" : "s"}
                </span>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleRefresh}
                className="rounded-2xl border border-emerald-300/20 bg-emerald-300/10 px-4 py-3 text-sm font-medium text-emerald-50 transition hover:border-emerald-200/40 hover:bg-emerald-300/20"
              >
                Refresh
              </button>
              <button
                type="button"
                onClick={handleClear}
                className="rounded-2xl border border-white/10 bg-white/0 px-4 py-3 text-sm font-medium text-slate-300 transition hover:border-white/20 hover:bg-white/5 hover:text-white"
              >
                Clear history
              </button>
            </div>
          </section>

          <div className="space-y-5">
            {history.length ? (
              history.map((entry) => (
                <section key={entry.id} className="space-y-4">
                  <FilesUsedPanel entry={entry} />
                  <ResponseCard response={entry} />
                </section>
              ))
            ) : (
              <div className="soft-panel p-10 text-center text-sm text-slate-400">
                No saved runs yet. Generate a summary, Q&A answer, risk
                analysis, or comparison and it will appear here.
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}