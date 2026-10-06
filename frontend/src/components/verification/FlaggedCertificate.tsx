import React from 'react';
import { Home } from 'lucide-react';
import Link from 'next/link';
import { CertificateAnalysisResponse } from '@/types';
import Seal from '@/components/ui/Seal';

export default function FlaggedCertificate({ data }: { data: CertificateAnalysisResponse }) {
  return (
    <div className="card mx-auto w-full max-w-2xl overflow-hidden">
      <div className="flex items-center gap-5 border-b border-danger-100 bg-danger-50 px-6 py-6 sm:px-8">
        <Seal tone="danger" mark="alert" size={64} className="shrink-0" label="Flagged" />
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-danger-700">Flagged</p>
          <h2 className="mt-1 font-display text-2xl font-semibold text-navy-900 sm:text-3xl">This document may be altered</h2>
        </div>
      </div>
      <div className="px-6 py-6 sm:px-8">
        <p className="leading-relaxed text-navy-700">
          Our forensic checks found signs that this file may have been digitally edited, so it cannot be
          verified. If you believe this is a mistake, download a fresh copy from the issuer and upload it again.
        </p>
        <div className="mt-6 rounded-lg border border-danger-100 bg-danger-50/60 p-4 text-sm text-danger-800">
          <p className="font-semibold">{data.forensics.status}</p>
          {data.forensics.details && data.forensics.details.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {data.forensics.details.map((d, i) => <li key={i}>{d}</li>)}
            </ul>
          )}
        </div>
        <Link href="/#verify" className="btn-primary mt-8 w-full sm:w-auto">
          <Home className="h-4 w-4" />
          Check another certificate
        </Link>
      </div>
    </div>
  );
}
