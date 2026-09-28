'use client';

import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { QRCodeSVG } from 'qrcode.react';
import { ShieldCheck, Printer, Home, Loader2, AlertTriangle, Calendar, Hash, Building, Link as LinkIcon } from 'lucide-react';
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
      <div className="min-h-screen flex items-center justify-center bg-gray-100" role="status">
        <Loader2 className="w-10 h-10 text-blue-600 animate-spin" aria-label="Validating certificate" />
      </div>
    );
  }

  if (state.status !== 'ok') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100 px-4">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-14 h-14 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-slate-900 mb-2">
            {state.status === 'invalid' ? 'Invalid verification link' : 'Could not validate'}
          </h1>
          <p className="text-slate-600 mb-6">
            {state.status === 'invalid'
              ? 'This link was not issued by CAFS or has been altered. Do not rely on it.'
              : state.message}
          </p>
          <Link href="/" className="text-blue-600 hover:underline">Go to CAFS</Link>
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
    <main className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-5xl shadow-2xl rounded-2xl overflow-hidden flex flex-col md:flex-row">

        {/* LEFT: sidebar */}
        <div className="w-full md:w-1/3 bg-slate-900 text-white p-8 flex flex-col items-center text-center">
          {pageUrl && (
            <div className="bg-white p-3 rounded-xl shadow-lg mb-6">
              <QRCodeSVG value={pageUrl} size={144} aria-label="QR code linking to this validation page" />
            </div>
          )}

          <div className="mb-8">
            <div className="flex items-center justify-center gap-2 text-emerald-400 mb-2">
              <ShieldCheck className="w-5 h-5" />
              <span className="font-bold tracking-wide uppercase text-sm">
                {isIdOnly ? 'ID Confirmed' : 'Verified'}
              </span>
            </div>
            <h2 className="text-lg font-semibold text-slate-100 leading-tight">
              Checked by <span className="text-blue-400">CAFS</span>
            </h2>
          </div>

          <div className="w-full border-t border-slate-700 mb-8" />

          <dl className="w-full space-y-5 text-left text-sm">
            <div>
              <dt className="text-slate-400 text-xs uppercase tracking-wider mb-1">Date of Verification</dt>
              <dd className="font-medium text-slate-100 flex items-center gap-2">
                <Calendar className="w-4 h-4 text-blue-400" /> {verifiedOn}
              </dd>
            </div>

            {report.certificate_id && (
              <div>
                <dt className="text-slate-400 text-xs uppercase tracking-wider mb-1">Certificate ID</dt>
                <dd className="bg-slate-800 p-2 rounded border border-slate-700 font-mono text-xs text-yellow-400 break-all select-all flex gap-2">
                  <Hash className="w-3.5 h-3.5 shrink-0 mt-0.5" /> {report.certificate_id}
                </dd>
              </div>
            )}

            {issuerLink && (
              <div>
                <dt className="text-slate-400 text-xs uppercase tracking-wider mb-1">Issuer Page</dt>
                <dd>
                  <a href={issuerLink} target="_blank" rel="noopener noreferrer"
                     className="text-blue-400 hover:text-blue-300 flex items-start gap-2 text-xs break-all">
                    <LinkIcon className="w-3.5 h-3.5 shrink-0 mt-0.5" /> {issuerLink}
                  </a>
                </dd>
              </div>
            )}

            {report.issuer_name && (
              <div>
                <dt className="text-slate-400 text-xs uppercase tracking-wider mb-1">Issuing Organization</dt>
                <dd className="text-blue-400 flex items-center gap-2">
                  <Building className="w-4 h-4" /> {report.issuer_name}
                </dd>
              </div>
            )}
          </dl>
        </div>

        {/* RIGHT: certificate */}
        <div className="w-full md:w-2/3 p-8 md:p-12 flex flex-col">
          <div className="flex justify-between items-start mb-10">
            <div>
              <h1 className="text-3xl font-bold text-slate-800 mb-2">Verification Report</h1>
              <p className="text-slate-500">
                {isIdOnly
                  ? 'The certificate ID below was found on the issuer’s own verification page.'
                  : 'The certificate below was matched against the issuer’s own verification page.'}
              </p>
            </div>
            <div className="hidden sm:flex items-center justify-center w-16 h-16 bg-blue-600 text-white rounded-lg shadow-md font-bold text-2xl" aria-hidden>
              SK
            </div>
          </div>

          <div className="space-y-6 mb-10">
            {report.candidate_name && !isIdOnly && (
              <div>
                <p className="block text-sm font-medium text-slate-400 mb-1">Issued To</p>
                <p className="text-2xl font-serif text-slate-900">{report.candidate_name}</p>
              </div>
            )}
            {report.issuer_name && (
              <div>
                <p className="block text-sm font-medium text-slate-400 mb-1">Issuing Organization</p>
                <p className="text-xl text-slate-700">{report.issuer_name}</p>
              </div>
            )}
            {isIdOnly && (
              <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
                Manual check: the name on the holder&apos;s document was not compared and the file was not scanned for tampering.
              </p>
            )}
            {!isIdOnly && report.forensics_status && (
              <div>
                <p className="block text-sm font-medium text-slate-400 mb-1">Document integrity</p>
                <p className="text-base text-slate-700">{report.forensics_status}</p>
              </div>
            )}
          </div>

          <div className="mt-auto border-t border-slate-200 pt-6 flex flex-col sm:flex-row justify-between items-center text-sm text-slate-500 gap-4">
            <p>
              Status:{' '}
              <span className="font-bold px-2 py-0.5 rounded text-emerald-700 bg-emerald-100">
                {isIdOnly ? 'ID CONFIRMED' : report.verdict}
              </span>
            </p>
            <p className="text-xs">This report is digitally signed by CAFS.</p>
          </div>

          <div className="flex gap-3 mt-6 print:hidden">
            <button
              onClick={() => window.print()}
              className="flex-1 inline-flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg transition-colors text-sm font-medium"
            >
              <Printer className="w-4 h-4" /> Print
            </button>
            <Link
              href="/"
              className="flex-1 inline-flex items-center justify-center gap-2 bg-slate-200 hover:bg-slate-300 text-slate-700 py-2 px-4 rounded-lg transition-colors text-sm font-medium"
            >
              <Home className="w-4 h-4" /> Home
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
