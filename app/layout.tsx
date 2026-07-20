import type { Metadata } from "next";
import { UserProvider } from "@/context/UserContext";
import "./globals.css";

export const metadata: Metadata = {
  title: "RoleCraft",
  description: "The Future of Smarter Career Fit",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <UserProvider>
          {children}
        </UserProvider>
      </body>
    </html>
  );
}
