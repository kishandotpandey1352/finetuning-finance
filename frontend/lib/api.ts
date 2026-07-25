import type {
  ChatRequestInput,
  ComparisonRequestInput,
  ComparisonResult,
  FinanceResponse,
  UsageMetadata,
} from "@/types";

const USE_MOCK_BACKEND =
  (process.env.NEXT_PUBLIC_USE_MOCK_BACKEND ?? "true").toLowerCase() === "true";

type LiveInferenceResponse = {
  model_id: string;
  output: string;
};

function now() {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}

function toTokenCount(text: string) {
  return Math.max(1, Math.round(text.trim().split(/\s+/).filter(Boolean).length * 1.2));
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

function buildRequestBody(input: ChatRequestInput) {
  const maxNewTokens = input.maxNewTokens ?? input.provider.defaultMaxNewTokens;
  const temperature = input.temperature ?? input.provider.defaultTemperature;

  if (input.task === "summarize") {
    return {
      text: input.prompt,
      max_new_tokens: maxNewTokens,
      temperature,
    };
  }

  if (input.task === "qa") {
    return {
      question: input.prompt,
      context: input.context ?? "",
      max_new_tokens: maxNewTokens,
      temperature,
    };
  }

  return {
    text: input.prompt,
    max_new_tokens: maxNewTokens,
    temperature,
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

async function postInference(input: ChatRequestInput): Promise<LiveInferenceResponse> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 10 * 60 * 1000);

  try {
    const response = await fetch(getTaskEndpoint(input.task), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(buildRequestBody(input)),
      signal: controller.signal,
      cache: "no-store",
    });

    const text = await response.text();

    if (!response.ok) {
      throw new Error(text || `Request failed with status ${response.status}`);
    }

    return JSON.parse(text) as LiveInferenceResponse;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function sendFinancePrompt(input: ChatRequestInput): Promise<FinanceResponse> {
  if (USE_MOCK_BACKEND) {
    return mockResponse(input);
  }

  const startedAt = now();
  const payload = await postInference(input);
  const output = payload.output;
  const modelId = payload.model_id ?? input.provider.modelId;

  return {
    id: `live-${Date.now()}`,
    prompt: input.prompt,
    title: titleFromPrompt(
      input.prompt,
      input.task === "summarize"
        ? "Summary"
        : input.task === "qa"
          ? "Answer"
          : "Risk analysis",
    ),
    output,
    provider: input.provider.provider,
    modelId,
    task: input.task,
    mode: input.mode,
    createdAt: new Date().toISOString(),
    usage: buildUsage({
      provider: input.provider.provider,
      modelId,
      task: input.task,
      prompt: input.task === "qa" ? `${input.context ?? ""}\n${input.prompt}` : input.prompt,
      output,
      latencyMs: now() - startedAt,
      source: "live",
    }),
  };
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
