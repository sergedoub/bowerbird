// Actions-secret sealing: GitHub requires secret values encrypted with the repo's
// public key using libsodium's sealed box before upload.

import sodium from "libsodium-wrappers";
import type { RepoClient } from "./repoClient";

export async function sealForGitHub(publicKeyB64: string, value: string): Promise<string> {
  await sodium.ready;
  const sealed = sodium.crypto_box_seal(
    sodium.from_string(value),
    sodium.from_base64(publicKeyB64, sodium.base64_variants.ORIGINAL),
  );
  return sodium.to_base64(sealed, sodium.base64_variants.ORIGINAL);
}

/** Seal and store one Actions secret on the instance repo. */
export async function setActionsSecret(
  repo: RepoClient,
  name: string,
  value: string,
  seal: typeof sealForGitHub = sealForGitHub,
): Promise<void> {
  const { key, key_id } = await repo.getSecretsPublicKey();
  const sealed = await seal(key, value);
  await repo.putSealedSecret(name, sealed, key_id);
}
