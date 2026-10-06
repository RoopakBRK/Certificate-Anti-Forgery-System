'use client';

import React, { useState } from 'react';
import { ExternalLink, Copy, Check, Info } from 'lucide-react';
import { CertificateAnalysisResponse } from '@/types';
import { safeHttpUrl, validationUrl } from '@/lib/utils';
import Seal from '@/components/ui/Seal';

interface VerifiedCertificateProps {
  data: CertificateAnalysisResponse;
}

export default function VerifiedCertificate({ data }: VerifiedCertificateProps) {
  const [copied, setCopied] = useState(false);

  const token = data.report_token;
  const isIdOnly = data.verification.method?.startsWith('manual') ?? false;
  const issuer = data.extraction.issuer_name || data.extraction.issuer_org;
  const issuerLink = safeHttpUrl(data.verification.verification_url || data.extraction.issuer_url);
  const forensicsLabel =
    data.forensics.status === 'skipped' ? 'Not checked' : data.forensics.is_high_risk ? 'High risk' : 'No tampering found';

  const handleViewCertificate = () => {
    if (token) window.open(validationUrl(token), '_blank', 'noopener,noreferrer');
  };

  const handleCopyLink = async () => {
    if (!token) return;
    try {
      await navigator.clipboard.writeText(validationUrl(token));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable */
    }
  };

  const rows: [string, React.ReactNode][] = [];
  if (data.extraction.candidate_name && !isIdOnly) rows.push(['Issued to', data.extraction.candidate_name]);
  if (issuer) rows.push(['Issuer', issuer]);
  if (data.extraction.certificate_id)
    rows.push(['Certificate ID', <span key="id" className="break-all font-mono text-sm">{data.extraction.certificate_id}</span>]);
  if (issuerLink)
    rows.push([
      'Issuer page',
      <a key="url" href={issuerLink} target="_blank" rel="noopener noreferrer" className="break-all text-sm text-navy-700 underline underline-offset-4 hover:text-navy-900">
        {issuerLink}
      </a>,
    ]);
  rows.push(['Document integrity', forensicsLabel]);

  return (
    <div className="card mx-auto w-full max-w-2xl overflow-hidden">
      {/* Verdict band */}
      <div className="flex items-center gap-5 border-b border-verified-100 bg-verified-50 px-6 py-6 sm:px-8">
        <Seal tone="verified" mark="check" size={64} className="shrink-0" label="Verified" />
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-verified-700">
            {isIdOnly ? 'ID confirmed' : 'Verified'}
          </p>
          <h2 className="mt-1 font-display text-2xl font-semibold text-navy-900 sm:text-3xl">
            {isIdOnly ? 'Certificate ID confirmed' : 'This certificate is genuine'}
          </h2>
          <p className="mt-1 text-sm text-verified-800">{data.verification.message}</p>
        </div>
      </div>

      <div className="px-6 py-6 sm:px-8">
        {isIdOnly && (
          <div className="mb-6 flex items-start gap-3 rounded-lg border border-warn-200 bg-warn-50 p-4 text-sm text-warn-800">
            <Info className="mt-0.5 h-5 w-5 shrink-0" />
            <p>
              This ID exists on the issuer&apos;s site. Because it was checked manually, we did not check
              the name on your document or scan the file for tampering.
            </p>
          </div>
        )}

        <dl className="divide-y divide-dashed divide-navy-100">
          {rows.map(([label, value]) => (
            <div key={label} className="grid gap-1 py-3.5 sm:grid-cols-[10rem_1fr] sm:gap-4">
              <dt className="text-sm text-navy-500">{label}</dt>
              <dd className={`font-medium text-navy-900 ${label === 'Issued to' ? 'font-display text-xl' : ''}`}>{value}</dd>
            </div>
          ))}
        </dl>

        {token && (
          <div className="mt-8 border-t border-navy-100 pt-6">
            <div className="grid gap-3 sm:grid-cols-2">
              <button onClick={handleViewCertificate} className="btn-primary">
                <ExternalLink className="h-4 w-4" />
                View signed report
              </button>
              <button onClick={handleCopyLink} className="btn-secondary">
                {copied ? <Check className="h-4 w-4 text-verified-600" /> : <Copy className="h-4 w-4" />}
                {copied ? 'Link copied' : 'Copy share link'}
              </button>
            </div>
            <p className="mt-3 text-center text-xs text-navy-500">
              Anyone with this link can confirm the result is genuine. It contains the name and ID shown above, so share it deliberately.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
