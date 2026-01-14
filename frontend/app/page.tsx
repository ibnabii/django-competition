import MaxWidthWrapper from "@/components/MaxWidthWrapper";
import Link from "next/link";

export default function Home() {
  // fetch from api
  const competitions = [1, 2, 3, 4, 5, 6, 7];
  return (
    <MaxWidthWrapper className="py-12">
      <div className="grid grid-cols-1 place-content-center gap-4 md:grid-cols-2 lg:grid-cols-3">
        {competitions.map((c) => (
          <Link href={`/competition/${c}`} key={c}>
            <div className="flex h-[200px] items-center justify-center bg-accent">
              competition: {c}
            </div>
          </Link>
        ))}
      </div>
    </MaxWidthWrapper>
  );
}
