import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "x402 — AIが自律的に、収益を動かす時代へ",
  description:
    "人が介在しない圧倒的な効率で、AIエージェントがデータ分析・意思決定・実行までを自律的に完結。ビジネスの収益創出を、次のステージへ。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
