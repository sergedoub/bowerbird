import { redirect } from "next/navigation";
import { currentSession } from "@/lib/session";
import FolderBrowser from "./browser";

export const dynamic = "force-dynamic";

export default async function FoldersPage() {
  const session = await currentSession().catch(() => null);
  if (!session) redirect("/api/auth/login");
  return (
    <>
      <h1>Bookmark folders</h1>
      <p className="meta">
        Your folders on X, by name. Assign each to a wiki topic; saving commits{" "}
        <code>config/topics.toml</code>.
      </p>
      <FolderBrowser />
    </>
  );
}
