import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "News NAS",
  description: "Personal news intelligence platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <header className="topbar">
            <Link href="/" className="brand">
              <span className="brand-mark">Helix</span>
              <span className="brand-subtitle">NAS cockpit</span>
            </Link>

            <nav className="nav-links" aria-label="Primary">
              <Link href="/">Home</Link>
              <Link href="/articles">Articles</Link>
              <Link href="/clusters">Clusters</Link>
              <Link href="/briefings">Briefings</Link>
              <Link href="/inbox">Inbox</Link>
              <Link href="/watchlist">Watchlist</Link>
              <Link href="/projects">Projects</Link>
              <Link href="/sources">Sources</Link>
              <Link href="/operations">Operations</Link>
              <Link href="/search">Search</Link>
              <Link href="/jarvis">Jarvis</Link>
            </nav>
          </header>

          <main className="shell-main">{children}</main>
        </div>
      </body>
    </html>
  );
}
