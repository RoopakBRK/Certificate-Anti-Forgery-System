'use client';

import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { QRCodeSVG } from 'qrcode.react';
import { ShieldCheck, Printer, Home, Loader2, Calendar, Hash, Building, Link as LinkIcon } from 'lucide-react';
import Seal from '@/components/ui/Seal';
import { verificationService } from '@/services/api';
import { safeHttpUrl } from '@/lib/utils';
import type { ReportPayload } from '@/types';

type State =
  | { status: 'loading' }
  | { status: 'invalid' }
  | { status: 'error'; message: string }
  | { status: 'ok'; report: ReportPayload };

export default function ValidationView() {
  const token = useSearchParams().get('t');
  const [state, setState] = useState<State>({ status: 'loading' });
  const [pageUrl, setPageUrl] = useState('');

  useEffect(() => {
    setPageUrl(window.location.href);
    if (!token) {
      setState({ status: 'invalid' });
      return;
    }
    let cancelled = false;
    verificationService
      .getReport(token)
      .then((report) => !cancelled && setState({ status: 'ok', report }))
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : 'Could not validate this certificate.';
        // The server answers 404 for tokens it did not issue (forged or corrupted)
        setState(message.includes('not found or invalid') ? { status: 'invalid' } : { status: 'error', message });
      });
    return () => { cancelled = true; };
  }, [token]);

  if (state.status === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper" role="status">
        <Loader2 className="h-10 w-10 animate-spin text-navy-900" aria-label="Validating certificate" />
      </div>
    );
  }

  if (state.status !== 'ok') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper px-4">
        <div className="max-w-md text-center">
          <Seal tone="danger" mark="alert" size={72} className="mx-auto mb-5" />
          <h1 className="mb-2 font-display text-3xl font-semibold text-navy-900">
            {state.status === 'invalid' ? 'Invalid verification link' : 'Could not validate'}
          </h1>
          <p className="mb-6 text-navy-600">
            {state.status === 'invalid'
              ? 'This link was not issued by CAFS or has been altered. Do not rely on it.'
              : state.message}
          </p>
          <Link href="/" className="btn-secondary">Go to CAFS</Link>
        </div>
      </div>
    );
  }

  const { report } = state;
  const isIdOnly = report.scope === 'id_only';
  const verifiedOn = new Date(report.verified_at * 1000).toLocaleDateString('en-US', {
    day: 'numeric', month: 'long', year: 'numeric',
  });
  const issuerLink = safeHttpUrl(report.verification_url);

  return (
    <main className="guilloche flex min-h-screen items-center justify-center bg-paper p-4 py-10 print:bg-white print:p-0">
      <article className="w-full max-w-4xl overflow-hidden rounded-2xl border border-navy-100 bg-white shadow-lift print:shadow-none">
        {/* Header band */}
        <header className="flex items-center justify-between gap-4 bg-navy-900 px-6 py-5 text-paper sm:px-10">
          <div className="flex items-center gap-3">
            <Seal size={36} className="rounded-full ring-1 ring-navy-600" />
            <div className="leading-tight">
              <p className="font-display text-lg font-semibold">CAFS</p>
              <p className="text-[10px] uppercase tracking-[0.16em] text-navy-300">Certificate Anti Forgery System</p>
            </div>
          </div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gold-400">Verification report</p>
        </header>

        <div className="grid gap-10 px-6 py-10 sm:px-10 md:grid-cols-[1fr_auto]">
          {/* Certificate body */}
          <div>
            <div className="flex items-center gap-4">
              <Seal tone="verified" mark="check" size={60} className="shrink-0" label={isIdOnly ? 'ID confirmed' : 'Verified'} />
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-verified-700">
                  {isIdOnly ? 'ID confirmed' : report.verdict}
                </p>
                <p className="mt-1 text-sm text-navy-600">
                  {isIdOnly
                    ? 'The certificate ID below was found on the issuer’s own verification page.'
                    : 'This certificate was matched against the issuer’s own verification page.'}
                </p>
              </div>
            </div>

            {report.candidate_name && !isIdOnly && (
              <div className="mt-10">
                <p className="eyebrow">Issued to</p>
                <p className="mt-2 font-display text-4xl text-navy-900">{report.candidate_name}</p>
              </div>
            )}

            <dl className="mt-10 divide-y divide-dashed divide-navy-100 border-y border-navy-100 text-sm">
              {report.issuer_name && (
                <div className="grid gap-1 py-3 sm:grid-cols-[11rem_1fr]">
                  <dt className="flex items-center gap-2 text-navy-500"><Building className="h-4 w-4" /> Issuer</dt>
                  <dd className="font-medium text-navy-900">{report.issuer_name}</dd>
                </div>
              )}
              {report.certificate_id && (
                <div className="grid gap-1 py-3 sm:grid-cols-[11rem_1fr]">
                  <dt className="flex items-center gap-2 text-navy-500"><Hash className="h-4 w-4" /> Certificate ID</dt>
                  <dd className="select-all break-all font-mono text-navy-900">{report.certificate_id}</dd>
                </div>
              )}
              <div className="grid gap-1 py-3 sm:grid-cols-[11rem_1fr]">
                <dt className="flex items-center gap-2 text-navy-500"><Calendar className="h-4 w-4" /> Verified on</dt>
                <dd className="font-medium text-navy-900">{verifiedOn}</dd>
              </div>
              {!isIdOnly && report.forensics_status && (
                <div className="grid gap-1 py-3 sm:grid-cols-[11rem_1fr]">
                  <dt className="flex items-center gap-2 text-navy-500"><ShieldCheck className="h-4 w-4" /> Document integrity</dt>
                  <dd className="font-medium text-navy-900">{report.forensics_status}</dd>
                </div>
              )}
              {issuerLink && (
                <div className="grid gap-1 py-3 sm:grid-cols-[11rem_1fr]">
                  <dt className="flex items-center gap-2 text-navy-500"><LinkIcon className="h-4 w-4" /> Issuer page</dt>
                  <dd>
                    <a href={issuerLink} target="_blank" rel="noopener noreferrer" className="break-all text-navy-700 underline underline-offset-4 hover:text-navy-900">
                      {issuerLink}
                    </a>
                  </dd>
                </div>
              )}
            </dl>

            {isIdOnly && (
              <p className="mt-6 rounded-lg border border-warn-200 bg-warn-50 p-3 text-sm text-warn-800">
                Manual check: the name on the holder&apos;s document was not compared and the file was not scanned for tampering.
              </p>
            )}
          </div>

          {/* QR */}
          {pageUrl && (
            <div className="flex flex-col items-center gap-3 md:w-44">
              <div className="rounded-xl border border-navy-100 bg-white p-3">
                <QRCodeSVG value={pageUrl} size={140} fgColor="#0B1F3A" aria-label="QR code linking to this validation page" />
              </div>
              <p className="text-center text-xs text-navy-500">Scan to re-check this report online</p>
            </div>
          )}
        </div>

        <footer className="flex flex-col items-center justify-between gap-4 border-t border-navy-100 bg-paper px-6 py-5 text-xs text-navy-500 sm:flex-row sm:px-10">
          <p>This report is digitally signed by CAFS. Edited copies show as invalid.</p>
          <div className="flex gap-3 print:hidden">
            <button onClick={() => window.print()} className="btn-secondary px-4 py-2">
              <Printer className="h-4 w-4" /> Print
            </button>
            <Link href="/" className="btn-primary px-4 py-2">
              <Home className="h-4 w-4" /> CAFS home
            </Link>
          </div>
        </footer>
      </article>
    </main>
  );
}
