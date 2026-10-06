import type { Metadata } from "next";
import { Inter, Source_Serif_4 } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const sourceSerif = Source_Serif_4({ subsets: ["latin"], variable: "--font-display", axes: ["opsz"] });

export const metadata: Metadata = {
  title: "CAFS - Certificate Anti Forgery System",
  description:
    "Detect forged certificates in seconds. CAFS checks the document for tampering, reads its details and confirms them on the issuer's own site.",
  openGraph: {
    title: "CAFS - Certificate Anti Forgery System",
    description: "Detect forged certificates in seconds, confirmed against the issuer's own records.",
    siteName: "CAFS",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${sourceSerif.variable}`}>
      <body className="font-sans">{children}</body>
    </html>
  );
}
