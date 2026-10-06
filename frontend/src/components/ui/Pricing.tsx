import { Check } from 'lucide-react';

// Paid plans are not wired to payments yet; their buttons open a waitlist email.
const WAITLIST = 'mailto:roopak2804@gmail.com?subject=CAFS%20waitlist%20';

interface Plan {
  name: string;
  audience: string;
  price: string;
  period?: string;
  blurb: string;
  features: string[];
  cta: { label: string; href: string };
  featured?: boolean;
}

const PLANS: Plan[] = [
  {
    name: 'Free',
    audience: 'Learners',
    price: '₹0',
    blurb: 'Prove your own certificates are genuine.',
    features: ['5 verifications a month', 'Signed, shareable report link', 'QR code for your resume'],
    cta: { label: 'Verify now', href: '#verify' },
  },
  {
    name: 'Learner Pro',
    audience: 'Learners',
    price: '₹99',
    period: '/month',
    blurb: 'A verified profile recruiters can trust.',
    features: ['Unlimited own-certificate checks', 'Public verified profile page', 'PDF reports, no CAFS branding'],
    cta: { label: 'Join waitlist', href: `${WAITLIST}(Learner%20Pro)` },
  },
  {
    name: 'HR Starter',
    audience: 'Hiring teams',
    price: '₹1,499',
    period: '/month',
    blurb: 'Screen every candidate’s certificates.',
    features: ['150 verifications a month', 'Bulk upload (ZIP / CSV)', '3 team seats', 'History and CSV export'],
    cta: { label: 'Join waitlist', href: `${WAITLIST}(HR%20Starter)` },
    featured: true,
  },
  {
    name: 'HR Growth',
    audience: 'Hiring teams',
    price: '₹4,999',
    period: '/month',
    blurb: 'Automate checks inside your hiring stack.',
    features: ['750 verifications a month', 'REST API and webhooks', '10 team seats', 'Priority support'],
    cta: { label: 'Join waitlist', href: `${WAITLIST}(HR%20Growth)` },
  },
];

export default function Pricing() {
  return (
    <section id="pricing" className="py-20 sm:py-28">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <p className="eyebrow">Pricing</p>
          <h2 className="mt-3 font-display text-4xl font-semibold tracking-tight text-navy-900 sm:text-5xl">
            Free for learners. Built for hiring teams.
          </h2>
          <p className="mt-4 text-lg text-navy-600">
            Start free today. Paid plans are opening soon, so join the waitlist for early pricing.
          </p>
        </div>

        <div className="mt-14 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`relative flex flex-col rounded-2xl p-7 ${
                plan.featured ? 'bg-navy-900 text-paper shadow-lift' : 'card'
              }`}
            >
              {plan.featured && (
                <span className="absolute -top-3 left-7 rounded-full bg-gold-400 px-3 py-1 text-xs font-semibold text-navy-900">
                  Most popular
                </span>
              )}
              <p className={`text-xs font-semibold uppercase tracking-[0.16em] ${plan.featured ? 'text-gold-400' : 'text-navy-500'}`}>
                {plan.audience}
              </p>
              <h3 className="mt-2 font-display text-2xl font-semibold">{plan.name}</h3>
              <p className={`mt-1 text-sm ${plan.featured ? 'text-navy-200' : 'text-navy-600'}`}>{plan.blurb}</p>
              <p className="mt-6 flex items-baseline gap-1">
                <span className="font-display text-4xl font-semibold">{plan.price}</span>
                {plan.period && <span className={`text-sm ${plan.featured ? 'text-navy-300' : 'text-navy-500'}`}>{plan.period}</span>}
              </p>
              <ul className="mt-6 flex-1 space-y-3 text-sm">
                {plan.features.map((f) => (
                  <li key={f} className="flex gap-2.5">
                    <Check className={`mt-0.5 h-4 w-4 shrink-0 ${plan.featured ? 'text-gold-400' : 'text-verified-600'}`} aria-hidden />
                    <span className={plan.featured ? 'text-navy-100' : 'text-navy-700'}>{f}</span>
                  </li>
                ))}
              </ul>
              <a
                href={plan.cta.href}
                className={`mt-8 ${plan.featured ? 'btn-secondary border-transparent' : 'btn-primary'}`}
              >
                {plan.cta.label}
              </a>
            </div>
          ))}
        </div>

        <p className="mt-8 text-center text-sm text-navy-500">
          Need more volume, SSO or on-premise forensics?{' '}
          <a href={`${WAITLIST}(Enterprise)`} className="font-medium text-navy-900 underline underline-offset-4">
            Talk to us about Enterprise
          </a>
          .
        </p>
      </div>
    </section>
  );
}
