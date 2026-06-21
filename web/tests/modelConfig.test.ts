import { describe, expect, it } from "vitest";
import {
  defaultModelSettings,
  parseModelSettings,
  serializeModelSettings,
  validateModelSettings,
} from "@/lib/modelConfig";

describe("model provider config", () => {
  it("defaults to OpenAI/Codex", () => {
    expect(defaultModelSettings()).toEqual({
      provider: "openai",
      model: "",
      compileModel: "",
      recapModel: "",
    });
  });

  it("round-trips through TOML", () => {
    const settings = {
      provider: "openai" as const,
      model: "gpt-5.4",
      compileModel: "",
      recapModel: "",
    };
    expect(parseModelSettings(serializeModelSettings(settings))).toEqual(settings);
  });

  it("accepts provider aliases and validates model ids", () => {
    expect(parseModelSettings('[compile]\nprovider = "codex"\n')).toMatchObject({
      provider: "openai",
      model: "",
    });
    expect(
      validateModelSettings({
        provider: "openai",
        model: "",
        compileModel: 'bad"model',
        recapModel: "ok",
      }),
    ).toContain("compile model must not contain quotes or newlines");
  });
});
