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

    const passages = getAllPassages();
    const passageIndex = passages.findIndex((item) => item.id === id);
    const passage = passages[passageIndex];

    if (!passage) {
        notFound();
    }

    const previousPassage = passages[passageIndex - 1];
    const nextPassage = passages[passageIndex + 1];

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
                <nav
                    aria-label={lang === "en" ? "Passage navigation" : "章句導覽"}
                    className="mt-12 flex justify-between gap-4 border-t pt-4"
                >
                    {previousPassage && (
                        <Link
                            href={`/${lang}/passage/${previousPassage.id}`}
                            rel="prev"
                            className="underline focus-visible:outline-2 focus-visible:outline-offset-4"
                        >
                            {lang === "en"
                                ? `← Previous · Book ${previousPassage.book.number}, passage ${previousPassage.number}`
                                : `← 前一章句 · 第 ${previousPassage.book.number} 篇，第 ${previousPassage.number} 章句`}
                        </Link>
                    )}
                    {nextPassage && (
                        <Link
                            href={`/${lang}/passage/${nextPassage.id}`}
                            rel="next"
                            className="ml-auto underline focus-visible:outline-2 focus-visible:outline-offset-4"
                        >
                            {lang === "en"
                                ? `Next · Book ${nextPassage.book.number}, passage ${nextPassage.number} →`
                                : `下一章句 · 第 ${nextPassage.book.number} 篇，第 ${nextPassage.number} 章句 →`}
                        </Link>
                    )}
                </nav>
            </article>
        </main>
    )
}
