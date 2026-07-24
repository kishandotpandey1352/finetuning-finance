import type {
  ChatRequestInput,
  ComparisonRequestInput,
  ComparisonResult,
  FinanceResponse,
  UsageMetadata,
} from "@/types";

const DEFAULT_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const USE_MOCK_BACKEND = (process.env.NEXT_PUBLIC_USE_MOCK_BACKEND ?? "true").toLowerCase() === "true";

function now() {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}

function toTokenCount(text: string) {
  return Math.max(1, Math.round(text.trim().split(/\s+/).filter(Boolean).length * 1.2));
}

function requestUrl(path: string) {
  return `${DEFAULT_API_BASE_URL.replace(/\/$/, "")}${path}`;
}

function requestHeaders(accessToken?: string) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (accessToken?.trim()) {
    headers["X-API-Key"] = accessToken.trim();
    headers.Authorization = `Bearer ${accessToken.trim()}`;
  }

  return headers;
}

function buildUsage(params: {
  provider: string;
  modelId: string;
  task: UsageMetadata["task"];
  prompt: string;
  output: string;
  latencyMs: number;
  source: UsageMetadata["source"];
}): UsageMetadata {
  const promptTokens = toTokenCount(params.prompt);
  const completionTokens = toTokenCount(params.output);

  return {
    provider: params.provider,
    modelId: params.modelId,
    task: params.task,
    promptTokens,
    completionTokens,
    totalTokens: promptTokens + completionTokens,
    latencyMs: Math.max(1, Math.round(params.latencyMs)),
    source: params.source,
  };
}

function titleFromPrompt(prompt: string, prefix: string) {
  const cleaned = prompt.replace(/\s+/g, " ").trim();
  const snippet = cleaned.slice(0, 64);

  if (cleaned.length <= 64) {
    return `${prefix}: ${snippet}`;
  }

  return `${prefix}: ${snippet}...`;
}

function mockOutput(input: ChatRequestInput, variant = 0) {
  const seeds = [
    "The filing suggests steady revenue momentum, but margin expansion depends on cost control and working-capital discipline.",
    "Cash flow remains constructive, yet leverage, refinancing cadence, and guidance credibility deserve monitoring.",
    "The risk profile centers on execution, pricing pressure, and sensitivity to macro demand in the next two quarters.",
  ];

  const base = seeds[variant % seeds.length];
  const providerLabel = `${input.provider.provider} / ${input.provider.name}`;

  return `${base} This mock response was generated for ${providerLabel} in ${input.mode} mode against the ${input.task} workflow. Prompt focus: ${input.prompt.slice(0, 80)}${input.prompt.length > 80 ? "..." : ""}`;
}

function mockResponse(input: ChatRequestInput, variant = 0): FinanceResponse {
  const started = now();
  const output = mockOutput(input, variant);
  const latencyMs = Math.round(180 + variant * 35 + input.prompt.length * 1.3);

  return {
    id: `mock-${Date.now()}-${variant}`,
    prompt: input.prompt,
    title: titleFromPrompt(input.prompt, input.task === "qa" ? "Question" : "Analysis"),
    output,
    provider: input.provider.provider,
    modelId: input.provider.modelId,
    task: input.task,
    mode: input.mode,
    createdAt: new Date().toISOString(),
    usage: buildUsage({
      provider: input.provider.provider,
      modelId: input.provider.modelId,
      task: input.task,
      prompt: input.prompt,
      output,
      latencyMs: latencyMs + Math.max(0, now() - started),
      source: "mock",
    }),
  };
}

async function postJson<T>(path: string, body: unknown, accessToken?: string): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(requestUrl(path), {
      method: "POST",
      headers: requestHeaders(accessToken),
      body: JSON.stringify(body),
      signal: controller.signal,
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    return (await response.json()) as T;
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function sendFinancePrompt(input: ChatRequestInput): Promise<FinanceResponse> {
  if (USE_MOCK_BACKEND || !input.accessToken) {
    return mockResponse(input);
  }

  const startedAt = now();

  try {
    if (input.task === "summarize") {
      const payload = await postJson<{ summary: string; model_id: string }>("/summarize", {
        text: input.prompt,
        max_new_tokens: input.maxNewTokens ?? input.provider.defaultMaxNewTokens,
        temperature: input.temperature ?? input.provider.defaultTemperature,
      }, input.accessToken);

      const output = payload.summary;

      return {
        id: `live-${Date.now()}`,
        prompt: input.prompt,
        title: titleFromPrompt(input.prompt, "Summary"),
        output,
        provider: input.provider.provider,
        modelId: payload.model_id ?? input.provider.modelId,
        task: input.task,
        mode: input.mode,
        createdAt: new Date().toISOString(),
        usage: buildUsage({
          provider: input.provider.provider,
          modelId: payload.model_id ?? input.provider.modelId,
          task: input.task,
          prompt: input.prompt,
          output,
          latencyMs: now() - startedAt,
          source: "live",
        }),
      };
    }

    if (input.task === "qa") {
      const payload = await postJson<{ answer: string; model_id: string }>("/qa", {
        question: input.prompt,
        context: input.context,
        max_new_tokens: input.maxNewTokens ?? input.provider.defaultMaxNewTokens,
        temperature: input.temperature ?? input.provider.defaultTemperature,
      }, input.accessToken);

      const output = payload.answer;

      return {
        id: `live-${Date.now()}`,
        prompt: input.prompt,
        title: titleFromPrompt(input.prompt, "Answer"),
        output,
        provider: input.provider.provider,
        modelId: payload.model_id ?? input.provider.modelId,
        task: input.task,
        mode: input.mode,
        createdAt: new Date().toISOString(),
        usage: buildUsage({
          provider: input.provider.provider,
          modelId: payload.model_id ?? input.provider.modelId,
          task: input.task,
          prompt: `${input.context ?? ""}\n${input.prompt}`,
          output,
          latencyMs: now() - startedAt,
          source: "live",
        }),
      };
    }

    const payload = await postJson<{ risk_analysis: string; model_id: string }>("/risk-analysis", {
      text: input.prompt,
      max_new_tokens: input.maxNewTokens ?? input.provider.defaultMaxNewTokens,
      temperature: input.temperature ?? input.provider.defaultTemperature,
    }, input.accessToken);

    const output = payload.risk_analysis;

    return {
      id: `live-${Date.now()}`,
      prompt: input.prompt,
      title: titleFromPrompt(input.prompt, "Risk analysis"),
      output,
      provider: input.provider.provider,
      modelId: payload.model_id ?? input.provider.modelId,
      task: input.task,
      mode: input.mode,
      createdAt: new Date().toISOString(),
      usage: buildUsage({
        provider: input.provider.provider,
        modelId: payload.model_id ?? input.provider.modelId,
        task: input.task,
        prompt: input.prompt,
        output,
        latencyMs: now() - startedAt,
        source: "live",
      }),
    };
  } catch {
    return mockResponse(input);
  }
}

export async function runComparison(input: ComparisonRequestInput): Promise<ComparisonResult> {
  const left = await sendFinancePrompt({
    task: input.task,
    prompt: input.prompt,
    context: input.context,
    provider: input.leftProvider,
    mode: "compare",
    accessToken: input.accessToken,
  });

  const right = await sendFinancePrompt({
    task: input.task,
    prompt: input.prompt,
    context: input.context,
    provider: input.rightProvider,
    mode: "compare",
    accessToken: input.accessToken,
    temperature: input.rightProvider.defaultTemperature + 0.05,
  });

  return { left, right };
}
