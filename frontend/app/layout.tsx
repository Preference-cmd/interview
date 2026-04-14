import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Multi-Agent Ops",
  description: "SaaS Dashboard for Agent Operations",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="font-anthropic-sans bg-parchment text-anthropic-near-black antialiased leading-relaxed min-h-screen flex flex-col">
        {children}
      </body>
    </html>
  );
}
