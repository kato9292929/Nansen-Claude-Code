import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Apex — Accelerate Your Revenue Growth",
  description:
    "Drive your funnel forward with clever workflows, analytics, and seamless lead management.",
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
