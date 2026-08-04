"use client";

import {
  ChangeEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/Sidebar";
import { clearAuth, getDisplayName, loadAuth } from "@/lib/auth";
import type { AuthState, FinanceTask } from "@/types";

type StoredDocument = {
  id: string;
  userId: string;
  fileName: string;
  fileType: string;
  kind: "pdf" | "docx" | "text" | "csv" | "image" | "unknown";
  size: number;
  pageCount?: number;
  chunkCount: number;
  extractedChars: number;
  embeddingModel: string;
  storageProfile: string;
  createdAt: string;
};

type RetrievedSource = {
  documentId: string;
  chunkId: string;
  fileName: string;
  chunkIndex: number;
  pageNumber?: number;
  score: number;
  snippet: string;
};

type RagAnswer = {
  id?: string;
  request_id?: string;
  provider?: string;
  model_id?: string;
  output?: string;
  latency_ms?: number;
  usage?: {
    input_tokens?: number;
    output_tokens?: number;
    total_tokens?: number;
  };
};

type RagQueryResponse = {
  ok: boolean;
  request_id?: string;
  answer?: RagAnswer;
  sources?: RetrievedSource[];
  retrieval?: {
    topK?: number;
    bestScore?: number;
    embeddingModel?: string;
    usage?: {
      prompt_tokens?: number;
      total_tokens?: number;
    };
  };
  error?: string;
};

type DocumentStorageProfile =
  | "session"
  | "local-json"
  | "local-sqlite"
  | "supabase-pgvector"
  | "aws"
  | "export-import";

type RagStorageConfig = {
  profile: DocumentStorageProfile;
  originalFileStorage: string;
  vectorStorage: string;
  metadataStorage: string;
  historyStorage: string;
  storeOriginalFiles: boolean;
  embeddingProvider: string;
  embeddingModel: string;
  chunkSizeChars: number;
  chunkOverlapChars: number;
  retrievalTopK: number;
  maxIndexedChars: number;
  updatedAt: string;
};

type DisabledProfile = {
  profile: DocumentStorageProfile;
  label: string;
  reason: string;
};

const providerOptions = [
  {
    id: "openai-premium",
    name: "OpenAI Premium",
    description: "Recommended for Phase 2A/2B RAG testing.",
  },
  {
    id: "claude-premium",
    name: "Claude Premium",
    description: "Useful for long narrative finance documents if configured.",
  },
  {
    id: "gemini-premium",
    name: "Gemini Premium",
    description: "Useful for long-context experiments if configured.",
  },
];

const taskOptions: Array<{
  id: FinanceTask;
  name: string;
  description: string;
}> = [
  {
    id: "qa",
    name: "Q&A",
    description: "Ask direct questions over selected indexed documents.",
  },
  {
    id: "summarize",
    name: "Summarize",
    description: "Summarize retrieved evidence from selected documents.",
  },
  {
    id: "risk-analysis",
    name: "Risk Analysis",
    description: "Find financial, operational, liquidity, and disclosure risks.",
  },
];


function formatFileSize(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function formatKind(kind: StoredDocument["kind"]) {
  if (kind === "pdf") return "PDF";
  if (kind === "docx") return "DOCX";
  if (kind === "text") return "TEXT";
  if (kind === "csv") return "CSV";
  if (kind === "image") return "IMAGE";
  return "UNKNOWN";
}

function formatDate(value: string) {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function profileLabel(profile?: DocumentStorageProfile) {
  if (profile === "session") return "Session only";
  if (profile === "local-json") return "Local project storage";
  if (profile === "local-sqlite") return "Local SQLite";
  if (profile === "supabase-pgvector") return "Supabase pgvector";
  if (profile === "aws") return "AWS";
  if (profile === "export-import") return "Export/import";
  return "Loading";
}

export default function DocSearchPage() {
  const router = useRouter();
  const configRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);


  const [auth, setAuth] = useState<AuthState | null>(null);
  const [documents, setDocuments] = useState<StoredDocument[]>([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [providerId, setProviderId] = useState("openai-premium");
  const [task, setTask] = useState<FinanceTask>("qa");
  const [question, setQuestion] = useState(
    "What are the main financial risks in the selected document?",
  );
  const [topK, setTopK] = useState(6);

  const [indexing, setIndexing] = useState(false);
  const [querying, setQuerying] = useState(false);
  const [loadingDocuments, setLoadingDocuments] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const [answer, setAnswer] = useState<RagAnswer | null>(null);
  const [sources, setSources] = useState<RetrievedSource[]>([]);
  const [latestRequestId, setLatestRequestId] = useState<string | null>(null);

  const [ragConfig, setRagConfig] = useState<RagStorageConfig | null>(null);
  const [disabledProfiles, setDisabledProfiles] = useState<DisabledProfile[]>(
    [],
  );
  const [savingConfig, setSavingConfig] = useState(false);
  const [pendingProfile, setPendingProfile] =
    useState<DocumentStorageProfile | null>(null);

  const selectedDocuments = useMemo(
    () =>
      documents.filter((document) =>
        selectedDocumentIds.includes(document.id),
      ),
    [documents, selectedDocumentIds],
  );

  function clearSelectedFile() {
    setSelectedFile(null);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  useEffect(() => {
    setAuth(loadAuth());
    void loadDocuments();
    void loadRagConfig();
  }, []);

  async function loadDocuments() {
    setLoadingDocuments(true);
    setError(null);

    try {
      const response = await fetch("/api/documents/list", {
        cache: "no-store",
      });
      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ?? "Failed to load indexed documents.");
      }

      const nextDocuments = (payload.documents ?? []) as StoredDocument[];
      setDocuments(nextDocuments);

      setSelectedDocumentIds((current) => {
        const availableIds = new Set(nextDocuments.map((item) => item.id));
        const stillAvailable = current.filter((id) => availableIds.has(id));

        if (stillAvailable.length) {
          return stillAvailable;
        }

        return nextDocuments[0]?.id ? [nextDocuments[0].id] : [];
      });
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Failed to load indexed documents.",
      );
    } finally {
      setLoadingDocuments(false);
    }
  }

  async function loadRagConfig() {
    try {
      const response = await fetch("/api/documents/config", {
        cache: "no-store",
      });
      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ?? "Failed to load RAG configuration.");
      }

      setRagConfig(payload.config);
      setDisabledProfiles(payload.disabledProfiles ?? []);
    } catch (configError) {
      setError(
        configError instanceof Error
          ? configError.message
          : "Failed to load RAG configuration.",
      );
    }
  }

  function scrollToConfig() {
    configRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  async function handleChangeStorageProfile(profile: DocumentStorageProfile) {
    if (profile === ragConfig?.profile) {
      setStatusMessage(`${profileLabel(profile)} is already active.`);
      return;
    }

    setSavingConfig(true);
    setPendingProfile(profile);
    setError(null);
    setStatusMessage(
      `Switching RAG storage profile to ${profileLabel(profile)}...`,
    );

    try {
      const response = await fetch("/api/documents/config", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ profile }),
      });

      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ?? "Failed to update RAG configuration.");
      }

      setRagConfig(payload.config);

      const warnings = Array.isArray(payload.warnings) ? payload.warnings : [];

      setStatusMessage(
        warnings.length
          ? `RAG configuration updated to ${profileLabel(
              payload.config.profile,
            )}. ${warnings.join(" ")}`
          : `RAG configuration updated to ${profileLabel(
              payload.config.profile,
            )}.`,
      );

      await loadDocuments();
    } catch (configError) {
      setError(
        configError instanceof Error
          ? configError.message
          : "Failed to update RAG configuration.",
      );
    } finally {
      setSavingConfig(false);
      setPendingProfile(null);
    }
  }

  async function handleClearDocumentMemory() {
    const confirmed = window.confirm(
      "Clear all local document memory for this user? This removes indexed documents, chunks, and vectors. Original files are not stored.",
    );

    if (!confirmed) return;

    setError(null);
    setStatusMessage(null);

    try {
      const response = await fetch("/api/documents/clear", {
        method: "DELETE",
      });

      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ?? "Failed to clear document memory.");
      }

      setDocuments([]);
      setSelectedDocumentIds([]);
      setAnswer(null);
      setSources([]);
      setStatusMessage("All local document memory was cleared.");
    } catch (clearError) {
      setError(
        clearError instanceof Error
          ? clearError.message
          : "Failed to clear document memory.",
      );
    }
  }

  function handleLogout() {
    clearAuth();
    setAuth(null);
    router.push("/login");
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setError(null);
    setStatusMessage(null);
  }
  // function clearSelectedFile() {
  //   setSelectedFile(null);

  //   if (fileInputRef.current) {
  //     fileInputRef.current.value = "";
  //   }
  // }

  function toggleDocument(documentId: string) {
    setSelectedDocumentIds((current) =>
      current.includes(documentId)
        ? current.filter((id) => id !== documentId)
        : [...current, documentId],
    );
  }

  async function handleUploadAndIndex() {
    if (!selectedFile) {
      setError("Choose a PDF, DOCX, TXT, MD, or CSV file first.");
      return;
    }

    setIndexing(true);
    setError(null);
    setStatusMessage(`Indexing ${selectedFile.name}...`);
    setAnswer(null);
    setSources([]);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch("/api/documents/upload", {
        method: "POST",
        body: formData,
      });

      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ?? "Document indexing failed.");
      }

      const indexedDocument = payload.document as StoredDocument;

      setStatusMessage(
        `${indexedDocument.fileName} indexed with ${indexedDocument.chunkCount} chunks and ${payload.vectorsIndexed} vectors.`,
      );

      setSelectedFile(null);
      setSelectedDocumentIds((current) => [
        indexedDocument.id,
        ...current.filter((id) => id !== indexedDocument.id),
      ]);

      await loadDocuments();
      clearSelectedFile();
    } catch (uploadError) {
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "Document indexing failed.",
      );
    } finally {
      setIndexing(false);
    }
  }

  async function handleDeleteDocument(documentId: string) {
    const target = documents.find((document) => document.id === documentId);

    const confirmed = window.confirm(
      `Delete ${
        target?.fileName ?? "this document"
      } from local document memory? This removes metadata, chunks, and vectors.`,
    );

    if (!confirmed) return;

    setError(null);
    setStatusMessage(null);

    try {
      const response = await fetch("/api/documents/delete", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ documentId }),
      });

      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ?? "Document deletion failed.");
      }

      setSelectedDocumentIds((current) =>
        current.filter((id) => id !== documentId),
      );

      clearSelectedFile();

      setStatusMessage("Document memory deleted locally.");
      await loadDocuments();
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "Document deletion failed.",
      );
    }

    
  }

  async function handleAskQuestion() {
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) {
      setError("Enter a question before running document search.");
      return;
    }

    if (!selectedDocumentIds.length) {
      setError("Select at least one indexed document.");
      return;
    }

    setQuerying(true);
    setError(null);
    setStatusMessage("Retrieving relevant chunks and asking the model...");
    setAnswer(null);
    setSources([]);
    setLatestRequestId(null);

    try {
      const response = await fetch("/api/documents/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: trimmedQuestion,
          task,
          providerId,
          documentIds: selectedDocumentIds,
          topK,
        }),
      });

      const payload = (await response.json()) as RagQueryResponse;

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error ?? "RAG query failed.");
      }

      setAnswer(payload.answer ?? null);
      setSources(payload.sources ?? []);
      setLatestRequestId(payload.request_id ?? null);

      const bestScore = payload.retrieval?.bestScore;

      setStatusMessage(
        `Retrieved ${(payload.sources ?? []).length} source chunk${
          (payload.sources ?? []).length === 1 ? "" : "s"
        } using ${
          payload.retrieval?.embeddingModel ?? "the configured embedding model"
        }.${
          typeof bestScore === "number" && bestScore < 0.3
            ? " Low retrieval confidence: review the source snippets."
            : ""
        }`,
      );
    } catch (queryError) {
      setError(
        queryError instanceof Error ? queryError.message : "RAG query failed.",
      );
    } finally {
      setQuerying(false);
    }
  }

  return (
    <main className="page-shell">
      <div className="app-grid">
        <Sidebar
          displayName={getDisplayName(auth)}
          mode="premium"
          onLogout={handleLogout}
        />

        <div className="space-y-6">
          <section className="soft-panel flex flex-wrap items-center justify-between gap-4 p-6 sm:p-8">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-emerald-200/70">
                Doc Intelligent Search
              </p>
              <h1 className="mt-2 text-3xl font-semibold text-white">
                Ask repeated questions over indexed finance documents
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-300">
                Upload and index documents once, then query selected files using
                chunking, embeddings, local vector search, retrieved sources,
                and your configured premium model.
              </p>

              <div className="mt-4 flex flex-wrap gap-3 text-xs">
                <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1 font-semibold text-emerald-100">
                  RAG active
                </span>
                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-slate-300">
                  Storage: {profileLabel(ragConfig?.profile)}
                </span>
                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-slate-300">
                  Original files: not stored
                </span>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={scrollToConfig}
                className="rounded-2xl border border-lime-300/20 bg-lime-300/10 px-4 py-3 text-sm font-medium text-lime-50 transition hover:border-lime-200/40 hover:bg-lime-300/20"
              >
                RAG Configuration
              </button>

              <button
                type="button"
                onClick={loadDocuments}
                disabled={loadingDocuments}
                className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-white transition hover:border-white/20 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loadingDocuments ? "Refreshing..." : "Refresh documents"}
              </button>
            </div>
          </section>

          {error ? (
            <div className="rounded-3xl border border-rose-300/20 bg-rose-300/10 p-4 text-sm text-rose-100">
              {error}
            </div>
          ) : null}

          {statusMessage ? (
            <div className="rounded-3xl border border-cyan-300/20 bg-cyan-300/10 p-4 text-sm text-cyan-100">
              {statusMessage}
            </div>
          ) : null}

          <div className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.25fr)]">
            <section className="space-y-6">
              <div className="soft-panel p-6">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.22em] text-cyan-200/70">
                      Document library
                    </p>
                    <h2 className="mt-2 text-xl font-semibold text-white">
                      Upload and index
                    </h2>
                    <p className="mt-2 text-sm leading-6 text-slate-400">
                      Phase 2A stores metadata, chunks, and embedding vectors in
                      local project storage. Original files are not persisted.
                    </p>
                  </div>
                </div>

                <div className="mt-5 rounded-3xl border border-dashed border-white/15 bg-black/20 p-4">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx,.txt,.md,.csv,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown,text/csv"
                    onChange={handleFileChange}
                    className="block w-full text-sm text-slate-300 file:mr-4 file:rounded-2xl file:border-0 file:bg-cyan-300/10 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-cyan-100 hover:file:bg-cyan-300/20"
                  />

                  {selectedFile ? (
                    <p className="mt-3 text-xs text-slate-400">
                      Selected:{" "}
                      <span className="font-semibold text-slate-200">
                        {selectedFile.name}
                      </span>{" "}
                      · {formatFileSize(selectedFile.size)}
                    </p>
                  ) : null}

                  <button
                    type="button"
                    onClick={handleUploadAndIndex}
                    disabled={indexing || !selectedFile}
                    className="mt-4 w-full rounded-2xl bg-cyan-300 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {indexing ? "Indexing document..." : "Upload and index"}
                  </button>
                </div>

                <div className="mt-5 space-y-3">
                  {documents.length ? (
                    documents.map((document) => {
                      const selected = selectedDocumentIds.includes(
                        document.id,
                      );

                      return (
                        <div
                          key={document.id}
                          className={`rounded-3xl border p-4 transition ${
                            selected
                              ? "border-emerald-300/30 bg-emerald-300/10"
                              : "border-white/10 bg-black/20"
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            <input
                              type="checkbox"
                              checked={selected}
                              onChange={() => toggleDocument(document.id)}
                              className="mt-1 h-4 w-4 rounded border-white/20 bg-black"
                            />

                            <div className="min-w-0 flex-1">
                              <p className="truncate text-sm font-semibold text-white">
                                {document.fileName}
                              </p>

                              <p className="mt-1 text-xs leading-5 text-slate-400">
                                {formatKind(document.kind)} ·{" "}
                                {formatFileSize(document.size)} ·{" "}
                                {document.chunkCount} chunks ·{" "}
                                {document.extractedChars.toLocaleString()} chars
                                {document.pageCount
                                  ? ` · ${document.pageCount} pages`
                                  : ""}
                              </p>

                              <p className="mt-1 text-xs text-slate-500">
                                {document.embeddingModel} ·{" "}
                                {formatDate(document.createdAt)}
                              </p>
                            </div>

                            <button
                              type="button"
                              onClick={() => handleDeleteDocument(document.id)}
                              className="rounded-xl border border-white/10 px-3 py-1 text-xs font-medium text-slate-400 transition hover:border-rose-300/30 hover:bg-rose-300/10 hover:text-rose-100"
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="rounded-3xl border border-white/10 bg-black/20 p-5 text-sm text-slate-400">
                      No indexed documents yet. Upload a document to create
                      local chunks and embeddings.
                    </div>
                  )}
                </div>
              </div>

              <div ref={configRef} className="soft-panel p-6 scroll-mt-6">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.22em] text-lime-200/70">
                      RAG Configuration
                    </p>
                    <h2 className="mt-2 text-xl font-semibold text-white">
                      Storage profile
                    </h2>
                    <p className="mt-2 text-sm leading-6 text-slate-400">
                      Phase 2B lets users choose safe storage profiles. Cloud
                      adapters are visible but disabled until Phase 2C.
                    </p>
                  </div>

                  <span className="rounded-full border border-lime-300/20 bg-lime-300/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-lime-100">
                    {ragConfig?.profile ?? "loading"}
                  </span>
                </div>

                <div className="mt-5 space-y-5">
                  <div className="rounded-3xl border border-lime-300/20 bg-lime-300/10 p-4">
                    <label className="block">
                      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-lime-100/80">
                        Editable now
                      </span>

                      <p className="mt-2 text-sm leading-6 text-slate-300">
                        Choose where Phase 2B document memory should live.
                        Cloud and BYO storage options stay locked until their
                        adapters are implemented.
                      </p>

                      <select
                        value={ragConfig?.profile ?? "local-json"}
                        disabled={savingConfig}
                        onChange={(event) =>
                          handleChangeStorageProfile(
                            event.target.value as DocumentStorageProfile,
                          )
                        }
                        className="mt-4 w-full rounded-2xl border border-lime-300/25 bg-black/40 px-4 py-3 text-sm font-semibold text-white outline-none transition focus:border-lime-200/60 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        <option value="local-json">Local project storage</option>
                        <option value="session">Session only</option>
                        <option value="supabase-pgvector">Supabase pgvector</option>
                      </select>

                      {savingConfig ? (
                        <p className="mt-2 text-xs text-lime-100">
                          Saving{" "}
                          {pendingProfile
                            ? profileLabel(pendingProfile)
                            : "configuration"}
                          ...
                        </p>
                      ) : null}
                    </label>
                  </div>

                  <div className="grid gap-3">
                    <button
                      type="button"
                      onClick={() => handleChangeStorageProfile("local-json")}
                      disabled={savingConfig}
                      className={[
                        "rounded-3xl border p-4 text-left transition disabled:cursor-not-allowed disabled:opacity-60",
                        ragConfig?.profile === "local-json"
                          ? "border-lime-300/40 bg-lime-300/10"
                          : "border-white/10 bg-black/20 hover:border-lime-300/25 hover:bg-lime-300/5",
                      ].join(" ")}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <p className="font-semibold text-white">
                          Local project storage
                        </p>
                        {ragConfig?.profile === "local-json" ? (
                          <span className="rounded-full border border-lime-300/20 bg-lime-300/10 px-3 py-1 text-xs font-semibold text-lime-100">
                            Active
                          </span>
                        ) : (
                          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold text-slate-300">
                            Click to activate
                          </span>
                        )}
                      </div>

                      <p className="mt-1 text-sm leading-6 text-slate-400">
                        Stores metadata, chunks, and vectors under{" "}
                        <code className="rounded bg-black/40 px-1 py-0.5 text-lime-100">
                          frontend/.data/document-memory
                        </code>
                        . Original files remain off.
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleChangeStorageProfile("session")}
                      disabled={savingConfig}
                      className={[
                        "rounded-3xl border p-4 text-left transition disabled:cursor-not-allowed disabled:opacity-60",
                        ragConfig?.profile === "session"
                          ? "border-cyan-300/40 bg-cyan-300/10"
                          : "border-white/10 bg-black/20 hover:border-cyan-300/25 hover:bg-cyan-300/5",
                      ].join(" ")}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <p className="font-semibold text-white">
                          Session only
                        </p>
                        {ragConfig?.profile === "session" ? (
                          <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-xs font-semibold text-cyan-100">
                            Active
                          </span>
                        ) : (
                          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold text-slate-300">
                            Click to activate
                          </span>
                        )}
                      </div>

                      <p className="mt-1 text-sm leading-6 text-slate-400">
                        Privacy-first profile for temporary document memory.
                        Original files are not stored. Full in-memory adapter
                        hardening comes next.
                      </p>
                    </button>
                  </div>

                  <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                          Storage layers
                        </p>
                        <p className="mt-1 text-sm text-slate-400">
                          These layer-level controls are locked in Phase 2B.
                          They become editable when Supabase, AWS, SQLite, and
                          export/import adapters are implemented.
                        </p>
                      </div>

                      <span className="rounded-full border border-amber-300/20 bg-amber-300/10 px-3 py-1 text-xs font-semibold text-amber-100">
                        Layer controls locked
                      </span>
                    </div>

                    <div className="mt-4 grid gap-3">
                      <label className="block">
                        <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
                          Original file storage
                        </span>
                        <select
                          value={ragConfig?.originalFileStorage ?? "none"}
                          disabled
                          className="mt-2 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-slate-500 outline-none"
                        >
                          <option value="none">
                            Off — original files are not stored
                          </option>
                        </select>
                        <p className="mt-1 text-xs text-slate-500">
                          Locked for privacy. Original file storage will require
                          explicit opt-in.
                        </p>
                      </label>

                      <label className="block">
                        <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
                          Metadata storage
                        </span>
                        <select
                          value={ragConfig?.metadataStorage ?? "local-json"}
                          disabled
                          className="mt-2 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-slate-500 outline-none"
                        >
                          <option value="local-json">Local JSON</option>
                          <option value="memory">Memory</option>
                          <option value="supabase-postgres">
                            Supabase Postgres — coming soon
                          </option>
                          <option value="aws-dynamodb">
                            AWS DynamoDB — coming soon
                          </option>
                        </select>
                      </label>

                      <label className="block">
                        <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
                          Vector storage
                        </span>
                        <select
                          value={ragConfig?.vectorStorage ?? "local-json"}
                          disabled
                          className="mt-2 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-slate-500 outline-none"
                        >
                          <option value="local-json">Local JSON</option>
                          <option value="memory">Memory</option>
                          <option value="supabase-pgvector">
                            Supabase pgvector — coming soon
                          </option>
                          <option value="aws-aurora">
                            AWS Aurora pgvector — coming soon
                          </option>
                          <option value="aws-opensearch">
                            AWS OpenSearch — enterprise only
                          </option>
                        </select>
                      </label>

                      <label className="block">
                        <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
                          History storage
                        </span>
                        <select
                          value={ragConfig?.historyStorage ?? "browser-local"}
                          disabled
                          className="mt-2 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-slate-500 outline-none"
                        >
                          <option value="browser-local">
                            Browser local history
                          </option>
                          <option value="local-json">
                            Local JSON — coming soon
                          </option>
                          <option value="supabase-postgres">
                            Supabase Postgres — coming soon
                          </option>
                          <option value="aws">AWS — coming soon</option>
                        </select>
                      </label>

                      <label className="block">
                        <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
                          Embedding model
                        </span>
                        <select
                          value={
                            ragConfig?.embeddingModel ??
                            "text-embedding-3-small"
                          }
                          disabled
                          className="mt-2 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-slate-500 outline-none"
                        >
                          <option value="text-embedding-3-small">
                            OpenAI text-embedding-3-small
                          </option>
                        </select>
                        <p className="mt-1 text-xs text-slate-500">
                          Changing embedding model later will require
                          re-indexing existing documents.
                        </p>
                      </label>
                    </div>
                  </div>

                  {disabledProfiles.length ? (
                    <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                        Coming later
                      </p>

                      <div className="mt-3 space-y-2">
                        {disabledProfiles.map((item) => (
                          <div
                            key={item.profile}
                            className="rounded-2xl border border-white/10 bg-white/5 p-3"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-3">
                              <p className="text-sm font-semibold text-slate-200">
                                {item.label}
                              </p>
                              <span className="rounded-full border border-white/10 bg-black/20 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                                Disabled
                              </span>
                            </div>
                            <p className="mt-1 text-xs leading-5 text-slate-500">
                              {item.reason}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  <button
                    type="button"
                    onClick={handleClearDocumentMemory}
                    className="w-full rounded-2xl border border-rose-300/30 bg-rose-300/10 px-4 py-3 text-sm font-semibold text-rose-100 transition hover:bg-rose-300/20"
                  >
                    Clear all local document memory
                  </button>
                </div>
              </div>
            </section>

            <section className="space-y-6">
              <div className="soft-panel p-6">
                <p className="text-xs uppercase tracking-[0.22em] text-emerald-200/70">
                  Ask documents
                </p>
                <h2 className="mt-2 text-xl font-semibold text-white">
                  Query selected document memory
                </h2>

                <div className="mt-5 grid gap-4 md:grid-cols-3">
                  <label className="space-y-2">
                    <span className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">
                      Provider
                    </span>
                    <select
                      value={providerId}
                      onChange={(event) => setProviderId(event.target.value)}
                      className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-300/40"
                    >
                      {providerOptions.map((provider) => (
                        <option key={provider.id} value={provider.id}>
                          {provider.name}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="space-y-2">
                    <span className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">
                      Task
                    </span>
                    <select
                      value={task}
                      onChange={(event) =>
                        setTask(event.target.value as FinanceTask)
                      }
                      className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-300/40"
                    >
                      {taskOptions.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.name}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="space-y-2">
                    <span className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">
                      Top-K sources
                    </span>
                    <input
                      type="number"
                      min={1}
                      max={12}
                      value={topK}
                      onChange={(event) =>
                        setTopK(Number(event.target.value) || 6)
                      }
                      className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-300/40"
                    />
                  </label>
                </div>

                <label className="mt-5 block space-y-2">
                  <span className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">
                    Question
                  </span>
                  <textarea
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    rows={6}
                    className="w-full rounded-3xl border border-white/10 bg-black/30 px-4 py-4 text-sm leading-7 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-300/40"
                    placeholder="Ask a question over the selected indexed documents..."
                  />
                </label>

                <div className="mt-5 rounded-3xl border border-white/10 bg-black/20 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                    Selected documents
                  </p>
                  {selectedDocuments.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {selectedDocuments.map((document) => (
                        <span
                          key={document.id}
                          className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1 text-xs font-medium text-emerald-100"
                        >
                          {document.fileName}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-2 text-sm text-slate-400">
                      No documents selected.
                    </p>
                  )}
                </div>

                <button
                  type="button"
                  onClick={handleAskQuestion}
                  disabled={querying || !selectedDocumentIds.length}
                  className="mt-5 w-full rounded-2xl bg-emerald-300 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {querying
                    ? "Searching documents..."
                    : "Ask selected documents"}
                </button>
              </div>

              <div className="soft-panel p-6">
                <p className="text-xs uppercase tracking-[0.22em] text-cyan-200/70">
                  Answer
                </p>

                {answer?.output ? (
                  <div className="mt-4 space-y-4">
                    <div className="rounded-3xl border border-white/10 bg-black/25 p-5">
                      <div className="mb-4 flex flex-wrap gap-2 text-xs">
                        {latestRequestId ? (
                          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-slate-300">
                            {latestRequestId}
                          </span>
                        ) : null}
                        {answer.provider ? (
                          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-slate-300">
                            {answer.provider}
                          </span>
                        ) : null}
                        {answer.model_id ? (
                          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-slate-300">
                            {answer.model_id}
                          </span>
                        ) : null}
                      </div>

                      <p className="whitespace-pre-wrap text-sm leading-7 text-slate-100">
                        {answer.output}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="mt-4 rounded-3xl border border-white/10 bg-black/20 p-6 text-sm text-slate-400">
                    Ask a question to generate a grounded answer from retrieved
                    document chunks.
                  </div>
                )}
              </div>

              <div className="soft-panel p-6">
                <p className="text-xs uppercase tracking-[0.22em] text-amber-200/70">
                  Retrieved sources
                </p>
                <h2 className="mt-2 text-xl font-semibold text-white">
                  Evidence used
                </h2>

                {sources.length ? (
                  <div className="mt-5 space-y-3">
                    {sources.map((source, index) => (
                      <details
                        key={source.chunkId}
                        className="rounded-3xl border border-white/10 bg-black/25 p-4"
                        open={index === 0}
                      >
                        <summary className="cursor-pointer list-none">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                              <p className="text-sm font-semibold text-white">
                                Source {index + 1}: {source.fileName}
                              </p>
                              <p className="mt-1 text-xs text-slate-400">
                                Chunk {source.chunkIndex}
                                {source.pageNumber
                                  ? ` · page ${source.pageNumber}`
                                  : ""}{" "}
                                · score {source.score.toFixed(3)}
                              </p>
                            </div>

                            <span className="rounded-full border border-amber-300/20 bg-amber-300/10 px-3 py-1 text-xs font-semibold text-amber-100">
                              Retrieved
                            </span>
                          </div>
                        </summary>

                        <p className="mt-4 rounded-2xl border border-white/10 bg-black/30 p-4 text-sm leading-7 text-slate-300">
                          {source.snippet}
                        </p>
                      </details>
                    ))}
                  </div>
                ) : (
                  <div className="mt-4 rounded-3xl border border-white/10 bg-black/20 p-6 text-sm text-slate-400">
                    Retrieved chunks will appear here after a document query.
                  </div>
                )}
              </div>
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}