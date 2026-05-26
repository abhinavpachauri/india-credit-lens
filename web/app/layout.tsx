import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const SITE_URL = "https://indiacreditlens.com";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),

  title: {
    default: "India Credit Lens — RBI Bank Credit Dashboard",
    template: "%s | India Credit Lens",
  },

  description:
    "Track ₹204L Cr in India bank credit across sectors. Monthly dashboard from RBI data — personal loans, MSME, services, agriculture, priority sector — with analysis for lending professionals and fintech strategy teams.",

  keywords: [
    "India bank credit dashboard",
    "RBI sector wise bank credit",
    "India credit growth trends",
    "RBI SIBC data",
    "MSME lending India",
    "personal loans India analytics",
    "priority sector lending",
    "India lending analytics",
    "bank credit data India",
    "fintech credit intelligence India",
    "India credit lens",
  ],

  authors: [{ name: "India Credit Lens", url: SITE_URL }],
  creator: "India Credit Lens",

  openGraph: {
    type:        "website",
    locale:      "en_IN",
    url:         SITE_URL,
    siteName:    "India Credit Lens",
    title:       "India Credit Lens — RBI Bank Credit Dashboard",
    description: "Track ₹204L Cr in India bank credit across sectors. Monthly dashboard from RBI data with analysis for lending professionals.",
    images: [
      {
        url:    "/opengraph-image",
        width:  1200,
        height: 630,
        alt:    "India Credit Lens — RBI Bank Credit Dashboard",
      },
    ],
  },

  twitter: {
    card:        "summary_large_image",
    title:       "India Credit Lens — RBI Bank Credit Dashboard",
    description: "Track ₹204L Cr in India bank credit across sectors. Monthly dashboard from RBI data with analysis for lending professionals.",
    images:      ["/opengraph-image"],
  },

  robots: {
    index:  true,
    follow: true,
    googleBot: {
      index:               true,
      follow:              true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet":       -1,
    },
  },

  alternates: {
    canonical: SITE_URL,
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": `${SITE_URL}/#website`,
      url:   SITE_URL,
      name:  "India Credit Lens",
      description:
        "Strategic credit intelligence from India's public lending data. Monthly dashboard covering RBI sector-wise bank credit.",
      publisher: { "@id": `${SITE_URL}/#organisation` },
    },
    {
      "@type": "Organization",
      "@id":   `${SITE_URL}/#organisation`,
      name:    "India Credit Lens",
      url:     SITE_URL,
    },
    {
      "@type":       "Dataset",
      "@id":         `${SITE_URL}/#dataset`,
      name:          "RBI Sector/Industry-wise Bank Credit — India Credit Lens",
      description:
        "Monthly outstanding bank credit by sector, industry size, services sub-sector, personal loan category, and priority sector — sourced from RBI SIBC returns.",
      url:           SITE_URL,
      creator:       { "@id": `${SITE_URL}/#organisation` },
      publisher:     { "@type": "Organization", name: "Reserve Bank of India", url: "https://rbi.org.in" },
      license:       "https://rbi.org.in/Scripts/Statistics.aspx",
      temporalCoverage: "2024/2026",
      spatialCoverage: "IN",
      variableMeasured: [
        "Outstanding bank credit by sector",
        "YoY credit growth by sector",
        "Priority sector lending",
        "MSME credit outstanding",
      ],
    },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className="min-h-full flex flex-col">
        {children}
        <Analytics />
      </body>
    </html>
  );
}
