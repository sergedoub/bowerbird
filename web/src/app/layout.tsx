import type { Metadata } from "next";
import Link from "next/link";
import { currentSession } from "@/lib/session";
import "./globals.css";

export const metadata: Metadata = {
  title: "Bowerbird",
  description: "Manage and consume your X-bookmark knowledge base.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  let session = null;
  try {
    session = await currentSession();
  } catch {
    // SESSION_SECRET unset — the app still serves the read-only recap preview.
  }
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <Link href="/" className="brand">
            bowerbird
          </Link>
          <nav>
            <Link href="/recap">Recap</Link>
            <Link href="/config">Config</Link>
            <Link href="/folders">Folders</Link>
            <Link href="/health">Health</Link>
          </nav>
          <div className="auth">
            {session ? (
              <form action="/api/auth/logout" method="post">
                <span className="meta">@{session.username}</span>{" "}
                <button type="submit">Sign out</button>
              </form>
            ) : (
              <a href="/api/auth/login">Sign in with X</a>
            )}
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
