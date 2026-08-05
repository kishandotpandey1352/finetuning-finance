"use client";

type MemorySuggestion = {
  is_memory_request: boolean;
  memory_type: string | null;
  memory_key: string | null;
  memory_value: string | null;
  confidence: number;
  requires_confirmation: boolean;
  reason: string | null;
  blocked: boolean;
};

export function MemorySuggestionCard({
  suggestion,
  saving,
  onSave,
  onDismiss,
}: {
  suggestion: MemorySuggestion;
  saving: boolean;
  onSave: () => void;
  onDismiss: () => void;
}) {
  if (!suggestion.is_memory_request) return null;

  if (suggestion.blocked) {
    return (
      <div className="rounded-2xl border border-amber-300/25 bg-amber-300/10 p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-amber-200/80">
              Memory not saved
            </p>
            <h3 className="mt-2 text-sm font-semibold text-amber-50">
              This may contain sensitive financial information
            </h3>
            <p className="mt-2 text-sm leading-6 text-amber-100/80">
              {suggestion.reason ??
                "This should not be stored as long-term preference memory."}
            </p>
          </div>

          <button
            type="button"
            onClick={onDismiss}
            className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-white/10"
          >
            Dismiss
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-cyan-300/25 bg-cyan-300/10 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/80">
            Save memory?
          </p>

          <h3 className="mt-2 text-sm font-semibold text-white">
            I detected a preference you may want me to remember.
          </h3>

          <div className="mt-3 rounded-xl border border-white/10 bg-black/20 p-3">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
              {suggestion.memory_type ?? "preference"}
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-100">
              {suggestion.memory_value}
            </p>
          </div>

          <p className="mt-2 text-xs leading-5 text-slate-400">
            This will only be saved after you confirm. It will affect style,
            tone, and workflow only — not financial facts.
          </p>
        </div>

        <div className="flex shrink-0 flex-wrap gap-2">
          <button
            type="button"
            onClick={onSave}
            disabled={saving}
            className="rounded-xl bg-cyan-300 px-3 py-2 text-xs font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving ? "Saving..." : "Save memory"}
          </button>

          <button
            type="button"
            onClick={onDismiss}
            disabled={saving}
            className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Not now
          </button>
        </div>
      </div>
    </div>
  );
}