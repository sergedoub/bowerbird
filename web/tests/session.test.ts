// Session cookie: seal/open round-trip, tamper rejection, missing-secret behavior.
import { describe, expect, it } from "vitest";
import { openSession, sealSession } from "@/lib/session";

const env = { SESSION_SECRET: "0123456789abcdef0123456789abcdef" };

describe("session JWT", () => {
  it("round-trips username, token, and user id", async () => {
    const jwt = await sealSession(
      { username: "alice", xAccessToken: "at", xUserId: "42" },
      env,
    );
    expect(await openSession(jwt, env)).toEqual({
      username: "alice",
      xAccessToken: "at",
      xUserId: "42",
    });
  });

  it("rejects tampered or garbage tokens", async () => {
    const jwt = await sealSession({ username: "alice" }, env);
    expect(await openSession(jwt.slice(0, -2) + "xx", env)).toBeNull();
    expect(await openSession("garbage", env)).toBeNull();
    expect(await openSession(undefined, env)).toBeNull();
  });

  it("rejects tokens signed with a different secret", async () => {
    const jwt = await sealSession({ username: "alice" }, env);
    const other = { SESSION_SECRET: "another-secret-another-secret" };
    expect(await openSession(jwt, other)).toBeNull();
  });

  it("demands a real secret", async () => {
    await expect(
      sealSession({ username: "s" }, { SESSION_SECRET: "short" }),
    ).rejects.toThrow("SESSION_SECRET");
  });
});
