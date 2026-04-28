import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '源灵AI',
  description: '本地优先、透明可控的 AI Agent 系统',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
