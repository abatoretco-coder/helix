import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "News NAS",
  description: "Personal news intelligence platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
