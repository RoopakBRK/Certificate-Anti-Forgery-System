import Link from 'next/link';
import { ExternalLink, FileSearch } from 'lucide-react';
import type { CafsReport } from '@/types';
import { cn } from '@/lib/utils';
import DeleteReportButton from './DeleteReportButton';

const PLAN_LABEL: Record<string, string> = {
  free: 'Free',
  learner_pro: 'Learner Pro',
  hr_starter: 'HR Starter',
  hr_growth: 'HR Growth',
  enterprise: 'Enterprise',
};

interface Props {
  name: string;
  email: string;
  avatarUrl?: string | null;
  plan: string;
  reports: CafsReport[];
  loadError: string | null;
}

function verdictStyle(r: CafsReport) {
  if (r.is_high_risk || r.final_verdict.startsWith('FLAGGED')) return { label: 'Flagged', cls: 'bg-danger-50 text-danger-700 border-danger-200' };
  if (r.is_verified) return { label: r.mode === 'manual' ? 'ID confirmed' : 'Verified', cls: 'bg-verified-50 text-verified-700 border-verified-200' };
  return { label: 'Unverified', cls: 'bg-warn-50 text-warn-800 border-warn-200' };
}

const dateFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });

export default function UserProfile({ name, email, avatarUrl, plan, reports, loadError }: Props) {
  const verified = reports.filter((r) => r.is_verified && !r.is_high_risk).length;
  const flagged = reports.filter((r) => r.is_high_risk || r.final_verdict.startsWith('FLAGGED')).length;
  const unverified = reports.length - verified - flagged;
  const thisMonth = reports.filter((r) => new Date(r.created_at).getMonth() === new Date().getMonth()
    && new Date(r.created_at).getFullYear() === new Date().getFullYear()).length;

  const stats = [
    { label: 'Verified', value: verified, cls: 'text-verified-700' },
    { label: 'Unverified', value: unverified, cls: 'text-warn-700' },
    { label: 'Flagged', value: flagged, cls: 'text-danger-700' },
    { label: 'This month', value: thisMonth, cls: 'text-navy-900' },
  ];

  return (
    <div className="mx-auto max-w-5xl px-4 pb-20 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
        <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-full border border-navy-200 bg-navy-50 font-display text-2xl font-semibold text-navy-800">
          {avatarUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={avatarUrl} alt="" className="h-full w-full object-cover" referrerPolicy="no-referrer" />
          ) : (
            name[0]?.toUpperCase()
          )}
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-display text-3xl font-semibold tracking-tight text-navy-900">{name}</h1>
          <p className="truncate text-navy-600">{email}</p>
        </div>
        <span className="self-start rounded-full border border-navy-200 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-navy-600 sm:self-center">
          {PLAN_LABEL[plan] ?? plan} plan
        </span>
      </div>

      {/* Stats */}
      <dl className="mt-10 grid grid-cols-2 gap-4 md:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="card p-5">
            <dt className="text-sm text-navy-500">{s.label}</dt>
            <dd className={cn('mt-1 font-display text-3xl font-semibold', s.cls)}>{s.value}</dd>
          </div>
        ))}
      </dl>

      {/* History */}
      <section className="card mt-10 overflow-hidden">
        <div className="flex items-center justify-between border-b border-navy-100 px-6 py-4">
          <h2 className="font-display text-xl font-semibold text-navy-900">Verification history</h2>
          <Link href="/#verify" className="btn-primary px-4 py-2 text-sm">
            Verify a certificate
          </Link>
        </div>

        {loadError && <p className="px-6 py-6 text-sm text-danger-700">{loadError}</p>}

        {!loadError && reports.length === 0 && (
          <div className="flex flex-col items-center px-6 py-14 text-center">
            <FileSearch className="h-10 w-10 text-navy-300" aria-hidden />
            <p className="mt-3 font-medium text-navy-800">No verifications yet</p>
            <p className="mt-1 max-w-sm text-sm text-navy-500">
              Certificates you check while signed in are saved here, with their signed report links.
            </p>
          </div>
        )}

        {reports.length > 0 && (
          <ul className="divide-y divide-navy-100">
            {reports.map((r) => {
              const v = verdictStyle(r);
              return (
                <li key={r.id} className="grid gap-2 px-6 py-4 sm:grid-cols-[1fr_auto] sm:items-center sm:gap-6">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={cn('rounded-full border px-2.5 py-0.5 text-xs font-semibold', v.cls)}>{v.label}</span>
                      <span className="truncate font-medium text-navy-900">
                        {r.candidate_name || (r.mode === 'manual' ? 'Manual ID check' : r.filename || 'Certificate')}
                      </span>
                    </div>
                    <p className="mt-1 truncate text-sm text-navy-500">
                      {[r.issuer_name, r.certificate_id].filter(Boolean).join(' · ') || 'Issuer not identified'}
                    </p>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <time className="text-navy-500" dateTime={r.created_at}>
                      {dateFmt.format(new Date(r.created_at))}
                    </time>
                    {r.report_token && (
                      <Link
                        href={`/validation-certificate?t=${encodeURIComponent(r.report_token)}`}
                        className="inline-flex items-center gap-1 font-medium text-navy-800 underline underline-offset-4 hover:text-navy-950"
                      >
                        Report <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                      </Link>
                    )}
                    <DeleteReportButton id={r.id} />
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
