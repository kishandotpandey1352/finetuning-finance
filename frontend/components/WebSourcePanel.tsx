"use client";

import type {
  PublicWebResearchSummary,
  WebPublicCitation,
  WebPublicFinancialFact,
} from "@/lib/api";

interface WebSourcePanelProps {
  research: PublicWebResearchSummary;
}

function citationMap(citations: WebPublicCitation[]) {
  return new Map(
    citations.map((citation) => [citation.source_number, citation]),
  );
}

function factValue(fact: WebPublicFinancialFact) {
  const value =
    fact.normalized_numeric_value ?? fact.numeric_value ?? fact.raw_value;

  if (value === null || value === undefined || value === "") {
    return null;
  }

  return [
    fact.currency,
    value,
    fact.scale,
    fact.unit_label,
  ]
    .filter(Boolean)
    .join(" ");
}

function SourceCard({ citation }: { citation: WebPublicCitation }) {
  return (
    <article className="rounded-2xl border border-white/10 bg-black/20 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <a
          href={citation.url}
          target="_blank"
          rel="noopener noreferrer"
          className="min-w-0 text-sm font-semibold text-cyan-100 underline decoration-cyan-200/40 underline-offset-2 hover:text-cyan-50"
        >
          <span className="mr-2 inline-flex rounded-md border border-cyan-300/30 bg-cyan-300/10 px-1.5 py-0.5 text-[10px] font-semibold text-cyan-100">
            [Web Source {citation.source_number}]
          </span>
          <span className="break-words">{citation.title}</span>
        </a>
        <span className="shrink-0 rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2 py-1 text-[10px] font-semibold text-cyan-100">
          Web-derived
        </span>
      </div>

      <p className="mt-2 break-all text-xs text-slate-400">{citation.domain}</p>

      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-500">
        {citation.page_number ? <span>Page {citation.page_number}</span> : null}
        {citation.trust_tier ? <span>{citation.trust_tier}</span> : null}
        {citation.content_type ? <span>{citation.content_type}</span> : null}
        {citation.retrieved_at ? (
          <span>Retrieved {new Date(citation.retrieved_at).toLocaleString()}</span>
        ) : null}
      </div>

      {citation.snippet ? (
        <p className="mt-3 rounded-xl border border-white/10 bg-black/20 p-3 text-xs leading-5 text-slate-300">
          {citation.snippet}
        </p>
      ) : null}
    </article>
  );
}

function ValidatedFactCard({
  fact,
  citation,
}: {
  fact: WebPublicFinancialFact;
  citation?: WebPublicCitation;
}) {
  const value = factValue(fact);
  const validation =
    typeof fact.validation_score === "number"
      ? `${Math.round(fact.validation_score * 100)}%`
      : null;

  return (
    <article className="rounded-2xl border border-emerald-300/20 bg-emerald-300/[0.04] p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="text-sm font-semibold text-slate-100">{fact.metric_label}</p>
        <span className="rounded-full border border-emerald-300/25 bg-emerald-300/10 px-2 py-1 text-[10px] font-semibold text-emerald-100">
          Validated fact
        </span>
      </div>
      {value ? <p className="mt-2 text-lg font-semibold text-emerald-100">{value}</p> : null}
      {fact.period_label ? <p className="mt-1 text-xs text-slate-400">{fact.period_label}</p> : null}
      <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-slate-500">
        {validation ? <span>Validation {validation}</span> : null}
        {citation ? (
          <a
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-cyan-200 underline underline-offset-2 hover:text-cyan-100"
          >
            [Web Source {fact.source_number}]
          </a>
        ) : null}
      </div>
    </article>
  );
}

export function WebSourcePanel({ research }: WebSourcePanelProps) {
  const citations = research.citations ?? [];
  const facts = research.validated_facts ?? [];
  const citationByNumber = citationMap(citations);

  if (!facts.length && !citations.length) {
    return null;
  }

  return (
    <section className="overflow-hidden rounded-3xl border border-cyan-300/20 bg-slate-950/80 shadow-xl shadow-black/15">
      <div className="border-b border-white/10 px-4 py-3">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-200/80">
          Web provenance
        </p>
      </div>

      {facts.length ? (
        <div className="border-b border-white/10 p-4">
          <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-200/70">
            Validated web financial facts
          </p>
          <div className="space-y-3">
            {facts.map((fact, index) => (
              <ValidatedFactCard
                key={`${fact.source_number}-${fact.metric_label}-${index}`}
                fact={fact}
                citation={citationByNumber.get(fact.source_number)}
              />
            ))}
          </div>
        </div>
      ) : null}

      {citations.length ? (
        <div className="p-4">
          <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
            Web sources
          </p>
          <div className="space-y-3">
            {citations.map((citation) => (
              <SourceCard key={citation.source_number} citation={citation} />
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
