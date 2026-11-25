import Link from "next/link";
import { getAllPassages } from "@/lib/content";

export default function HomePage() {
  const passages = getAllPassages();
  const passagesByBook = new Map<number, typeof passages>();

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
                      <Link
                        href={`/en/passage/${passage.id}`}
                        aria-label={`Read Book ${book.number}, passage ${passage.number} in English`}
                      >
                        English
                      </Link>
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
