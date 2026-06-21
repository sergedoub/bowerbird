import Anthropic from "@anthropic-ai/sdk";
import {
  MODEL_PROVIDERS,
  normalizeProvider,
  type ModelProviderKey,
  type ModelSettings,
} from "./modelConfig";

export type Summarizer = (prompt: string) => Promise<string>;

/** Returns the (prompt) => text summarizer, or null when no matching key is configured. */
export function summarizerFromEnv(env = process.env, settings?: ModelSettings): Summarizer | null {
  const provider = recapProviderFromEnv(env, settings);
  if (provider === "openai") return openaiSummarizer(env, settings);
  if (provider === "anthropic") return anthropicSummarizer(env, settings);
  if (provider === "gemini") return geminiSummarizer(env, settings);
  return null;
}

export function recapProviderFromEnv(
  env: Record<string, string | undefined>,
  settings?: ModelSettings,
): ModelProviderKey | "none" {
  const explicit = env.RECAP_PROVIDER?.trim();
  if (explicit && explicit.toLowerCase() === "none") return "none";
  if (explicit) return normalizeProvider(explicit);
  if (settings?.provider) return settings.provider;
  if (env.OPENAI_API_KEY) return "openai";
  if (env.ANTHROPIC_API_KEY) return "anthropic";
  if (env.GEMINI_API_KEY) return "gemini";
  return "none";
}

function modelFor(
  env: Record<string, string | undefined>,
  provider: ModelProviderKey,
  settings?: ModelSettings,
): string {
  if (env.RECAP_MODEL) return env.RECAP_MODEL;
  if (settings?.provider === provider && settings.recapModel) return settings.recapModel;
  if (settings?.provider === provider && settings.model) return settings.model;
  return MODEL_PROVIDERS[provider].defaultModel;
}

function openaiSummarizer(
  env: Record<string, string | undefined>,
  settings?: ModelSettings,
): Summarizer | null {
  const apiKey = env.OPENAI_API_KEY;
  if (!apiKey) return null;
  const model = modelFor(env, "openai", settings);
  return async (prompt: string) => {
    const response = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        input: prompt,
        max_output_tokens: 2000,
      }),
    });
    if (!response.ok) throw new Error(`OpenAI recap failed (${response.status})`);
    const data = (await response.json()) as { output_text?: string };
    return data.output_text ?? "";
  };
}

function anthropicSummarizer(
  env: Record<string, string | undefined>,
  settings?: ModelSettings,
): Summarizer | null {
  const apiKey = env.ANTHROPIC_API_KEY;
  if (!apiKey) return null;
  const model = modelFor(env, "anthropic", settings);
  const client = new Anthropic({ apiKey });
  return async (prompt: string) => {
    const response = await client.messages.create({
      model,
      max_tokens: 2000,
      messages: [{ role: "user", content: prompt }],
    });
    return response.content
      .filter((b): b is Anthropic.TextBlock => b.type === "text")
      .map((b) => b.text)
      .join("\n");
  };
}

function geminiSummarizer(
  env: Record<string, string | undefined>,
  settings?: ModelSettings,
): Summarizer | null {
  const apiKey = env.GEMINI_API_KEY;
  if (!apiKey) return null;
  const model = modelFor(env, "gemini", settings);
  return async (prompt: string) => {
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(
        model,
      )}:generateContent?key=${encodeURIComponent(apiKey)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: { maxOutputTokens: 2000 },
        }),
      },
    );
    if (!response.ok) throw new Error(`Gemini recap failed (${response.status})`);
    const data = (await response.json()) as {
      candidates?: { content?: { parts?: { text?: string }[] } }[];
    };
    return (
      data.candidates?.[0]?.content?.parts
        ?.map((part) => part.text ?? "")
        .join("\n") ?? ""
    );
  };
}
