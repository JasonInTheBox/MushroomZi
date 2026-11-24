import Link from "next/link";
import { getAllPassages } from "@/lib/content";

export default function HomePage() {
  const passages = getAllPassages();

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="mb-3 text-3xl font-semibold">
        Mushroom Zi 蘑菇子
      </h1>
      <p className="mb-10">
        Read the Analects · 閱讀《論語》
      </p>

      <ul className="space-y-4">
        {passages.map((passage) => (
          <li key={passage.id} className="flex justify-between gap-4">
            <Link href={`/en/passage/${passage.id}`}>
              Book {passage.book.number}, passage {passage.number}
            </Link>
            <Link href={`/zh/passage/${passage.id}`}>
              中文
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
