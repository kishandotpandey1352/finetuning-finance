import type {
  ChatRequestInput,
  ComparisonRequestInput,
  ComparisonResult,
  FinanceResponse,
  UsageMetadata,
} from "@/types";

const USE_MOCK_BACKEND =
  (process.env.NEXT_PUBLIC_USE_MOCK_BACKEND ?? "true").toLowerCase() === "true";

type InferenceResponse = {
  id?: string;
  provider?: string;
  providerId?: string;
  model_id?: string;
  output?: string;
  latency_ms?: number;
  source?: "premium" | "basic" | "live" | "mock";
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
};

function now() {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}

function toTokenCount(text: string) {
  return Math.max(
    1,
    Math.round(text.trim().split(/\s+/).filter(Boolean).length * 1.2),
  );
}

function getTaskEndpoint(task: ChatRequestInput["task"]) {
  if (task === "summarize") {
    return "/api/backend/summarize";
  }

  if (task === "qa") {
    return "/api/backend/qa";
  }

  return "/api/backend/risk-analysis";
}

function getPremiumProviderId(provider: ChatRequestInput["provider"]) {
  if (provider.provider === "finance-eks") {
    return "finance-eks";
  }

  return provider.id;
}

function shouldUsePremiumRoute(input: ChatRequestInput) {
  if (input.mode === "premium") {
    return true;
  }

  if (input.mode === "compare") {
    return input.provider.tier === "premium";
  }

  return false;
}

function buildBasicRequestBody(input: ChatRequestInput) {
  const maxNewTokens = input.maxNewTokens ?? input.provider.defaultMaxNewTokens;
  const temperature = input.temperature ?? input.provider.defaultTemperature;
  const context = input.context?.trim();

  if (input.task === "summarize") {
    return {
      text: context
        ? `${input.prompt}\n\nInstructions:\n${context}`
        : input.prompt,
      max_new_tokens: maxNewTokens,
      temperature,
    };
  }

  if (input.task === "qa") {
    return {
      question: input.prompt,
      context: context ?? "",
      max_new_tokens: maxNewTokens,
      temperature,
    };
  }

  return {
    text: context
      ? `${input.prompt}\n\nRisk focus:\n${context}`
      : input.prompt,
    max_new_tokens: maxNewTokens,
    temperature,
  };
}

function buildPremiumRequestBody(input: ChatRequestInput) {
  return {
    providerId: getPremiumProviderId(input.provider),
    mode: input.mode === "compare" ? "compare" : "premium",
    task: input.task,
    prompt: input.prompt,
    context: input.context ?? "",
    temperature: input.temperature ?? input.provider.defaultTemperature,
    maxNewTokens: input.maxNewTokens ?? input.provider.defaultMaxNewTokens,
  };
}

