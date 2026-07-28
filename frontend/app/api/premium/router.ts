import { callFinanceEks } from "./financeEks";
import { getPremiumProvider } from "./providers";
import type { PremiumInferenceInput, PremiumInferenceOutput } from "./types";
import { callOpenAI } from "./openai";
import { callAnthropic } from "./anthropic";

const allowedTasks = new Set(["summarize", "qa", "risk-analysis"]);

export function validatePremiumInput(input: unknown): PremiumInferenceInput {
  const value = input as Partial<PremiumInferenceInput>;

  if (!value.providerId || typeof value.providerId !== "string") {
    throw new Error("providerId is required");
  }

  const provider = getPremiumProvider(value.providerId);
  if (!provider) {
    throw new Error(`Unsupported premium provider: ${value.providerId}`);
  }

  if (!provider.enabled) {
    throw new Error(`Premium provider is not enabled yet: ${value.providerId}`);
  }

  if (!value.task || !allowedTasks.has(value.task)) {
    throw new Error("task must be summarize, qa, or risk-analysis");
  }

  if (!value.prompt || typeof value.prompt !== "string" || !value.prompt.trim()) {
    throw new Error("prompt is required");
  }

  if (value.prompt.length > 20000) {
    throw new Error("prompt is too large. Limit is 20,000 characters.");
  }

  if (value.context && value.context.length > 30000) {
    throw new Error("context is too large. Limit is 30,000 characters.");
  }

  const maxNewTokens = value.maxNewTokens ?? 512;
  if (maxNewTokens < 32 || maxNewTokens > 2048) {
    throw new Error("maxNewTokens must be between 32 and 2048");
  }

  const temperature = value.temperature ?? 0.2;
  if (temperature < 0 || temperature > 1.5) {
    throw new Error("temperature must be between 0 and 1.5");
  }

  return {
    providerId: value.providerId,
    task: value.task,
    mode: value.mode ?? "premium",
    prompt: value.prompt,
    context: value.context,
    temperature,
    maxNewTokens,
  };
}

export async function runPremiumInference(
  input: PremiumInferenceInput,
): Promise<PremiumInferenceOutput> {
  const startedAt = Date.now();

  if (input.providerId === "finance-eks") {
    return callFinanceEks(input, startedAt);
  }

  if (input.providerId === "openai-premium") {
    return callOpenAI(input, startedAt);
  }

  if (input.providerId === "claude-premium") {
    return callAnthropic(input, startedAt);
  }

  throw new Error(`Provider adapter is not implemented yet: ${input.providerId}`);
}