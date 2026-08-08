"use client";

import {
  ChangeEvent,
  useMemo,
  useRef,
  useState,
} from "react";


type NumericSummary = {
  min?: number | null;
  max?: number | null;
  mean?: number | null;
  median?: number | null;
  std?: number | null;
  q1?: number | null;
  q3?: number | null;
  sum?: number | null;
};


type ColumnProfile = {
  name: string;
  inferred_type:
    | "date"
    | "numeric"
    | "boolean"
    | "string";

  non_null_count: number;
  missing_count: number;
  missing_percent: number;

  unique_count: number;

  numeric_format?:
    | "number"
    | "currency"
    | "percentage"
    | null;

  numeric_summary?: NumericSummary | null;

  example_values?: unknown[];
};


type ChartSuggestion = {
  chart_type:
    | "line"
    | "bar"
    | "scatter"
    | "table";

  x?: string | null;
  series: string[];
  reason: string;
};


type UploadResponse = {
  ok: boolean;

  requestId?: string;
  dataset_id?: string;

  file_name?: string;

  row_count?: number;
  column_count?: number;
  size_bytes?: number;

  created_at?: string;

  error?: string;
  detail?: string;
};


type DatasetProfileResponse = {
  ok: boolean;

  requestId?: string;

  dataset_id: string;
  file_name: string;

  row_count: number;
  column_count: number;

  columns: ColumnProfile[];

  sample_rows: Array<
    Record<string, unknown>
  >;

  chart_suggestions: ChartSuggestion[];

  error?: string;
  detail?: string;
};


type AgentAnalyzeResponse = {
  ok: boolean;

  request_id?: string;

  answer?: string;

  model?: string;

  memory_used_count?: number;

  tool_plan?: Record<
    string,
    unknown
  > | null;

  tool_results?: Array<
    Record<string, unknown>
  >;

  error?: string;
  detail?: string;
};


type WorkspaceTab =
  | "overview"
  | "columns"
  | "preview"
  | "insights";


const MAX_CLIENT_FILE_BYTES =
  10 * 1024 * 1024;


