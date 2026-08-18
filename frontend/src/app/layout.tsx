import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ClerkClientProvider } from "@/components/clerk-provider";
import { Providers } from "@/components/providers";
import { SentryInit } from "@/components/sentry-init";
import { ServiceWorkerRegister } from "@/components/service-worker-register";
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
  title: "PSX Intelligence Platform",
  description: "Pakistan Stock Exchange market data dashboard",
  manifest: "/manifest.json",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <ClerkClientProvider>
          <SentryInit />
          <ServiceWorkerRegister />
          <Providers>{children}</Providers>
        </ClerkClientProvider>
      </body>
    </html>
  );
}
