import React from 'react';
import { RotateCcw, Home } from 'lucide-react';
import Link from 'next/link';
import Seal from '@/components/ui/Seal';

interface CertificateNotFoundProps {
  message?: string;
  onRetry?: () => void;
}

export default function CertificateNotFound({ message, onRetry }: CertificateNotFoundProps) {
  return (
    <div className="card mx-auto w-full max-w-2xl overflow-hidden">
      <div className="flex items-center gap-5 border-b border-warn-100 bg-warn-50 px-6 py-6 sm:px-8">
        <Seal tone="warn" mark="question" size={64} className="shrink-0" label="Unverified" />
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-warn-700">Unverified</p>
          <h2 className="mt-1 font-display text-2xl font-semibold text-navy-900 sm:text-3xl">
            We couldn&apos;t confirm this certificate
          </h2>
        </div>
      </div>
      <div className="px-6 py-6 sm:px-8">
        <p className="leading-relaxed text-navy-700">
          {message ||
            "The certificate ID or link may be incorrect, or the certificate may not be publicly visible on the issuer's site."}
        </p>
        <p className="mt-2 text-sm text-navy-500">
          Unverified doesn&apos;t mean fake. Check the details and try again, or upload a different file.
        </p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          {onRetry && (
            <button onClick={onRetry} className="btn-primary">
              <RotateCcw className="h-4 w-4" />
              Enter the ID manually
            </button>
          )}
          <Link href="/#verify" className="btn-secondary">
            <Home className="h-4 w-4" />
            Upload another file
          </Link>
        </div>
      </div>
    </div>
  );
}
