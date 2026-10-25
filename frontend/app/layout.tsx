import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Panna — Match Intelligence That Explains Itself",
  description:
    "AI-driven match intelligence for the Microsoft Premier League Inside the Game hackathon. Synthetic football, explainable by design.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