function buildUsage(params: {
  provider: string;
  modelId: string;
  task: UsageMetadata["task"];
  prompt: string;
  output: string;
  latencyMs: number;
  source: UsageMetadata["source"];
  promptTokens?: number;
  completionTokens?: number;
  totalTokens?: number;
}): UsageMetadata {
  const estimatedPromptTokens = toTokenCount(params.prompt);
  const estimatedCompletionTokens = toTokenCount(params.output);

  const promptTokens = params.promptTokens ?? estimatedPromptTokens;
  const completionTokens = params.completionTokens ?? estimatedCompletionTokens;
  const totalTokens =
    params.totalTokens ?? Math.max(1, promptTokens + completionTokens);

  return {
    provider: params.provider,
    modelId: params.modelId,
    task: params.task,
    promptTokens,
    completionTokens,
    totalTokens,
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

function titleFromTask(input: ChatRequestInput) {
  if (input.task === "summarize") {
    return titleFromPrompt(input.prompt, "Finance Summary");
  }

  if (input.task === "qa") {
    return titleFromPrompt(input.prompt, "Finance Q&A");
  }

  return titleFromPrompt(input.prompt, "Risk Analysis");
}

function mockOutput(input: ChatRequestInput, variant = 0) {
  const seeds = [
    "The filing suggests steady revenue momentum, but margin expansion depends on cost control and working-capital discipline.",
    "Cash flow remains constructive, yet leverage, refinancing cadence, and guidance credibility deserve monitoring.",
    "The risk profile centers on execution, pricing pressure, and sensitivity to macro demand in the next two quarters.",
  ];

  const base = seeds[variant % seeds.length];
  const providerLabel = `${input.provider.provider} / ${input.provider.name}`;

  return `${base} This mock response was generated for ${providerLabel} in ${input.mode} mode against the ${input.task} workflow. Prompt focus: ${input.prompt.slice(
    0,
    80,
  )}${input.prompt.length > 80 ? "..." : ""}`;
}

function mockResponse(input: ChatRequestInput, variant = 0): FinanceResponse {
  const started = now();
  const output = mockOutput(input, variant);
  const latencyMs = Math.round(180 + variant * 35 + input.prompt.length * 1.3);

  return {
    id: `mock-${Date.now()}-${variant}`,
    prompt: input.prompt,
    title: titleFromTask(input),
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

function failedComparisonResponse(
  input: ChatRequestInput,
  error: unknown,
): FinanceResponse {
  const message =
    error instanceof Error ? error.message : "Provider request failed";

  return {
    id: `error-${Date.now()}-${input.provider.id}`,
    prompt: input.prompt,
    title: `${input.provider.name} failed`,
    output: `Provider unavailable: ${message}`,
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
      output: message,
      latencyMs: 1,
      source: "live",
      promptTokens: 0,
      completionTokens: 0,
      totalTokens: 0,
    }),
  };
}

async function postInference(input: ChatRequestInput): Promise<InferenceResponse> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 10 * 60 * 1000);

  const startedAt = now();
  const isPremium = shouldUsePremiumRoute(input);

  const endpoint = isPremium
    ? "/api/premium/inference"
    : getTaskEndpoint(input.task);

  const body = isPremium
    ? buildPremiumRequestBody(input)
    : buildBasicRequestBody(input);

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      signal: controller.signal,
      cache: "no-store",
    });

    const text = await response.text();

    if (!response.ok) {
      try {
        const errorPayload = JSON.parse(text) as { error?: string };
        throw new Error(
          errorPayload.error || `Request failed with status ${response.status}`,
        );
      } catch {
        throw new Error(text || `Request failed with status ${response.status}`);
      }
    }

    const payload = JSON.parse(text) as InferenceResponse;

    return {
      ...payload,
      latency_ms:
        payload.latency_ms ?? Math.max(1, Math.round(now() - startedAt)),
    };
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function sendFinancePrompt(
  input: ChatRequestInput,
): Promise<FinanceResponse> {
  if (USE_MOCK_BACKEND) {
    return mockResponse(input);
  }

  const startedAt = now();
  const payload = await postInference(input);
  const createdAt = new Date().toISOString();

  const output = payload.output ?? "";
  const provider = payload.provider ?? input.provider.provider;
  const modelId = payload.model_id ?? input.provider.modelId;
  const latencyMs =
    payload.latency_ms ?? Math.max(1, Math.round(now() - startedAt));

  return {
    id: payload.id ?? `response-${Date.now()}`,
    prompt: input.prompt,
    title: titleFromTask(input),
    output,
    provider,
    modelId,
    task: input.task,
    mode: input.mode,
    createdAt,
    usage: buildUsage({
      provider,
      modelId,
      task: input.task,
      prompt: input.prompt,
      output,
      latencyMs,
      source: "live",
      promptTokens: payload.usage?.prompt_tokens,
      completionTokens: payload.usage?.completion_tokens,
      totalTokens: payload.usage?.total_tokens,
    }),
  };
}

export async function runComparison(
  input: ComparisonRequestInput,
): Promise<ComparisonResult> {
  if (USE_MOCK_BACKEND) {
    const left = mockResponse(
      {
        task: input.task,
        prompt: input.prompt,
        context: input.context,
        provider: input.leftProvider,
        mode: "compare",
        accessToken: input.accessToken,
        temperature: input.leftProvider.defaultTemperature,
        maxNewTokens: input.leftProvider.defaultMaxNewTokens,
      },
      0,
    );

    const right = mockResponse(
      {
        task: input.task,
        prompt: input.prompt,
        context: input.context,
        provider: input.rightProvider,
        mode: "compare",
        accessToken: input.accessToken,
        temperature: input.rightProvider.defaultTemperature + 0.05,
        maxNewTokens: input.rightProvider.defaultMaxNewTokens,
      },
      1,
    );

    return { left, right };
  }

  const leftInput: ChatRequestInput = {
    task: input.task,
    prompt: input.prompt,
    context: input.context,
    provider: input.leftProvider,
    mode: "compare",
    accessToken: input.accessToken,
    temperature: input.leftProvider.defaultTemperature,
    maxNewTokens: input.leftProvider.defaultMaxNewTokens,
  };

  const rightInput: ChatRequestInput = {
    task: input.task,
    prompt: input.prompt,
    context: input.context,
    provider: input.rightProvider,
    mode: "compare",
    accessToken: input.accessToken,
    temperature: input.rightProvider.defaultTemperature + 0.05,
    maxNewTokens: input.rightProvider.defaultMaxNewTokens,
  };

  const [leftResult, rightResult] = await Promise.allSettled([
    sendFinancePrompt(leftInput),
    sendFinancePrompt(rightInput),
  ]);

  const left =
    leftResult.status === "fulfilled"
      ? leftResult.value
      : failedComparisonResponse(leftInput, leftResult.reason);

  const right =
    rightResult.status === "fulfilled"
      ? rightResult.value
      : failedComparisonResponse(rightInput, rightResult.reason);

  return {
    left,
    right,
  };
}