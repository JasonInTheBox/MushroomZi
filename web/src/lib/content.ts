import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";

type Source = {
    title: string;
    citation: string;
    url?: string;
}

type PassageData = {
  id: string;
  number: number;
  original: {
    text: string;
    source: Source;
    variants?: {
      simplified?: string;
      pinyin?: string;
    };
  };
  translations: Array<{
    language: "en" | "zh-Hans" | "zh-Hant";
    text: string;
    translator: string;
    source: Source;
    rights: {
      reuseStatus: "unverified" | "public_domain" | "licensed" | "permission_required";
      license?: string | null;
    };
  }>;
};

type BookInfo = {
  number: number;
  title: {
    chinese: string;
    pinyin?: string;
    english?: string;
  };
};

type BookFile = {
  book: BookInfo;
  passages: PassageData[];
};

export type ReaderPassage = PassageData & {
  book: BookInfo;
};

// Production builds publish only translations whose reuse rights are cleared;
// `next dev` shows drafts so unverified text can still be reviewed locally.
function isPublishable(translation: PassageData["translations"][number]) {
    const { reuseStatus } = translation.rights;
    return (
        process.env.NODE_ENV !== "production" ||
        reuseStatus === "public_domain" ||
        reuseStatus === "licensed"
    );
}

export function getAllPassages(): ReaderPassage[] {
    const booksDirectory = path.resolve(
        process.cwd(),
        "..",
        "content",
        "books",
    );

    const filenames = readdirSync(booksDirectory)
        .filter((filename) => /^book-\d{2}\.json$/.test(filename))
        .sort();

    return filenames.flatMap((filename) => {
        const filePath = path.join(booksDirectory, filename);
        const bookFile = JSON.parse(
            readFileSync(filePath, "utf8"),
        ) as BookFile;

        return bookFile.passages.map((passage) => ({
            ...passage,
            translations: passage.translations.filter(isPublishable),
            book: bookFile.book,
        }));
    });
}
