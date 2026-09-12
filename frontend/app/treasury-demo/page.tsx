"use client";

import { useMemo, useState } from "react";
import styles from "./page.module.css";

type Scenario =
  | "normal"
  | "shortfall"
  | "stale"
  | "tool_failure"
  | "unauthorized_tool";

type TraceEvent = {
  sequence: number;
  event_type: string;
  task_id: string | null;
  state: string | null;
  detail: string;
  retry_count: number;
  evidence_ids: string[];
};

type AICommentary = {
  status: "generated" | "disabled" | "error" | "not_requested";
  provider: string | null;
  model: string | null;
  prompt_version: string | null;
  latency_ms: number;
  summary: string | null;
  message: string | null;
  read_only: boolean;
  input_scope: string;
};

type DemoResponse = {
  scenario: Scenario;
  run_state: string;
  workflow_state: string | null;
  latency_ms: number;
  task_states: Record<string, string>;
  retry_counts: Record<string, number>;
  variance: Record<
    string,
    {
      available: number;
      required_liquidity: number;
      scheduled_outflows: number;
      projected_requirement: number;
      projected_shortfall: number;
      shortfall_detected: boolean;
      evidence_ids: string[];
    }
  >;
  funding_recommendations: Array<{
    destination_currency: string;
    recommendation: string;
    required_amount: number;
    source_currency: string | null;
    source_available_surplus: number;
    source_capacity_sufficient: boolean;
    unfunded_amount: number;
    reason: string;
    evidence_ids: string[];
  }>;
  approval: null | {
    workflow_state: string;
    decisions: Array<{
      destination_currency: string;
      source_currency: string | null;
      required_amount: number;
      decision: string;
      reason: string;
      evidence_ids: string[];
    }>;
    evidence_ids: string[];
  };
  failure: null | {
    code: string;
    message: string;
    retry_count: number;
    failed_task: string | null;
    evidence_ids: string[];
  };
  trace: TraceEvent[];
  ai_commentary: AICommentary;
};

const scenarios: Array<{
  value: Scenario;
  label: string;
  description: string;
}> = [
  {
    value: "normal",
    label: "Normal liquidity",
    description: "Healthy liquidity. No funding action required.",
  },
  {
    value: "shortfall",
    label: "EUR shortfall",
    description: "High-value shortfall routed to human approval.",
  },
  {
    value: "stale",
    label: "Stale balance data",
    description: "Freshness guard blocks downstream reasoning.",
  },
  {
    value: "tool_failure",
    label: "Settlement 503",
    description: "Bounded retries, then failed dependency propagation.",
  },
  {
    value: "unauthorized_tool",
    label: "Unauthorized capability",
    description: "Least-privilege guard rejects execution.",
  },
];

const API_BASE =
  process.env.NEXT_PUBLIC_AGENT_SERVICE_URL || "http://localhost:8010";

const taskLabels: Record<string, string> = {
  cash_position: "Cash Position",
  obligations: "Obligations",
  variance: "Variance / Reconciliation",
  funding_recommendation: "Funding Recommendation",
  approval_gate: "Approval Gate",
};

