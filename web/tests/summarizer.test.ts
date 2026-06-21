import { describe, expect, it } from "vitest";
import { recapProviderFromEnv } from "@/lib/summarizer";

describe("recap provider selection", () => {
  it("honors an explicit provider", () => {
    expect(recapProviderFromEnv({ RECAP_PROVIDER: "codex", OPENAI_API_KEY: "key" })).toBe("openai");
    expect(recapProviderFromEnv({ RECAP_PROVIDER: "none", OPENAI_API_KEY: "key" })).toBe("none");
  });

  it("infers provider from staged API keys", () => {
    expect(recapProviderFromEnv({ OPENAI_API_KEY: "key" })).toBe("openai");
    expect(recapProviderFromEnv({ ANTHROPIC_API_KEY: "key" })).toBe("anthropic");
    expect(recapProviderFromEnv({ GEMINI_API_KEY: "key" })).toBe("gemini");
    expect(recapProviderFromEnv({})).toBe("none");
  });

  it("uses saved model settings before key inference", () => {
    expect(
      recapProviderFromEnv(
        { OPENAI_API_KEY: "key" },
        { provider: "gemini", model: "", compileModel: "", recapModel: "gemini-2.5-flash" },
      ),
    ).toBe("gemini");
  });
});
