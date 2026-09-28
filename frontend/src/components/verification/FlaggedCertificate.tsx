import React from 'react';
import { ShieldAlert, Home } from 'lucide-react';
import Link from 'next/link';
import { CertificateAnalysisResponse } from '@/types';

export default function FlaggedCertificate({ data }: { data: CertificateAnalysisResponse }) {
  return (
    <div className="bg-white rounded-xl shadow-lg border border-red-200 p-8 md:p-12 text-center max-w-2xl mx-auto">
      <div className="mb-6 inline-flex p-4 bg-red-50 rounded-full">
        <ShieldAlert className="w-16 h-16 text-red-600" />
      </div>
      <h2 className="text-3xl font-bold text-slate-900 mb-4">This document was flagged</h2>
      <p className="text-slate-600 text-lg mb-6 leading-relaxed">
        Our forensic checks found signs that this file may have been digitally altered. It cannot be
        verified. If you believe this is a mistake, obtain a fresh copy from the issuer and upload it again.
      </p>
      <div className="bg-red-50 rounded-lg p-4 text-left text-sm text-red-800 mb-8">
        <p className="font-semibold mb-1">{data.forensics.status}</p>
        {data.forensics.details && data.forensics.details.length > 0 && (
          <ul className="list-disc pl-5 space-y-0.5">
            {data.forensics.details.map((d, i) => <li key={i}>{d}</li>)}
          </ul>
        )}
      </div>
      <Link
        href="/"
        className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors shadow-md"
      >
        <Home className="w-5 h-5" />
        Back to Home
      </Link>
    </div>
  );
}
