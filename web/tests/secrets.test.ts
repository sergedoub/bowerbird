// Actions-secret seeding: real libsodium sealing (verified by unsealing with the
// matching keypair) and the RepoClient wiring.
import sodium from "libsodium-wrappers";
import { describe, expect, it } from "vitest";
import { sealForGitHub, setActionsSecret } from "@/lib/secrets";
import type { RepoClient } from "@/lib/repoClient";

describe("sealForGitHub", () => {
  it("produces a sealed box the repo private key can open", async () => {
    await sodium.ready;
    const pair = sodium.crypto_box_keypair();
    const pubB64 = sodium.to_base64(pair.publicKey, sodium.base64_variants.ORIGINAL);

    const sealed = await sealForGitHub(pubB64, '{"access_token":"at"}');

    const opened = sodium.crypto_box_seal_open(
      sodium.from_base64(sealed, sodium.base64_variants.ORIGINAL),
      pair.publicKey,
      pair.privateKey,
    );
    expect(sodium.to_string(opened)).toBe('{"access_token":"at"}');
  });
});

describe("setActionsSecret", () => {
  it("fetches the public key, seals, and PUTs under the secret name", async () => {
    const calls: any[] = [];
    const fakeRepo = {
      getSecretsPublicKey: async () => ({ key_id: "k1", key: "PUBKEY" }),
      putSealedSecret: async (name: string, sealed: string, keyId: string) => {
        calls.push({ name, sealed, keyId });
      },
    } as unknown as RepoClient;

    await setActionsSecret(fakeRepo, "X_TOKENS", "value", async (key, v) => {
      expect(key).toBe("PUBKEY");
      return `sealed(${v})`;
    });
    expect(calls).toEqual([{ name: "X_TOKENS", sealed: "sealed(value)", keyId: "k1" }]);
  });
});
