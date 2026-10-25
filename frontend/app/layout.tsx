export const metadata = { title: "Panna — Match Intelligence" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, -apple-system, sans-serif", background: "#0b0f14", color: "#e6edf3" }}>
        {children}
      </body>
    </html>
  );
}
