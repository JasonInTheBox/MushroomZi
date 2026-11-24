import Link from "next/link";
import { notFound } from "next/navigation";
import { getAllPassages } from "@/lib/content";

const languages = ["en", "zh"] as const;

export const dynamicParams = false; 

export function generateStaticParams() {
    return getAllPassages().flatMap(({ id }) => 
        languages.map((lang) => ({ lang, id })),
    );
}

export default async function PassagePage({
    params,
}: {
    params: Promise<{ lang: string; id: string }>;
}) {
    const { lang, id } = await params;

    if (lang !== "en" && lang !== "zh") {
        notFound();
    }

    const passage = getAllPassages().find((item) => item.id === id);

    if (!passage) {
        notFound();
    }

    const englishTranslation = passage.translations.find(
        (translation) => translation.language === "en",
    );

    const labels = 
        lang === "en"
            ? {
                original: "Original text",
                translation: "English translation",
                simplified: "Simplified form",
            }
            : {
                original: "原文",
                translation: "英文翻譯",
                simplified: "簡體字",
            };

    const otherLanguage = lang === "en" ? "zh" : "en";

    return (
        <main className="mx-auto max-w-3xl px-6 py-10">
            <nav className="mb-12 flex justify-between">
                <Link href="/">Mushroom Zi 蘑菇子</Link>
                <Link href={`/${otherLanguage}/passage/${passage.id}`}>
                    {lang === "en" ? "中文" : "English"}
                </Link>
            </nav>

            <article>
                <p className="mb-3 text-sm">
                    {lang === "en" ? "Book" : "第"} {passage.book.number}
                    {" · "}
                    {lang === "en" ? "Passage" : "章句"} {passage.number}
                </p>
            

            <h1 className="mb-10 text-3xl font-semibold">
                {passage.book.title.chinese}
                {passage.book.title.english
                    ? ` — ${passage.book.title.english}`
                    : ""}
            </h1>

            <section className="mb-8">
                <h2 className="mb-3 text-lg font-medium">{labels.original}</h2>
                <p lang="zh-Hant" className="text-2xl leading-loose">
                    {passage.original.text}
                </p>
                </section>

                {lang === "zh" && passage.original.variants?.simplified && (
                <section className="mb-8">
                    <h2 className="mb-3 text-lg font-medium">
                    {labels.simplified}
                    </h2>
                    <p lang="zh-Hans" className="text-2xl leading-loose">
                    {passage.original.variants.simplified}
                    </p>
                </section>
                )}

                {lang === "en" && englishTranslation && (
                <section className="mb-8">
                    <h2 className="mb-3 text-lg font-medium">
                    {labels.translation}
                    </h2>
                    <p lang="en" className="text-lg leading-relaxed">
                    {englishTranslation.text}
                    </p>
                    <p className="mt-3 text-sm">
                    {englishTranslation.translator}
                    </p>
                </section>
                )}

                <footer className="mt-12 border-t pt-4 text-sm">
                <p>
                    {lang === "en" ? "Source" : "來源"}:{" "}
                    {passage.original.source.citation}
                </p>
                {passage.original.source.url && (
                    <a
                    className="underline"
                    href={passage.original.source.url}
                    target="_blank"
                    rel="noreferrer"
                    >
                    {passage.original.source.title}
                    </a>
                )}
                </footer>
            </article>
        </main>
    )
}
