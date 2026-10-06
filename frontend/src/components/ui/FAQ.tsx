const FAQS = [
  {
    q: 'What exactly does CAFS check?',
    a: 'Three things. A forensic scan looks for areas of the image that were edited after it was created. We then read the holder’s name, certificate ID and issuer. Finally we open the issuer’s own verification page and confirm the ID and name match.',
  },
  {
    q: 'Why would a genuine certificate come back “Unverified”?',
    a: 'Usually because the issuer page is private, the certificate ID wasn’t readable, or the issuer isn’t one we can check automatically yet. You can then enter the ID and verification link by hand. That confirms the ID exists, but not that it belongs to the name on the document.',
  },
  {
    q: 'What does “Flagged” mean?',
    a: 'The forensic scan found signs the file was digitally altered. A flagged document can’t be verified. If you believe it’s genuine, download a fresh copy from the issuer and try again.',
  },
  {
    q: 'Do you store my certificate?',
    a: 'The uploaded file is processed in memory and never kept. If you are signed in, the result (holder name, certificate ID, issuer and verdict) is saved to your history so you can find it again, and you can delete any entry from your profile. Screenshots of the issuer page, taken as proof, are deleted automatically after 24 hours.',
  },
  {
    q: 'How can someone check a report I shared?',
    a: 'Every verified result comes with a signed link and QR code. Opening it asks our server to confirm the signature, so an edited or made-up link shows as invalid.',
  },
];

export default function FAQ() {
  return (
    <section id="faq" className="border-t border-navy-100 bg-white/60 py-20 sm:py-28">
      <div className="mx-auto grid max-w-7xl gap-12 px-4 sm:px-6 lg:grid-cols-[0.8fr_1.2fr] lg:px-8">
        <div>
          <p className="eyebrow">FAQ</p>
          <h2 className="mt-3 font-display text-4xl font-semibold tracking-tight text-navy-900">
            Questions, answered plainly.
          </h2>
        </div>
        <div className="divide-y divide-navy-100 border-y border-navy-100">
          {FAQS.map(({ q, a }) => (
            <details key={q} className="group py-5">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-left text-lg font-medium text-navy-900 [&::-webkit-details-marker]:hidden">
                {q}
                <span className="font-display text-2xl text-navy-400 transition-transform group-open:rotate-45" aria-hidden>
                  +
                </span>
              </summary>
              <p className="mt-3 leading-relaxed text-navy-600">{a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
