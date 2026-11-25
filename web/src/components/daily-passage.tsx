"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getDailyPassageIndex } from "@/lib/daily-passage.mjs";

type DailyPassageContent = {
    id: string;
    bookNumber: number;
    passageNumber: number;
    originalText: string;
    originalSource: { title: string; citation: string; url?: string };
    translation: {
        text: string;
        translator: string;
        source: { title: string; citation: string; url?: string };
    };
    commentary: {
        explanation: { en: string; zhHant: string };
        application: { en: string; zhHant: string };
    };
};

export default function DailyPassage({
    passages,
    initialTimestamp,
}: {
    passages: DailyPassageContent[];
    initialTimestamp: number;
}) {
    const [timestamp, setTimestamp] = useState(initialTimestamp);

    useEffect(() => {
        let timeout: ReturnType<typeof setTimeout>;
        const refreshAtUtcMidnight = () => {
            const now = Date.now();
            const date = new Date(now);
            const nextMidnight = Date.UTC(
                date.getUTCFullYear(),
                date.getUTCMonth(),
                date.getUTCDate() + 1,
            );

            setTimestamp(now);
            timeout = setTimeout(refreshAtUtcMidnight, nextMidnight - now);
        };

        refreshAtUtcMidnight();
        return () => clearTimeout(timeout);
    }, []);

    const index = getDailyPassageIndex(timestamp, passages.length);
    const passage = index < 0 ? undefined : passages[index];
    const utcDate = new Date(timestamp).toISOString().slice(0, 10);

    return (
        <section aria-labelledby="daily-passage-title" className="mb-12 border-y py-8">
            <h2 id="daily-passage-title" className="mb-2 text-2xl font-semibold">
                Daily passage <span lang="zh-Hant">· 每日章句</span>
            </h2>
            <p className="mb-6 text-sm" aria-live="polite" aria-atomic="true">
                UTC date: {utcDate} <span lang="zh-Hant">· UTC 日期</span>
            </p>

            {!passage ? (
                <p>No daily passage is available yet. <span lang="zh-Hant">目前尚無每日章句。</span></p>
            ) : (
                <article>
                    <p className="mb-5 text-sm">
                        Book {passage.bookNumber}, passage {passage.passageNumber}
                        <span lang="zh-Hant"> · 第 {passage.bookNumber} 篇，第 {passage.passageNumber} 章句</span>
                    </p>

                    <section className="mb-6">
                        <h3 className="mb-2 font-medium">Original text <span lang="zh-Hant">· 原文</span></h3>
                        <p lang="zh-Hant" className="text-xl leading-loose">{passage.originalText}</p>
                        <p className="mt-2 text-sm">
                            {passage.originalSource.url ? (
                                <a className="underline" href={passage.originalSource.url} target="_blank" rel="noreferrer">
                                    {passage.originalSource.title}, {passage.originalSource.citation}
                                </a>
                            ) : (
                                `${passage.originalSource.title}, ${passage.originalSource.citation}`
                            )}
                        </p>
                    </section>

                    <section className="mb-6">
                        <h3 className="mb-2 font-medium">English translation <span lang="zh-Hant">· 英文翻譯</span></h3>
                        <p lang="en" className="leading-relaxed">{passage.translation.text}</p>
                        <p className="mt-2 text-sm">
                            {passage.translation.translator} ·{" "}
                            {passage.translation.source.url ? (
                                <a className="underline" href={passage.translation.source.url} target="_blank" rel="noreferrer">
                                    {passage.translation.source.title}, {passage.translation.source.citation}
                                </a>
                            ) : (
                                `${passage.translation.source.title}, ${passage.translation.source.citation}`
                            )}
                        </p>
                    </section>

                    <section className="space-y-5 border-t pt-5">
                        <h3 className="font-medium">
                            AI-generated commentary <span lang="zh-Hant">· AI 生成評論</span>
                        </h3>
                        <p className="text-sm">
                            Generated project commentary, not a scholarly interpretation.
                            <span lang="zh-Hant">本站生成的評論，並非學術詮釋。</span>
                        </p>
                        <div>
                            <h4 className="mb-2 font-medium">Explanation · 解說 <span className="text-sm">(AI-generated · AI 生成)</span></h4>
                            <p lang="en" className="mb-2 leading-relaxed">{passage.commentary.explanation.en}</p>
                            <p lang="zh-Hant" className="leading-relaxed">{passage.commentary.explanation.zhHant}</p>
                        </div>
                        <div>
                            <h4 className="mb-2 font-medium">Modern application · 現代應用 <span className="text-sm">(AI-generated · AI 生成)</span></h4>
                            <p lang="en" className="mb-2 leading-relaxed">{passage.commentary.application.en}</p>
                            <p lang="zh-Hant" className="leading-relaxed">{passage.commentary.application.zhHant}</p>
                        </div>
                    </section>

                    <nav aria-label="Read this passage" className="mt-6 flex gap-5 border-t pt-4">
                        <Link className="underline" href={`/en/passage/${passage.id}`}>Read in English</Link>
                        <Link className="underline" href={`/zh/passage/${passage.id}`} lang="zh-Hant">閱讀中文版本</Link>
                    </nav>
                </article>
            )}
        </section>
    );
}
