import type { Metadata } from "next";
import { fontClassNames } from "../fonts";
import "../globals.css";

export const metadata: Metadata = {
  title: "Mushroom Zi 蘑菇子",
  description: "Read the Analects in English and Chinese.",
};

// Root layout for /en/... and /zh/... so <html lang> matches the page language.
export default async function LangLayout({
  children,
  params,
}: LayoutProps<"/[lang]">) {
  const { lang } = await params;

  return (
    <html
      lang={lang === "zh" ? "zh-Hant" : "en"}
      className={`${fontClassNames} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