function money(value: number | undefined, currency = "GBP") {
  if (value === undefined) return "—";
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

function statusClass(state: string | undefined) {
  const normalized = (state || "").toLowerCase();
  if (
    normalized.includes("completed") ||
    normalized.includes("generated") ||
    normalized.includes("no_action") ||
    normalized.includes("auto_allowed")
  ) {
    return styles.good;
  }
  if (
    normalized.includes("waiting") ||
    normalized.includes("retry") ||
    normalized.includes("disabled")
  ) {
    return styles.warn;
  }
  if (
    normalized.includes("failed") ||
    normalized.includes("error") ||
    normalized.includes("blocked") ||
    normalized.includes("unauthorized") ||
    normalized.includes("stale")
  ) {
    return styles.bad;
  }
  if (
    normalized.includes("skipped") ||
    normalized.includes("not_requested")
  ) {
    return styles.muted;
  }
  return styles.neutral;
}

export default function TreasuryDemoPage() {
  const [scenario, setScenario] = useState<Scenario>("shortfall");
  const [data, setData] = useState<DemoResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = useMemo(
    () => scenarios.find((item) => item.value === scenario)!,
    [scenario]
  );

  async function runDemo() {
    setLoading(true);
    setError(null);
    setData(null);

    try {
      const response = await fetch(`${API_BASE}/api/demo/treasury/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario }),
      });

      if (!response.ok) {
        const body = await response.text();
        throw new Error(body || `Request failed with ${response.status}`);
      }

      setData((await response.json()) as DemoResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to run demo.");
    } finally {
      setLoading(false);
    }
  }

  const eur = data?.variance?.EUR;
  const recommendation = data?.funding_recommendations?.[0];
  const commentary = data?.ai_commentary;

  return (
    <main className={styles.shell}>
      <section className={styles.hero}>
        <div>
          <p className={styles.eyebrow}>
            Governed Multi-Agent Treasury
          </p>
          <h1>Treasury Multi-Agent Control Room</h1>
          <p className={styles.subhead}>
            Deterministic financial calculations, bounded agents, explicit
            dependencies, approval gates, retries, evidence lineage and a
            read-only LLM commentary layer over validated workflow results.
          </p>
        </div>

        <div className={styles.heroState}>
          <span>Terminal state</span>
          <strong className={data ? statusClass(data.run_state) : styles.neutral}>
            {data?.run_state || "NOT RUN"}
          </strong>
          {data && <small>{data.latency_ms} ms deterministic workflow</small>}
        </div>
      </section>

      <section className={styles.controls}>
        <div>
          <label htmlFor="scenario">Scenario</label>
          <select
            id="scenario"
            value={scenario}
            onChange={(e) => setScenario(e.target.value as Scenario)}
            disabled={loading}
          >
            {scenarios.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          <p>{selected.description}</p>
        </div>

        <button onClick={runDemo} disabled={loading}>
          {loading ? "Running workflow + AI commentary…" : "Run Treasury Demo"}
        </button>
      </section>

      {error && (
        <section className={styles.errorBox}>
          <strong>Demo request failed</strong>
          <p>{error}</p>
          <small>Check that the FastAPI service is running on {API_BASE}.</small>
        </section>
      )}

      <section className={styles.pipeline}>
        {[
          "cash_position",
          "obligations",
          "variance",
          "funding_recommendation",
          "approval_gate",
        ].map((task, index) => (
          <div className={styles.pipelineItem} key={task}>
            <div className={styles.agentCard}>
              <span>{taskLabels[task]}</span>
              <strong
                className={
                  data ? statusClass(data.task_states[task]) : styles.neutral
                }
              >
                {data?.task_states?.[task]?.toUpperCase() || "PENDING"}
              </strong>
              {data?.retry_counts?.[task] > 0 && (
                <small>{data.retry_counts[task]} retries</small>
              )}
            </div>
            {index < 4 && <div className={styles.arrow}>→</div>}
          </div>
        ))}
      </section>

      <section className={styles.grid}>
        <article className={styles.panel}>
          <div className={styles.panelTitle}>
            <h2>Liquidity result</h2>
            <span>EUR focus · deterministic</span>
          </div>

          <div className={styles.metrics}>
            <div>
              <span>Available</span>
              <strong>{money(eur?.available, "EUR")}</strong>
            </div>
            <div>
              <span>Required liquidity</span>
              <strong>{money(eur?.required_liquidity, "EUR")}</strong>
            </div>
            <div>
              <span>Scheduled outflows</span>
              <strong>{money(eur?.scheduled_outflows, "EUR")}</strong>
            </div>
            <div>
              <span>Projected requirement</span>
              <strong>{money(eur?.projected_requirement, "EUR")}</strong>
            </div>
            <div className={styles.emphasisMetric}>
              <span>Projected shortfall</span>
              <strong>{money(eur?.projected_shortfall, "EUR")}</strong>
            </div>
          </div>
        </article>

        <article className={styles.panel}>
          <div className={styles.panelTitle}>
            <h2>Funding & approval</h2>
            <span>Policy governed · deterministic</span>
          </div>

          {recommendation ? (
            <div className={styles.stack}>
              <div className={styles.row}>
                <span>Source corridor</span>
                <strong>
                  {recommendation.source_currency || "—"} →{" "}
                  {recommendation.destination_currency}
                </strong>
              </div>
              <div className={styles.row}>
                <span>Required funding</span>
                <strong>
                  {money(
                    recommendation.required_amount,
                    recommendation.destination_currency
                  )}
                </strong>
              </div>
              <div className={styles.row}>
                <span>Source surplus</span>
                <strong>
                  {money(
                    recommendation.source_available_surplus,
                    recommendation.source_currency || "GBP"
                  )}
                </strong>
              </div>
              <div className={styles.row}>
                <span>Approval decision</span>
                <strong
                  className={statusClass(
                    data?.approval?.workflow_state || data?.run_state
                  )}
                >
                  {data?.approval?.workflow_state || data?.run_state}
                </strong>
              </div>
              <p className={styles.reason}>{recommendation.reason}</p>
            </div>
          ) : (
            <p className={styles.placeholder}>
              Run a scenario to view the funding recommendation.
            </p>
          )}
        </article>
      </section>

      <section className={`${styles.panel} ${styles.aiPanel}`}>
        <div className={styles.panelTitle}>
          <div>
            <p className={styles.aiEyebrow}>LLM LAYER</p>
            <h2>AI Treasury Commentary</h2>
          </div>
          <span className={styles.aiBadge}>READ ONLY · POST-WORKFLOW</span>
        </div>

        {commentary ? (
          <>
            <div className={styles.aiMeta}>
              <span>
                Status:{" "}
                <strong className={statusClass(commentary.status)}>
                  {commentary.status.toUpperCase()}
                </strong>
              </span>
              <span>Provider: {commentary.provider || "—"}</span>
              <span>Model: {commentary.model || "—"}</span>
              <span>LLM latency: {commentary.latency_ms} ms</span>
            </div>

            {commentary.summary ? (
              <p className={styles.aiSummary}>{commentary.summary}</p>
            ) : (
              <p className={styles.placeholder}>
                {commentary.message || "AI commentary was not generated."}
              </p>
            )}

            <div className={styles.aiGuardrail}>
              <strong>Safety boundary</strong>
              <span>
                The LLM receives validated workflow results only. It has no
                funding, approval, payment, or calculation tools and cannot
                modify the Treasury decision.
              </span>
            </div>
          </>
        ) : (
          <p className={styles.placeholder}>
            Run the demo to generate a read-only LLM explanation after the
            deterministic Treasury workflow completes.
          </p>
        )}
      </section>

      {data?.failure && (
        <section className={styles.failurePanel}>
          <div>
            <span>Controlled failure</span>
            <h2>{data.failure.code}</h2>
          </div>
          <p>{data.failure.message}</p>
          <div className={styles.failureMeta}>
            <span>Failed task: {data.failure.failed_task || "—"}</span>
            <span>Retries: {data.failure.retry_count}</span>
          </div>
        </section>
      )}

      <section className={styles.panel}>
        <div className={styles.panelTitle}>
          <h2>Execution trace</h2>
          <span>Server-owned runtime state</span>
        </div>

        <div className={styles.trace}>
          {data?.trace?.length ? (
            data.trace.map((event) => (
              <div className={styles.traceRow} key={event.sequence}>
                <span className={styles.sequence}>
                  {String(event.sequence).padStart(2, "0")}
                </span>
                <span>{event.event_type}</span>
                <strong>{event.task_id || "workflow"}</strong>
                <span className={statusClass(event.state || "")}>
                  {event.state || "—"}
                </span>
                <p>{event.detail}</p>
                {event.evidence_ids.length > 0 && (
                  <div className={styles.evidence}>
                    {event.evidence_ids.map((id) => (
                      <code key={id}>{id}</code>
                    ))}
                  </div>
                )}
              </div>
            ))
          ) : (
            <p className={styles.placeholder}>
              Run the demo to see task ordering, retries, evidence and terminal
              state.
            </p>
          )}
        </div>
      </section>

      <footer className={styles.footer}>
        Demo-only surface. LLM commentary is read-only. No fund execution
        capability is exposed.
      </footer>
    </main>
  );
}
