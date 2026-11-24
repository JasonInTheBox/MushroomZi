import type { Metadata } from "next";
import { fontClassNames } from "../fonts";
import "../globals.css";

export const metadata: Metadata = {
  title: "Mushroom Zi 蘑菇子",
  description: "Read the Analects in English and Chinese.",
};

export default function HomeLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${fontClassNames} h-full antialiased`}>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
