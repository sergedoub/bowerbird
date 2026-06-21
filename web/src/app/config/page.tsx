import { redirect } from "next/navigation";
import { currentSession } from "@/lib/session";
import ConfigEditor from "./editor";

export const dynamic = "force-dynamic";

export default async function ConfigPage() {
  const session = await currentSession().catch(() => null);
  if (!session) redirect("/api/auth/login");
  return (
    <>
      <h1>Configuration</h1>
      <p className="meta">
        Saving commits <code>config/topics.toml</code> and{" "}
        <code>config/accounts.toml</code> to your repo.
      </p>
      <ConfigEditor />
    </>
  );
}
