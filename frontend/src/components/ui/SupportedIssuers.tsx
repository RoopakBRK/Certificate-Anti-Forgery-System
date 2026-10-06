import Link from 'next/link';

// Most-used issuers the backend confirms automatically (full list: /issuers, from backend/data/onlinelist.csv)
const ISSUERS = ['Coursera', 'Udemy', 'edX', 'LinkedIn Learning', 'NPTEL', 'Credly', 'Great Learning', 'Udacity', 'DataCamp'];

export default function SupportedIssuers() {
  return (
    <section aria-label="Supported issuers" className="border-y border-navy-100 bg-white/60">
      <div className="mx-auto flex max-w-7xl flex-col items-center gap-4 px-4 py-7 sm:px-6 md:flex-row md:justify-between lg:px-8">
        <p className="eyebrow shrink-0">Checks certificates from</p>
        <ul className="flex flex-wrap items-center justify-center gap-x-7 gap-y-3 md:justify-end">
          {ISSUERS.map((name) => (
            <li key={name} className="font-display text-lg font-medium text-navy-400">
              {name}
            </li>
          ))}
          <li>
            <Link href="/issuers" className="text-sm font-semibold text-navy-700 underline underline-offset-4 hover:text-navy-900">
              See all 72
            </Link>
          </li>
        </ul>
      </div>
    </section>
  );
}
