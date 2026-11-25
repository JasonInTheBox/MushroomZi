import Link from "next/link";
import { getAllPassages } from "@/lib/content";
import DailyPassage from "@/components/daily-passage";

// The static first render uses this timestamp; the client refreshes it on mount.
const buildTimestamp = Date.now();

export default function HomePage() {
  const passages = getAllPassages();
  const passagesByBook = new Map<number, typeof passages>();
  const dailyPassages = passages.flatMap((passage) => {
    const translation = passage.translations.find((item) => item.language === "en");
    const explanation = {
      en: passage.commentary.find((item) => item.kind === "project_explanation" && item.language === "en")?.text,
      zhHant: passage.commentary.find((item) => item.kind === "project_explanation" && item.language === "zh-Hant")?.text,
    };
    const application = {
      en: passage.commentary.find((item) => item.kind === "modern_application" && item.language === "en")?.text,
      zhHant: passage.commentary.find((item) => item.kind === "modern_application" && item.language === "zh-Hant")?.text,
    };

    if (!translation || !explanation.en || !explanation.zhHant || !application.en || !application.zhHant) {
      return [];
    }

    return [{
      id: passage.id,
      bookNumber: passage.book.number,
      passageNumber: passage.number,
      originalText: passage.original.text,
      originalSource: passage.original.source,
      translation,
      commentary: {
        explanation: { en: explanation.en, zhHant: explanation.zhHant },
        application: { en: application.en, zhHant: application.zhHant },
      },
    }];
  });

  for (const passage of passages) {
    const bookPassages = passagesByBook.get(passage.book.number) ?? [];
    bookPassages.push(passage);
    passagesByBook.set(passage.book.number, bookPassages);
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="mb-3 text-3xl font-semibold">
        Mushroom Zi <span lang="zh-Hant">蘑菇子</span>
      </h1>
      <p className="mb-10">
        Read the Analects <span aria-hidden="true">·</span>{" "}
        <span lang="zh-Hant">閱讀《論語》</span>
      </p>

      <DailyPassage passages={dailyPassages} initialTimestamp={buildTimestamp} />

      <div className="space-y-8">
        {Array.from(passagesByBook.values(), (bookPassages) => {
          const book = bookPassages[0].book;

          return (
            <section key={book.number}>
              <h2 className="mb-3 text-xl font-medium">
                Book {book.number} <span lang="zh-Hant">· {book.title.chinese}</span>
              </h2>
              <ol className="space-y-3">
                {bookPassages.map((passage) => (
                  <li key={passage.id} className="flex justify-between gap-4">
                    <span>Passage {passage.number}</span>
                    <span className="flex gap-4">
                      {passage.translations.some((translation) => translation.language === "en") && (
                        <Link
                          href={`/en/passage/${passage.id}`}
                          aria-label={`Read Book ${book.number}, passage ${passage.number} in English`}
                        >
                          English
                        </Link>
                      )}
                      <Link
                        href={`/zh/passage/${passage.id}`}
                        lang="zh-Hant"
                        aria-label={`閱讀第 ${book.number} 篇，第 ${passage.number} 章句（中文）`}
                      >
                        中文
                      </Link>
                    </span>
                  </li>
                ))}
              </ol>
            </section>
          );
        })}
      </div>
    </main>
  );
}
