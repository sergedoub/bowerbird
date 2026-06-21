import { parse as parseToml } from "smol-toml";

export type ModelProviderKey = "openai" | "anthropic" | "gemini";

export interface ModelProvider {
  key: ModelProviderKey;
  label: string;
  compileRunner: "codex" | "claude" | "gemini";
  apiKeyName: "OPENAI_API_KEY" | "ANTHROPIC_API_KEY" | "GEMINI_API_KEY";
  defaultModel: string;
}

export const MODEL_PROVIDERS: Record<ModelProviderKey, ModelProvider> = {
  openai: {
    key: "openai",
    label: "OpenAI / Codex",
    compileRunner: "codex",
    apiKeyName: "OPENAI_API_KEY",
    defaultModel: "gpt-5.4-mini",
  },
  anthropic: {
    key: "anthropic",
    label: "Anthropic / Claude",
    compileRunner: "claude",
    apiKeyName: "ANTHROPIC_API_KEY",
    defaultModel: "claude-opus-4-8",
  },
  gemini: {
    key: "gemini",
    label: "Google Gemini",
    compileRunner: "gemini",
    apiKeyName: "GEMINI_API_KEY",
    defaultModel: "gemini-2.5-flash",
  },
};

export interface ModelSettings {
  provider: ModelProviderKey;
  model: string;
  compileModel: string;
  recapModel: string;
}

export function defaultModelSettings(): ModelSettings {
  return {
    provider: "openai",
    model: "",
    compileModel: "",
    recapModel: "",
  };
}

export function normalizeProvider(value: unknown): ModelProviderKey {
  const key = String(value ?? "").trim().toLowerCase();
  if (key === "codex" || key === "openai") return "openai";
  if (key === "claude" || key === "anthropic") return "anthropic";
  if (key === "gemini" || key === "google") return "gemini";
  return "openai";
}

export function parseModelSettings(toml: string): ModelSettings {
  if (!toml.trim()) return defaultModelSettings();
  const data = parseToml(toml) as {
    model?: { provider?: unknown; model?: unknown };
    compile?: { provider?: unknown; model?: unknown };
    recap?: { provider?: unknown; model?: unknown };
  };
  const provider = normalizeProvider(
    data.model?.provider ?? data.compile?.provider ?? data.recap?.provider,
  );
  const model = String(data.model?.model ?? "");
  const compileModel = String(data.compile?.model ?? "");
  const recapModel = String(data.recap?.model ?? "");
  return {
    provider,
    model: model || (compileModel && compileModel === recapModel ? compileModel : ""),
    compileModel,
    recapModel,
  };
}

export function serializeModelSettings(settings: ModelSettings): string {
  const provider = MODEL_PROVIDERS[settings.provider] ?? MODEL_PROVIDERS.openai;
  const model = settings.model.trim();
  const compileModel = settings.compileModel.trim();
  const recapModel = settings.recapModel.trim();
  const lines = [
    "# Model provider selection. Managed by the Bowerbird web dashboard.",
    "",
    "[model]",
    `provider = "${provider.key}"`,
  ];
  if (model) lines.push(`model = "${model}"`);
  if (compileModel && compileModel !== model) lines.push("", "[compile]", `model = "${compileModel}"`);
  if (recapModel && recapModel !== model) lines.push("", "[recap]", `model = "${recapModel}"`);
  lines.push("");
  return lines.join("\n");
}

export function validateModelSettings(settings: ModelSettings): string[] {
  const problems: string[] = [];
  if (!MODEL_PROVIDERS[settings.provider]) problems.push("unknown model provider");
  for (const [label, value] of [
    ["compile model", settings.compileModel],
    ["recap model", settings.recapModel],
    ["model", settings.model],
  ] as const) {
    if (/["\n\r]/.test(value)) problems.push(`${label} must not contain quotes or newlines`);
  }
  return problems;
}