function formatFileSize(
  size: number,
) {
  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(
      size / 1024
    ).toFixed(1)} KB`;
  }

  return `${(
    size /
    1024 /
    1024
  ).toFixed(1)} MB`;
}


function formatNumber(
  value: number | null | undefined,
) {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(value)
  ) {
    return "—";
  }

  return new Intl.NumberFormat(
    undefined,
    {
      maximumFractionDigits: 2,
    },
  ).format(value);
}


function formatCellValue(
  value: unknown,
) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "—";
  }

  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }

  return String(value);
}


function getApiError(
  payload: unknown,
  fallback: string,
) {
  if (
    typeof payload !== "object" ||
    payload === null
  ) {
    return fallback;
  }

  const candidate =
    payload as Record<
      string,
      unknown
    >;

  if (
    typeof candidate.error === "string"
  ) {
    return candidate.error;
  }

  if (
    typeof candidate.detail === "string"
  ) {
    return candidate.detail;
  }

  return fallback;
}


function typeBadgeClass(
  type: ColumnProfile["inferred_type"],
) {
  if (type === "numeric") {
    return (
      "border-cyan-300/25 " +
      "bg-cyan-300/10 " +
      "text-cyan-100"
    );
  }

  if (type === "date") {
    return (
      "border-violet-300/25 " +
      "bg-violet-300/10 " +
      "text-violet-100"
    );
  }

  if (type === "boolean") {
    return (
      "border-emerald-300/25 " +
      "bg-emerald-300/10 " +
      "text-emerald-100"
    );
  }

  return (
    "border-white/10 " +
    "bg-white/5 " +
    "text-slate-300"
  );
}


function chartBadgeClass(
  chartType: ChartSuggestion["chart_type"],
) {
  if (chartType === "line") {
    return (
      "border-cyan-300/25 " +
      "bg-cyan-300/10 " +
      "text-cyan-100"
    );
  }

  if (chartType === "bar") {
    return (
      "border-amber-300/25 " +
      "bg-amber-300/10 " +
      "text-amber-100"
    );
  }

  if (chartType === "scatter") {
    return (
      "border-violet-300/25 " +
      "bg-violet-300/10 " +
      "text-violet-100"
    );
  }

  return (
    "border-white/10 " +
    "bg-white/5 " +
    "text-slate-300"
  );
}


export function DataWorkspace() {
  const fileInputRef =
    useRef<HTMLInputElement | null>(
      null,
    );

  const [
    selectedFile,
    setSelectedFile,
  ] = useState<File | null>(null);

  const [
    upload,
    setUpload,
  ] = useState<UploadResponse | null>(
    null,
  );

  const [
    profile,
    setProfile,
  ] =
    useState<DatasetProfileResponse | null>(
      null,
    );

  const [
    activeTab,
    setActiveTab,
  ] =
    useState<WorkspaceTab>(
      "overview",
    );

  const [
    uploading,
    setUploading,
  ] = useState(false);

  const [
    profiling,
    setProfiling,
  ] = useState(false);

  const [
    analyzing,
    setAnalyzing,
  ] = useState(false);

  const [
    deleting,
    setDeleting,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState<string | null>(
    null,
  );

  const [
    statusMessage,
    setStatusMessage,
  ] = useState<string | null>(
    null,
  );

  const [
    analysisQuestion,
    setAnalysisQuestion,
  ] = useState(
    "Analyze this CSV. Summarize the dataset, highlight important statistics, data-quality issues, and the most useful visualization.",
  );

  const [
    analysisAnswer,
    setAnalysisAnswer,
  ] = useState<string | null>(
    null,
  );

  const [
    analysisModel,
    setAnalysisModel,
  ] = useState<string | null>(
    null,
  );


  const datasetId =
    upload?.dataset_id ??
    profile?.dataset_id ??
    null;


  const totalMissingValues =
    useMemo(() => {
      if (!profile) {
        return 0;
      }

      return profile.columns.reduce(
        (
          total,
          column,
        ) =>
          total +
          column.missing_count,
        0,
      );
    }, [profile]);


  const numericColumnCount =
    useMemo(
      () =>
        profile?.columns.filter(
          (column) =>
            column.inferred_type ===
            "numeric",
        ).length ?? 0,
      [profile],
    );


  const dateColumnCount =
    useMemo(
      () =>
        profile?.columns.filter(
          (column) =>
            column.inferred_type ===
            "date",
        ).length ?? 0,
      [profile],
    );


  function resetFileInput() {
    if (fileInputRef.current) {
      fileInputRef.current.value =
        "";
    }
  }


  function resetWorkspace() {
    setSelectedFile(null);
    setUpload(null);
    setProfile(null);
    setAnalysisAnswer(null);
    setAnalysisModel(null);
    setActiveTab("overview");

    resetFileInput();
  }


  function handleFileChange(
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const file =
      event.target.files?.[0] ??
      null;

    setError(null);
    setStatusMessage(null);
    setAnalysisAnswer(null);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (
      !file.name
        .toLowerCase()
        .endsWith(".csv")
    ) {
      setError(
        "Choose a CSV file.",
      );

      setSelectedFile(null);

      resetFileInput();

      return;
    }

    if (
      file.size >
      MAX_CLIENT_FILE_BYTES
    ) {
      setError(
        "CSV files are currently limited to 10 MB.",
      );

      setSelectedFile(null);

      resetFileInput();

      return;
    }

    setSelectedFile(file);
  }


  async function loadProfile(
    nextDatasetId: string,
  ) {
    setProfiling(true);

    try {
      const response = await fetch(
        `/api/data/profile/${encodeURIComponent(
          nextDatasetId,
        )}`,
        {
          cache: "no-store",
        },
      );

      const payload =
        (await response.json()) as DatasetProfileResponse;

      if (
        !response.ok ||
        !payload.ok
      ) {
        throw new Error(
          getApiError(
            payload,
            "CSV profiling failed.",
          ),
        );
      }

      setProfile(payload);

      setStatusMessage(
        `${payload.file_name} profiled successfully: ` +
          `${payload.row_count} rows and ` +
          `${payload.column_count} columns.`,
      );

      setActiveTab("overview");
    } finally {
      setProfiling(false);
    }
  }


  async function handleUpload() {
    if (!selectedFile) {
      setError(
        "Choose a CSV file first.",
      );

      return;
    }

    setUploading(true);
    setError(null);
    setStatusMessage(
      `Uploading ${selectedFile.name}...`,
    );

    setUpload(null);
    setProfile(null);
    setAnalysisAnswer(null);

    try {
      const formData =
        new FormData();

      formData.append(
        "file",
        selectedFile,
      );

      const response = await fetch(
        "/api/data/upload",
        {
          method: "POST",
          body: formData,
        },
      );

      const payload =
        (await response.json()) as UploadResponse;

      if (
        !response.ok ||
        !payload.ok ||
        !payload.dataset_id
      ) {
        throw new Error(
          getApiError(
            payload,
            "CSV upload failed.",
          ),
        );
      }

      setUpload(payload);

      setStatusMessage(
        `${payload.file_name ?? selectedFile.name} uploaded. Profiling dataset...`,
      );

      await loadProfile(
        payload.dataset_id,
      );

      setSelectedFile(null);

      resetFileInput();
    } catch (uploadError) {
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "CSV upload failed.",
      );
    } finally {
      setUploading(false);
    }
  }


  async function handleRefreshProfile() {
    if (!datasetId) {
      return;
    }

    setError(null);
    setStatusMessage(
      "Refreshing CSV profile...",
    );

    try {
      await loadProfile(
        datasetId,
      );
    } catch (profileError) {
      setError(
        profileError instanceof Error
          ? profileError.message
          : "CSV profiling failed.",
      );
    }
  }


  async function handleDelete() {
    if (!datasetId) {
      return;
    }

    const confirmed =
      window.confirm(
        "Delete this CSV dataset from local analysis storage?",
      );

    if (!confirmed) {
      return;
    }

    setDeleting(true);
    setError(null);
    setStatusMessage(null);

    try {
      const response = await fetch(
        `/api/data/delete/${encodeURIComponent(
          datasetId,
        )}`,
        {
          method: "DELETE",
        },
      );

      const payload =
        (await response.json()) as {
          ok?: boolean;
          deleted?: boolean;
          error?: string;
          detail?: string;
        };

      if (
        !response.ok ||
        !payload.ok
      ) {
        throw new Error(
          getApiError(
            payload,
            "Dataset deletion failed.",
          ),
        );
      }

      resetWorkspace();

      setStatusMessage(
        "CSV dataset deleted.",
      );
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "Dataset deletion failed.",
      );
    } finally {
      setDeleting(false);
    }
  }


  async function handleAnalyze() {
    if (!datasetId) {
      setError(
        "Upload a CSV before running AI analysis.",
      );

      return;
    }

    const question =
      analysisQuestion.trim();

    if (!question) {
      setError(
        "Enter an analysis request.",
      );

      return;
    }

    setAnalyzing(true);
    setError(null);
    setStatusMessage(
      "Running structured CSV analysis through the finance agent...",
    );

    setAnalysisAnswer(null);
    setAnalysisModel(null);

    try {
      const response = await fetch(
        "/api/agents/analyze",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            question,
            provider_id:
              "openai-premium",
            dataset_id: datasetId,

            // Important:
            // CSV analysis is structured data,
            // not document RAG.
            use_documents: false,
          }),
        },
      );

      const payload =
        (await response.json()) as AgentAnalyzeResponse;

      if (
        !response.ok ||
        !payload.ok
      ) {
        throw new Error(
          getApiError(
            payload,
            "AI CSV analysis failed.",
          ),
        );
      }

      setAnalysisAnswer(
        payload.answer ??
          "Analysis completed without a text response.",
      );

      setAnalysisModel(
        payload.model ?? null,
      );

      setActiveTab("insights");

      setStatusMessage(
        "CSV analysis completed.",
      );
    } catch (analysisError) {
      setError(
        analysisError instanceof Error
          ? analysisError.message
          : "AI CSV analysis failed.",
      );
    } finally {
      setAnalyzing(false);
    }
  }


  const tabs: Array<{
    id: WorkspaceTab;
    label: string;
  }> = [
    {
      id: "overview",
      label: "Overview",
    },
    {
      id: "columns",
      label: "Columns",
    },
    {
      id: "preview",
      label: "Preview",
    },
    {
      id: "insights",
      label: "Insights",
    },
  ];


  return (
    <div className="space-y-4">
      {error ? (
        <div className="rounded-2xl border border-rose-300/20 bg-rose-300/10 px-4 py-3 text-sm text-rose-100">
          {error}
        </div>
      ) : null}

      {statusMessage ? (
        <div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/10 px-4 py-3 text-sm text-cyan-100">
          {statusMessage}
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[360px_minmax(0,1fr)]">
        {/* Upload / dataset panel */}
        <section className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-amber-200/70">
              Dataset
            </p>

            <h2 className="mt-2 text-lg font-semibold text-white">
              Upload CSV
            </h2>

            <p className="mt-1 text-xs leading-5 text-slate-400">
              CSV files are analyzed as structured data with pandas.
              They are not embedded or sent through document RAG.
            </p>
          </div>

          <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              onChange={
                handleFileChange
              }
              disabled={
                uploading ||
                profiling ||
                deleting
              }
              className="block w-full text-xs text-slate-300 file:mr-3 file:rounded-xl file:border-0 file:bg-amber-300/10 file:px-3 file:py-2 file:text-xs file:font-semibold file:text-amber-100 hover:file:bg-amber-300/20 disabled:opacity-50"
            />

            {selectedFile ? (
              <div className="mt-3 rounded-xl border border-amber-300/15 bg-amber-300/5 p-3">
                <p className="truncate text-sm font-semibold text-white">
                  {selectedFile.name}
                </p>

                <p className="mt-1 text-xs text-slate-400">
                  {formatFileSize(
                    selectedFile.size,
                  )}
                </p>
              </div>
            ) : null}

            <button
              type="button"
              onClick={
                handleUpload
              }
              disabled={
                !selectedFile ||
                uploading ||
                profiling
              }
              className="mt-3 w-full rounded-xl bg-amber-300 px-3 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {uploading
                ? "Uploading..."
                : profiling
                  ? "Profiling..."
                  : "Upload and analyze"}
            </button>
          </div>

          {profile ? (
            <div className="mt-4 rounded-2xl border border-emerald-300/20 bg-emerald-300/5 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-white">
                    {
                      profile.file_name
                    }
                  </p>

                  <p className="mt-1 text-xs text-slate-400">
                    {
                      profile.row_count
                    }{" "}
                    rows ·{" "}
                    {
                      profile.column_count
                    }{" "}
                    columns
                  </p>
                </div>

                <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-emerald-100">
                  Ready
                </span>
              </div>

              <div className="mt-4 space-y-2">
                <div className="flex justify-between gap-3 text-xs">
                  <span className="text-slate-400">
                    Numeric
                  </span>

                  <span className="font-semibold text-white">
                    {
                      numericColumnCount
                    }
                  </span>
                </div>

                <div className="flex justify-between gap-3 text-xs">
                  <span className="text-slate-400">
                    Date/time
                  </span>

                  <span className="font-semibold text-white">
                    {
                      dateColumnCount
                    }
                  </span>
                </div>

                <div className="flex justify-between gap-3 text-xs">
                  <span className="text-slate-400">
                    Missing cells
                  </span>

                  <span className="font-semibold text-white">
                    {
                      totalMissingValues
                    }
                  </span>
                </div>
              </div>

              <div className="mt-4 grid gap-2">
                <button
                  type="button"
                  onClick={
                    handleRefreshProfile
                  }
                  disabled={
                    profiling ||
                    deleting
                  }
                  className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-white transition hover:border-cyan-300/30 hover:bg-cyan-300/10 disabled:opacity-50"
                >
                  {profiling
                    ? "Refreshing..."
                    : "Refresh profile"}
                </button>

                <button
                  type="button"
                  onClick={
                    handleDelete
                  }
                  disabled={
                    deleting
                  }
                  className="rounded-xl border border-rose-300/20 bg-rose-300/5 px-3 py-2 text-xs font-semibold text-rose-100 transition hover:bg-rose-300/10 disabled:opacity-50"
                >
                  {deleting
                    ? "Deleting..."
                    : "Delete dataset"}
                </button>
              </div>
            </div>
          ) : (
            <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
              <p className="text-sm font-medium text-slate-300">
                No dataset loaded
              </p>

              <p className="mt-1 text-xs leading-5 text-slate-500">
                Upload a CSV to inspect its schema, statistics,
                missing values, preview rows, and suggested
                visualizations.
              </p>
            </div>
          )}
        </section>

        {/* Main workspace */}
        <section className="min-w-0 rounded-3xl border border-white/10 bg-slate-950/75 shadow-xl shadow-black/15">
          <div className="border-b border-white/10 p-4">
            <div className="flex flex-wrap gap-2">
              {tabs.map(
                (tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() =>
                      setActiveTab(
                        tab.id,
                      )
                    }
                    className={[
                      "rounded-xl border px-3 py-2 text-xs font-semibold transition",
                      activeTab ===
                      tab.id
                        ? "border-amber-300/30 bg-amber-300/10 text-amber-100"
                        : "border-white/10 bg-white/5 text-slate-400 hover:border-white/20 hover:text-white",
                    ].join(
                      " ",
                    )}
                  >
                    {tab.label}
                  </button>
                ),
              )}
            </div>
          </div>

          {!profile ? (
            <div className="flex min-h-[420px] items-center justify-center p-8 text-center">
              <div className="max-w-md">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-amber-300/20 bg-amber-300/10 text-xl font-semibold text-amber-100">
                  CSV
                </div>

                <h3 className="mt-4 text-lg font-semibold text-white">
                  Structured finance analysis
                </h3>

                <p className="mt-2 text-sm leading-6 text-slate-400">
                  Upload a CSV to profile columns, inspect financial
                  data quality, preview rows, and prepare chart-ready
                  analysis.
                </p>
              </div>
            </div>
          ) : null}

          {profile &&
          activeTab ===
            "overview" ? (
            <div className="space-y-5 p-4 sm:p-5">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <MetricCard
                  label="Rows"
                  value={formatNumber(
                    profile.row_count,
                  )}
                />

                <MetricCard
                  label="Columns"
                  value={formatNumber(
                    profile.column_count,
                  )}
                />

                <MetricCard
                  label="Numeric fields"
                  value={formatNumber(
                    numericColumnCount,
                  )}
                />

                <MetricCard
                  label="Missing cells"
                  value={formatNumber(
                    totalMissingValues,
                  )}
                  warning={
                    totalMissingValues >
                    0
                  }
                />
              </div>

              <div>
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                    Suggested analysis
                  </p>

                  <h3 className="mt-2 text-base font-semibold text-white">
                    Visualization candidates
                  </h3>

                  <p className="mt-1 text-xs leading-5 text-slate-400">
                    These are deterministic suggestions from the CSV
                    profile. Actual chart rendering will be added in
                    the charting phase.
                  </p>
                </div>

                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  {profile
                    .chart_suggestions
                    .map(
                      (
                        suggestion,
                        index,
                      ) => (
                        <div
                          key={`${suggestion.chart_type}-${index}`}
                          className="rounded-2xl border border-white/10 bg-black/20 p-4"
                        >
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] ${chartBadgeClass(
                                suggestion.chart_type,
                              )}`}
                            >
                              {
                                suggestion.chart_type
                              }
                            </span>

                            {suggestion.x ? (
                              <span className="text-xs text-slate-400">
                                X:{" "}
                                <span className="font-semibold text-slate-200">
                                  {
                                    suggestion.x
                                  }
                                </span>
                              </span>
                            ) : null}
                          </div>

                          {suggestion
                            .series
                            .length ? (
                            <p className="mt-3 text-sm text-slate-300">
                              Series:{" "}
                              <span className="font-semibold text-white">
                                {suggestion.series.join(
                                  ", ",
                                )}
                              </span>
                            </p>
                          ) : null}

                          <p className="mt-2 text-xs leading-5 text-slate-400">
                            {
                              suggestion.reason
                            }
                          </p>
                        </div>
                      ),
                    )}
                </div>
              </div>

              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                  Schema
                </p>

                <div className="mt-3 flex flex-wrap gap-2">
                  {profile.columns.map(
                    (column) => (
                      <div
                        key={
                          column.name
                        }
                        className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2"
                      >
                        <span className="text-xs font-semibold text-white">
                          {
                            column.name
                          }
                        </span>

                        <span
                          className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] ${typeBadgeClass(
                            column.inferred_type,
                          )}`}
                        >
                          {
                            column.inferred_type
                          }
                        </span>
                      </div>
                    ),
                  )}
                </div>
              </div>
            </div>
          ) : null}

          {profile &&
          activeTab ===
            "columns" ? (
            <div className="grid gap-3 p-4 sm:p-5 lg:grid-cols-2">
              {profile.columns.map(
                (column) => (
                  <ColumnCard
                    key={
                      column.name
                    }
                    column={
                      column
                    }
                  />
                ),
              )}
            </div>
          ) : null}

          {profile &&
          activeTab ===
            "preview" ? (
            <div className="p-4 sm:p-5">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                  Data preview
                </p>

                <h3 className="mt-2 text-base font-semibold text-white">
                  First{" "}
                  {
                    profile
                      .sample_rows
                      .length
                  }{" "}
                  rows
                </h3>
              </div>

              <div className="mt-4 overflow-x-auto rounded-2xl border border-white/10">
                <table className="min-w-full border-collapse text-left text-xs">
                  <thead className="bg-white/5">
                    <tr>
                      {profile.columns.map(
                        (
                          column,
                        ) => (
                          <th
                            key={
                              column.name
                            }
                            className="whitespace-nowrap border-b border-white/10 px-4 py-3 font-semibold text-slate-300"
                          >
                            {
                              column.name
                            }
                          </th>
                        ),
                      )}
                    </tr>
                  </thead>

                  <tbody>
                    {profile
                      .sample_rows
                      .map(
                        (
                          row,
                          rowIndex,
                        ) => (
                          <tr
                            key={
                              rowIndex
                            }
                            className="border-b border-white/5 last:border-b-0"
                          >
                            {profile.columns.map(
                              (
                                column,
                              ) => (
                                <td
                                  key={
                                    column.name
                                  }
                                  className="max-w-[260px] whitespace-nowrap px-4 py-3 text-slate-300"
                                >
                                  {formatCellValue(
                                    row[
                                      column
                                        .name
                                    ],
                                  )}
                                </td>
                              ),
                            )}
                          </tr>
                        ),
                      )}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          {profile &&
          activeTab ===
            "insights" ? (
            <div className="space-y-4 p-4 sm:p-5">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-amber-200/70">
                  Finance Agent
                </p>

                <h3 className="mt-2 text-base font-semibold text-white">
                  Analyze this dataset with AI
                </h3>

                <p className="mt-1 text-xs leading-5 text-slate-400">
                  The agent receives the deterministic pandas profile,
                  not vector-search results.
                </p>
              </div>

              <textarea
                value={
                  analysisQuestion
                }
                onChange={(
                  event,
                ) =>
                  setAnalysisQuestion(
                    event.target
                      .value,
                  )
                }
                rows={5}
                disabled={
                  analyzing
                }
                className="w-full resize-y rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm leading-6 text-white outline-none transition placeholder:text-slate-600 focus:border-amber-300/30 disabled:opacity-60"
              />

              <button
                type="button"
                onClick={
                  handleAnalyze
                }
                disabled={
                  analyzing ||
                  !datasetId ||
                  !analysisQuestion.trim()
                }
                className="rounded-xl bg-amber-300 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {analyzing
                  ? "Analyzing..."
                  : "Analyze with AI"}
              </button>

              {analysisAnswer ? (
                <div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/5 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-cyan-200">
                      Analysis result
                    </p>

                    {analysisModel ? (
                      <span className="rounded-full border border-white/10 bg-black/20 px-2.5 py-1 text-[10px] text-slate-400">
                        {
                          analysisModel
                        }
                      </span>
                    ) : null}
                  </div>

                  <div className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-200">
                    {
                      analysisAnswer
                    }
                  </div>
                </div>
              ) : (
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-400">
                  Run an analysis request to summarize the CSV using
                  the LangGraph CSV profiling tool.
                </div>
              )}
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}


function MetricCard({
  label,
  value,
  warning = false,
}: {
  label: string;
  value: string;
  warning?: boolean;
}) {
  return (
    <div
      className={[
        "rounded-2xl border p-4",
        warning
          ? "border-amber-300/20 bg-amber-300/5"
          : "border-white/10 bg-black/20",
      ].join(" ")}
    >
      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
        {label}
      </p>

      <p
        className={[
          "mt-2 text-2xl font-semibold",
          warning
            ? "text-amber-100"
            : "text-white",
        ].join(" ")}
      >
        {value}
      </p>
    </div>
  );
}


function ColumnCard({
  column,
}: {
  column: ColumnProfile;
}) {
  const summary =
    column.numeric_summary;

  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="break-words text-sm font-semibold text-white">
            {column.name}
          </p>

          <p className="mt-1 text-xs text-slate-500">
            {
              column.unique_count
            }{" "}
            unique value
            {column.unique_count ===
            1
              ? ""
              : "s"}
          </p>
        </div>

        <span
          className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] ${typeBadgeClass(
            column.inferred_type,
          )}`}
        >
          {
            column.inferred_type
          }
        </span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2">
        <SmallStat
          label="Non-null"
          value={formatNumber(
            column.non_null_count,
          )}
        />

        <SmallStat
          label="Missing"
          value={`${formatNumber(
            column.missing_count,
          )} (${column.missing_percent.toFixed(
            1,
          )}%)`}
        />
      </div>

      {column.numeric_format ? (
        <p className="mt-3 text-xs text-slate-400">
          Format:{" "}
          <span className="font-semibold text-slate-200">
            {
              column.numeric_format
            }
          </span>
        </p>
      ) : null}

      {summary ? (
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <SmallStat
            label="Min"
            value={formatNumber(
              summary.min,
            )}
          />

          <SmallStat
            label="Max"
            value={formatNumber(
              summary.max,
            )}
          />

          <SmallStat
            label="Mean"
            value={formatNumber(
              summary.mean,
            )}
          />

          <SmallStat
            label="Median"
            value={formatNumber(
              summary.median,
            )}
          />
        </div>
      ) : null}

      {column.example_values?.length ? (
        <div className="mt-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
            Examples
          </p>

          <div className="mt-2 flex flex-wrap gap-2">
            {column.example_values.map(
              (
                value,
                index,
              ) => (
                <span
                  key={index}
                  className="max-w-full truncate rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[11px] text-slate-300"
                >
                  {formatCellValue(
                    value,
                  )}
                </span>
              ),
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}


function SmallStat({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.03] p-2.5">
      <p className="text-[9px] font-semibold uppercase tracking-[0.14em] text-slate-500">
        {label}
      </p>

      <p className="mt-1 break-words text-xs font-semibold text-slate-200">
        {value}
      </p>
    </div>
  );
}