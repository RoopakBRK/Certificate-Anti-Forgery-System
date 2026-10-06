import { ExternalLink } from 'lucide-react';
import Navbar from '@/components/ui/Navbar';
import Footer from '@/components/ui/Footer';
import { createClient } from '@supabase/supabase-js';
import { safeHttpUrl } from '@/lib/utils';
import type { Issuer } from '@/types';

export const metadata = {
  title: 'Supported issuers - CAFS',
  description: 'Certificate issuers CAFS can verify, with their official verification links and ID formats.',
};
export const revalidate = 3600;

const CATEGORY_ORDER = ['Online Learning Platform', 'Credential Platform', 'Company / Tech Provider', 'Gov / Non-Profit'];

export default async function IssuersPage() {
  // Public catalogue: a cookie-less client keeps this page statically cached (revalidated hourly)
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  const supabase = url && key ? createClient(url, key, { auth: { persistSession: false } }) : null;
  const { data, error } = supabase
    ? await supabase
        .from('issuers')
        .select('id, name, category, aliases, website_url, verification_url, url_patterns, id_example, verification_type, notes')
        .order('verification_type')
        .order('name')
    : { data: null, error: new Error('not configured') };
  const issuers = (data as Issuer[] | null) ?? [];
  const direct = issuers.filter((i) => i.verification_type === 'direct').length;

  const groups = CATEGORY_ORDER.map((cat) => ({ cat, items: issuers.filter((i) => i.category === cat) })).filter((g) => g.items.length);

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 pb-24 pt-28 sm:px-6 lg:px-8">
        <p className="eyebrow">Supported issuers</p>
        <h1 className="mt-3 max-w-3xl font-display text-4xl font-semibold tracking-tight text-navy-900 sm:text-5xl">
          Where every certificate is checked
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-navy-600">
          CAFS only trusts each issuer&apos;s own verification pages. <strong>{direct}</strong> issuers are confirmed
          automatically from the certificate ID; for the rest we link you to the issuer&apos;s official lookup.
        </p>

        {error && issuers.length === 0 && (
          <p className="mt-10 rounded-lg border border-warn-200 bg-warn-50 p-4 text-sm text-warn-800">
            The issuer directory is unavailable right now.
          </p>
        )}

        {groups.map(({ cat, items }) => (
          <section key={cat} className="mt-14">
            <h2 className="font-display text-2xl font-semibold text-navy-900">{cat}</h2>
            <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {items.map((issuer) => {
                const link = safeHttpUrl(issuer.verification_url);
                const isDirect = issuer.verification_type === 'direct';
                return (
                  <article key={issuer.id} className="card flex flex-col p-5">
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="font-display text-lg font-semibold text-navy-900">{issuer.name}</h3>
                      <span
                        className={`shrink-0 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${
                          isDirect ? 'border-verified-200 bg-verified-50 text-verified-700' : 'border-navy-200 bg-navy-50 text-navy-600'
                        }`}
                      >
                        {isDirect ? 'Automatic' : 'Manual lookup'}
                      </span>
                    </div>
                    {issuer.aliases.length > 0 && (
                      <p className="mt-1 text-xs text-navy-500">Also: {issuer.aliases.join(', ')}</p>
                    )}
                    {isDirect && issuer.url_patterns[0] && (
                      <p className="mt-3 break-all rounded-md bg-navy-50 px-2.5 py-1.5 font-mono text-xs text-navy-700">
                        {issuer.url_patterns[0].replace('{id}', issuer.id_example || '<certificate-id>')}
                      </p>
                    )}
                    {issuer.notes && <p className="mt-3 text-sm text-navy-600">{issuer.notes}</p>}
                    <div className="mt-auto pt-4">
                      {link ? (
                        <a
                          href={link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-sm font-medium text-navy-800 underline underline-offset-4 hover:text-navy-950"
                        >
                          Official verification page <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                        </a>
                      ) : (
                        <span className="text-sm text-navy-400">No public verification page</span>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        ))}
      </main>
      <Footer />
    </>
  );
}
