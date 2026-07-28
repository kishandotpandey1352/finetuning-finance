import type { PremiumProviderConfig, PremiumProviderId } from "./types";

export const premiumProviders: Record<PremiumProviderId, PremiumProviderConfig> = {
  "finance-eks": {
    id: "finance-eks",
    name: "Finance EKS 3B",
    provider: "finance-eks",
    modelId: "qwen2.5-3b-finance-runB-r16-lr2e4",
    tier: "premium",
    costClass: "self-hosted",
    privacy: "internal",
    enabled: true,
  },

  "openai-premium": {
    id: "openai-premium",
    name: "OpenAI Premium",
    provider: "openai",
    modelId: process.env.OPENAI_PREMIUM_MODEL ?? "env:OPENAI_PREMIUM_MODEL",
    tier: "premium",
    costClass: "paid-api",
    privacy: "external-provider",
    enabled: false,
  },

  "claude-premium": {
    id: "claude-premium",
    name: "Claude Premium",
    provider: "anthropic",
    modelId: process.env.ANTHROPIC_PREMIUM_MODEL ?? "env:ANTHROPIC_PREMIUM_MODEL",
    tier: "premium",
    costClass: "paid-api",
    privacy: "external-provider",
    enabled: false,
  },

  "gemini-premium": {
    id: "gemini-premium",
    name: "Gemini Premium",
    provider: "gemini",
    modelId: process.env.GEMINI_PREMIUM_MODEL ?? "env:GEMINI_PREMIUM_MODEL",
    tier: "premium",
    costClass: "paid-api",
    privacy: "external-provider",
    enabled: false,
  },

  "bedrock-premium": {
    id: "bedrock-premium",
    name: "Amazon Bedrock Premium",
    provider: "bedrock",
    modelId: process.env.BEDROCK_MODEL_ID ?? "env:BEDROCK_MODEL_ID",
    tier: "premium",
    costClass: "aws-managed",
    privacy: "aws-managed",
    enabled: false,
  },

  "vllm-qwen-7b": {
    id: "vllm-qwen-7b",
    name: "Self-hosted vLLM Qwen 7B",
    provider: "vllm",
    modelId: process.env.VLLM_MODEL_ID ?? "Qwen/Qwen2.5-7B-Instruct",
    tier: "premium",
    costClass: "self-hosted",
    privacy: "internal",
    enabled: false,
  },

  "ollama-local": {
    id: "ollama-local",
    name: "Ollama Local",
    provider: "ollama",
    modelId: process.env.OLLAMA_MODEL_ID ?? "llama3.1",
    tier: "premium",
    costClass: "free-local",
    privacy: "internal",
    enabled: false,
  },
};

export function getPremiumProvider(providerId: string) {
  return premiumProviders[providerId as PremiumProviderId];
}

export function listPremiumProviders() {
  return Object.values(premiumProviders);
}