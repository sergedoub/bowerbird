// Config model: round-trip fidelity and the validation rules that protect the
// pipeline (mirrors kb.config). Corrupting a user's TOML is the worst bug this app
// can have — these tests are the guardrail.
import { describe, expect, it } from "vitest";
import {
  ConfigValidationError,
  parseAccounts,
  parseTopics,
  serializeAccounts,
  serializeTopics,
  validateAccounts,
  validateConfig,
  validateTopics,
} from "@/lib/configModel";

const TOPICS_TOML = `# comment
[topics.marketing]
folder_ids = ["111", "222"]

[topics.ai]
folder_ids = ["333"]
`;

const ACCOUNTS_TOML = `[[handles]]
handle = "bcherny"
topic = "claude-code"
label = "Boris (Anthropic)"
off_topic = "skip"

[[handles]]
handle = "@OfficialLoganK"
topic = "google-ai"
off_topic = "skip"
`;

describe("topics", () => {
  it("parses names and folder ids", () => {
    expect(parseTopics(TOPICS_TOML)).toEqual([
      { name: "marketing", folderIds: ["111", "222"] },
      { name: "ai", folderIds: ["333"] },
    ]);
  });

  it("round-trips through serialize -> parse", () => {
    const parsed = parseTopics(TOPICS_TOML);
    expect(parseTopics(serializeTopics(parsed))).toEqual(parsed);
  });

  it("rejects a folder mapped to two topics (the kb.config rule)", () => {
    const problems = validateTopics([
      { name: "a", folderIds: ["1"] },
      { name: "b", folderIds: ["1"] },
    ]);
    expect(problems.join()).toContain("mapped to both 'a' and 'b'");
  });

  it("rejects empty folder lists, bad ids, bad names, duplicates", () => {
    const problems = validateTopics([
      { name: "Bad Name", folderIds: [] },
      { name: "ok", folderIds: ["abc"] },
      { name: "ok", folderIds: ["2"] },
    ]);
    expect(problems.some((p) => p.includes("lowercase slug"))).toBe(true);
    expect(problems.some((p) => p.includes("no folder ids"))).toBe(true);
    expect(problems.some((p) => p.includes("must be numeric"))).toBe(true);
    expect(problems.some((p) => p.includes("duplicate topic"))).toBe(true);
  });
});

describe("accounts", () => {
  it("parses handles, strips leading @, keeps labels", () => {
    expect(parseAccounts(ACCOUNTS_TOML)).toEqual([
      { handle: "bcherny", topic: "claude-code", offTopic: "skip", label: "Boris (Anthropic)" },
      { handle: "OfficialLoganK", topic: "google-ai", offTopic: "skip", label: undefined },
    ]);
  });

  it("round-trips through serialize -> parse", () => {
    const parsed = parseAccounts(ACCOUNTS_TOML);
    expect(parseAccounts(serializeAccounts(parsed))).toEqual(parsed);
  });

  it("rejects duplicates case-insensitively, bad handles, bad policies", () => {
    const problems = validateAccounts([
      { handle: "bcherny", topic: "t", offTopic: "skip" },
      { handle: "BCherny", topic: "t", offTopic: "skip" },
      { handle: "way-too-long-for-an-x-handle!", topic: "t", offTopic: "skip" },
      { handle: "ok_handle", topic: "t", offTopic: "explode" as never },
    ]);
    expect(problems.some((p) => p.includes("duplicate handle"))).toBe(true);
    expect(problems.some((p) => p.includes("not a valid X username"))).toBe(true);
    expect(problems.some((p) => p.includes("unknown off_topic"))).toBe(true);
  });

  it("rejects labels that would break the TOML line", () => {
    const problems = validateAccounts([
      { handle: "ok", topic: "t", offTopic: "skip", label: 'evil " quote' },
    ]);
    expect(problems.some((p) => p.includes("label"))).toBe(true);
  });
});

describe("validateConfig", () => {
  it("collects every problem across both files into one error", () => {
    expect(() =>
      validateConfig({
        topics: [{ name: "ok", folderIds: [] }],
        accounts: [{ handle: "!!", topic: "Bad Topic", offTopic: "skip" }],
      }),
    ).toThrow(ConfigValidationError);
    try {
      validateConfig({
        topics: [{ name: "ok", folderIds: [] }],
        accounts: [{ handle: "!!", topic: "Bad Topic", offTopic: "skip" }],
      });
    } catch (e) {
      expect((e as ConfigValidationError).problems.length).toBe(3);
    }
  });

  it("accepts the shipped sample-shaped config", () => {
    expect(() =>
      validateConfig({
        topics: [{ name: "getting-started", folderIds: ["9100000000000000001"] }],
        accounts: [
          { handle: "bcherny", topic: "claude-code", offTopic: "skip", label: "Boris (Anthropic)" },
        ],
      }),
    ).not.toThrow();
  });
});
