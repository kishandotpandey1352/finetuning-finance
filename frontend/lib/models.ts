import type { FinanceTask, ProviderOption } from "@/types";

export const tasks: Array<{ value: FinanceTask; label: string; description: string }> = [
  {
    value: "summarize",
    label: "Summarize",
    description: "Condense earnings, filings, or guidance into an executive brief.",
  },
  {
    value: "qa",
    label: "Q&A",
    description: "Answer investor, risk, or operations questions from context.",
  },
  {
    value: "risk-analysis",
    label: "Risk analysis",
    description: "Extract market, credit, liquidity, operational, and business risk.",
  },
];

export const providerCatalog: ProviderOption[] = [
  {
    id: "finance-base",
    name: "Finance Base",
    provider: "Local vLLM",
    description: "Baseline model routed through the secure FastAPI gateway.",
    tier: "basic",
    modelId: "qwen2.5-3b-base",
    defaultTemperature: 0.15,
    defaultMaxNewTokens: 256,
  },
  {
    id: "finance-adapter",
    name: "Finance Adapter",
    provider: "Local vLLM",
    description: "QLoRA adapter tuned for finance summarization and QA.",
    tier: "premium",
    modelId: "qwen2.5-3b-finance-runB-r16-lr2e4",
    defaultTemperature: 0.2,
    defaultMaxNewTokens: 320,
  },
  {
    id: "openai-4_1",
    name: "GPT-4.1",
    provider: "OpenAI",
    description: "Cloud provider comparison target for premium prompts.",
    tier: "premium",
    modelId: "gpt-4.1",
    defaultTemperature: 0.2,
    defaultMaxNewTokens: 320,
  },
  {
    id: "claude-sonnet",
    name: "Claude Sonnet",
    provider: "Anthropic",
    description: "Alternative reasoning profile for side-by-side evaluation.",
    tier: "premium",
    modelId: "claude-sonnet-4",
    defaultTemperature: 0.25,
    defaultMaxNewTokens: 320,
  },
  {
    id: "llama-premium",
    name: "Llama 3.1",
    provider: "Together AI",
    description: "High-throughput premium fallback for latency comparisons.",
    tier: "premium",
    modelId: "llama-3.1-70b-instruct",
    defaultTemperature: 0.25,
    defaultMaxNewTokens: 384,
  },
];

export const comparisonPairs = [
  {
    left: "finance-adapter",
    right: "openai-4_1",
    label: "Adapter vs GPT-4.1",
  },
  {
    left: "finance-adapter",
    right: "claude-sonnet",
    label: "Adapter vs Claude Sonnet",
  },
  {
    left: "finance-base",
    right: "finance-adapter",
    label: "Base vs Adapter",
  },
];

export function getProviderById(providerId: string): ProviderOption {
  const provider = providerCatalog.find((item) => item.id === providerId);

  if (!provider) {
    return providerCatalog[0];
  }

  return provider;
}

export function getProvidersByTier(tier: ProviderOption["tier"]) {
  return providerCatalog.filter((provider) => provider.tier === tier);
}
