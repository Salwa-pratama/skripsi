import type { Metadata, Viewport } from "next";
import "./globals.css";
import "@/content/generated/pygments.css";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { ProgressProvider } from "@/lib/progress";
import { curriculum } from "@/lib/curriculum";

const themeScript = `(function(){try{var k='pyjourney.theme';var t=localStorage.getItem(k);if(t!=='light'&&t!=='dark'){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}document.documentElement.dataset.theme=t;}catch(e){document.documentElement.dataset.theme='light';}})();`;

export const metadata: Metadata = {
  title: {
    default: "PyJourney — Belajar Python 3 dari dokumentasi resmi",
    template: "%s · PyJourney",
  },
  description: curriculum.description,
  applicationName: "PyJourney",
  authors: [{ name: "PyJourney" }],
  creator: "PyJourney",
  category: "education",
  keywords: [
    "belajar python",
    "python 3",
    "dokumentasi python resmi",
    "tutorial python indonesia",
    "OOP python",
    "list dictionary python",
    "Sphinx JSON Builder",
    "objects.inv",
  ],
  openGraph: {
    title: "PyJourney — Belajar Python 3 dari dokumentasi resmi",
    description: curriculum.description,
    type: "website",
    locale: "id_ID",
    siteName: "PyJourney",
  },
  twitter: {
    card: "summary_large_image",
    title: "PyJourney — Belajar Python 3 dari dokumentasi resmi",
    description: curriculum.description,
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f3ea" },
    { media: "(prefers-color-scheme: dark)", color: "#10120f" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <ProgressProvider>
          <a className="skip-link" href="#konten">
            Lewati ke konten
          </a>
          <SiteHeader />
          <main id="konten">{children}</main>
          <SiteFooter />
        </ProgressProvider>
      </body>
    </html>
  );
}
