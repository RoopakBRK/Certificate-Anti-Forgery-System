'use client';

import React, { useState } from 'react';
import { AlertCircle, Loader2, CheckCircle, ArrowRight } from 'lucide-react';
import { verificationService } from '@/services/api';
import { CertificateAnalysisResponse } from '@/types';

interface ManualVerificationFormProps {
  onVerificationComplete?: (data: CertificateAnalysisResponse) => void;
}

export default function ManualVerificationForm({ onVerificationComplete }: ManualVerificationFormProps) {
  const [certificateId, setCertificateId] = useState('');
  const [issuerUrl, setIssuerUrl] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!certificateId.trim() || !issuerUrl.trim()) {
      setError('Both Certificate ID and Issuer URL are required.');
      return;
    }

    setIsVerifying(true);
    setError(null);

    try {
      const result = await verificationService.manualVerify({
        certificate_id: certificateId.trim(),
        issuer_url: issuerUrl.trim(),
      });
      
      if (onVerificationComplete) {
        onVerificationComplete(result);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Verification failed. Please try again.');
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      
      {/* Modern Info Header */}
      <div className="rounded-xl border border-warn-200 bg-warn-50 p-5 mb-6">
        <div className="flex items-start gap-4">
          <div className="p-2 bg-warn-100 rounded-full shrink-0">
            <AlertCircle className="w-5 h-5 text-warn-700" />
          </div>
          <div>
            <h3 className="font-display font-semibold text-navy-900 text-xl">Manual Verification Required</h3>
            <p className="text-navy-700 mt-1 leading-relaxed text-sm">
              We couldn&apos;t automatically verify this certificate. Enter its ID and the issuer&apos;s verification link below. We&apos;ll check that the ID appears on the issuer&apos;s own page. This confirms the ID exists but does not check the name on your document.
            </p>
          </div>
        </div>
      </div>

      {/* Card Form */}
      <form 
        onSubmit={handleSubmit} 
        className="card p-6 sm:p-8 space-y-6"
      >
        <div className="space-y-6">
          {/* Certificate ID Input */}
          <div className="group">
            <label htmlFor="certificate-id" className="block text-sm font-semibold text-navy-800 mb-2">
              Certificate ID
            </label>
            <div className="relative">
              <input
                type="text"
                id="certificate-id"
                value={certificateId}
                onChange={(e) => setCertificateId(e.target.value)}
                placeholder="e.g., ABC123456789"
                className="w-full px-4 py-3 bg-paper border border-navy-200 rounded-lg focus:bg-white focus:ring-2 focus:ring-navy-900/10 focus:border-navy-500 transition-all duration-200 outline-none placeholder:text-navy-300"
                disabled={isVerifying}
                aria-invalid={!!error}
                aria-describedby={error ? 'manual-error' : undefined}
              />
            </div>
            <p className="mt-2 text-xs text-navy-500 flex items-center gap-1">
              <ArrowRight className="w-3 h-3" /> The unique ID found on the certificate
            </p>
          </div>

          {/* Issuer URL Input */}
          <div className="group">
            <label htmlFor="issuer-url" className="block text-sm font-semibold text-navy-800 mb-2">
              Issuer Verification URL
            </label>
            <input
              type="url"
              id="issuer-url"
              value={issuerUrl}
              onChange={(e) => setIssuerUrl(e.target.value)}
              placeholder="e.g., https://coursera.org/verify/..."
              className="w-full px-4 py-3 bg-paper border border-navy-200 rounded-lg focus:bg-white focus:ring-2 focus:ring-navy-900/10 focus:border-navy-500 transition-all duration-200 outline-none placeholder:text-navy-300"
              disabled={isVerifying}
            />
            <p className="mt-2 text-xs text-navy-500 flex items-center gap-1">
              <ArrowRight className="w-3 h-3" /> The direct link to verify this credential
            </p>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div id="manual-error" role="alert" className="p-4 bg-danger-50 border border-danger-200 text-danger-700 text-sm rounded-lg flex items-center gap-3 animate-in fade-in slide-in-from-top-2">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span className="font-medium">{error}</span>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isVerifying || !certificateId.trim() || !issuerUrl.trim()}
          className={`
            w-full flex items-center justify-center gap-2 py-3.5 px-6 rounded-lg font-semibold text-white text-sm transition-all duration-200
            ${isVerifying || !certificateId.trim() || !issuerUrl.trim()
              ? 'bg-navy-200 cursor-not-allowed' 
              : 'bg-navy-900 hover:bg-navy-700 shadow-sm'}
          `}
        >
          {isVerifying ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Verifying details...
            </>
          ) : (
            <>
              Verify Certificate
              <CheckCircle className="w-5 h-5" />
            </>
          )}
        </button>
      </form>
    </div>
  );
}