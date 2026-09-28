'use client';

import React, { useState } from 'react';
import { CheckCircle, User, Hash, Building, Link as LinkIcon, ExternalLink, Copy, Check, Info } from 'lucide-react';
import { CertificateAnalysisResponse } from '@/types';
import { safeHttpUrl, validationUrl } from '@/lib/utils';

interface VerifiedCertificateProps {
  data: CertificateAnalysisResponse;
}

export default function VerifiedCertificate({ data }: VerifiedCertificateProps) {
  const [copied, setCopied] = useState(false);

  const token = data.report_token;
  const isIdOnly = data.verification.method?.startsWith('manual') ?? false;
  const issuer = data.extraction.issuer_name || data.extraction.issuer_org;
  const issuerLink = safeHttpUrl(data.verification.verification_url || data.extraction.issuer_url);

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

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Success Header */}
      <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl p-6 mb-6 border border-green-200">
        <div className="flex items-center gap-3 mb-3">
          <CheckCircle className="w-8 h-8 text-green-600" />
          <h2 className="text-2xl font-bold text-green-800">
            {isIdOnly ? 'Certificate ID Confirmed' : 'Certificate Verified!'}
          </h2>
        </div>
        <p className="text-green-700">{data.verification.message}</p>
      </div>

      {isIdOnly && (
        <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6 text-sm text-amber-800">
          <Info className="w-5 h-5 shrink-0 mt-0.5" />
          <p>
            This ID exists on the issuer&apos;s site. Because it was checked manually, we did not check
            the name on your document or scan the file for tampering.
          </p>
        </div>
      )}

      {/* Certificate Details */}
      <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6 space-y-6">
        
        {data.extraction.candidate_name && !isIdOnly && (
          <div className="flex items-start gap-3">
            <User className="w-5 h-5 text-blue-600 mt-1" />
            <div>
              <p className="text-sm text-gray-500 font-medium">Candidate Name</p>
              <p className="text-lg font-semibold text-gray-900">{data.extraction.candidate_name}</p>
            </div>
          </div>
        )}

        {data.extraction.certificate_id && (
          <div className="flex items-start gap-3">
            <Hash className="w-5 h-5 text-blue-600 mt-1" />
            <div>
              <p className="text-sm text-gray-500 font-medium">Certificate ID</p>
              <p className="text-lg font-mono text-gray-900 break-all">{data.extraction.certificate_id}</p>
            </div>
          </div>
        )}

        {issuer && (
          <div className="flex items-start gap-3">
            <Building className="w-5 h-5 text-blue-600 mt-1" />
            <div>
              <p className="text-sm text-gray-500 font-medium">Issuing Organization</p>
              <p className="text-lg font-semibold text-gray-900">{issuer}</p>
            </div>
          </div>
        )}

        {issuerLink && (
          <div className="flex items-start gap-3">
            <LinkIcon className="w-5 h-5 text-blue-600 mt-1" />
            <div className="flex-1">
              <p className="text-sm text-gray-500 font-medium">Verification URL</p>
              <a 
                href={issuerLink} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-700 underline break-all"
              >
                {issuerLink}
              </a>
            </div>
          </div>
        )}

        <div className="border-t border-gray-200"></div>

        {/* Forensics Info */}
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-sm font-medium text-gray-700 mb-2">Security Analysis</p>
          <div className="space-y-1 text-sm text-gray-600">
            <p>• Risk Level: <span className={`font-semibold ${data.forensics.is_high_risk ? 'text-red-600' : 'text-green-600'}`}>
              {data.forensics.status === 'skipped' ? 'Not checked' : data.forensics.is_high_risk ? 'High Risk' : 'Low Risk'}
            </span></p>
            <p>• Status: <span className="font-semibold">{data.forensics.status}</span></p>
          </div>
        </div>

        {/* Actions */}
        {token && (
          <div className="space-y-3">
            <button
              onClick={handleViewCertificate}
              className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white font-medium py-3 px-6 rounded-lg transition-all shadow-md hover:shadow-lg"
            >
              <ExternalLink className="w-5 h-5" />
              View Validation Certificate
            </button>
            
            <button
              onClick={handleCopyLink}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg transition-all shadow-md hover:shadow-lg"
            >
              {copied ? <Check className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
              {copied ? 'Link copied' : 'Copy verification link'}
            </button>
            <p className="text-xs text-gray-500 text-center">
              Anyone with this link can confirm the result is genuine. It contains the name and ID shown above, so share it deliberately.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
