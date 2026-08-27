import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Sidebar from "./components/Sidebar";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Anchor",
  description: "Turn source material into notes, flashcards, and grounded Q&A.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full">
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="min-w-0 flex-1 overflow-y-auto">
            <div className="mx-auto w-full max-w-3xl px-6 py-10 sm:px-10">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
