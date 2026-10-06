'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Navbar from '@/components/ui/Navbar';
import VerifiedCertificate from '@/components/verification/VerifiedCertificate';
import ManualVerificationForm from '@/components/verification/ManualVerificationForm';
import CertificateNotFound from '@/components/verification/CertificateNotFound';
import FlaggedCertificate from '@/components/verification/FlaggedCertificate';
import OcrSummary from '@/components/verification/OcrSummary';
import { Loader2, ArrowLeft, AlertTriangle } from 'lucide-react';
import { CertificateAnalysisResponse } from '@/types';

export default function VerifyResultPage() {
  const router = useRouter();
  const [result, setResult] = useState<CertificateAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showManualForm, setShowManualForm] = useState(false);

  useEffect(() => {
    // Retrieve the verification result from sessionStorage
    try {
      const storedResult = sessionStorage.getItem('verificationResult');
      if (storedResult) {
        const parsedResult: CertificateAnalysisResponse = JSON.parse(storedResult);
        setResult(parsedResult);
        // Offer manual verification only for plain UNVERIFIED results.
        // A FLAGGED (tampered) document must never be turned into "verified" by typing an ID.
        setShowManualForm(!parsedResult.verification.is_verified && !parsedResult.forensics.is_high_risk);
      }
    } catch (error) {
      console.error('Error reading verification result:', error);
    }
    setIsLoading(false);
  }, []);

  const handleManualVerificationComplete = (data: CertificateAnalysisResponse) => {
    setResult(data);
    setShowManualForm(false);
    try {
      sessionStorage.setItem('verificationResult', JSON.stringify(data));
    } catch {
      /* storage unavailable: the result still shows on this page */
    }
  };

  if (isLoading) {
    return (
      <main className="min-h-screen bg-paper">
        <Navbar />
        <div className="flex items-center justify-center min-h-[calc(100vh-4rem)]">
          <div className="text-center">
            <Loader2 className="w-10 h-10 text-navy-900 animate-spin mx-auto mb-4" />
            <p className="text-navy-600">Loading verification results...</p>
          </div>
        </div>
      </main>
    );
  }

  if (!result) {
    return (
      <main className="min-h-screen bg-paper">
        <Navbar />
        <div className="flex items-center justify-center min-h-[calc(100vh-4rem)] px-4">
          <div className="text-center max-w-md">
            <AlertTriangle className="w-14 h-14 text-warn-600 mx-auto mb-4" />
            <h1 className="font-display text-3xl font-semibold text-navy-900 mb-2">No Results Found</h1>
            <p className="text-navy-600 mb-6">
              No verification data available. Please upload a certificate first.
            </p>
            <Link 
              href="/" 
              className="btn-primary"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to upload
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-paper">
      <Navbar />
      
      <div className="max-w-3xl mx-auto px-4 pt-24 pb-16 md:pt-32">
        
        {/* Back Button */}
        <Link 
          href="/"
          className="inline-flex items-center gap-2 text-navy-600 hover:text-navy-900 text-sm font-medium mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to upload
        </Link>

        {/* Results Header */}
        <div className="mb-8">
          <h1 className="font-display text-4xl font-semibold tracking-tight text-navy-900 mb-2">
            Verification result
          </h1>
          <p className="text-navy-600">
            File: <span className="font-medium text-navy-900">{result.filename}</span>
          </p>
        </div>

        {/* Render appropriate component based on verification status */}
        {result.forensics.is_high_risk ? (
          <FlaggedCertificate data={result} />
        ) : showManualForm ? (
          <ManualVerificationForm onVerificationComplete={handleManualVerificationComplete} />
        ) : result.verification.is_verified ? (
          <VerifiedCertificate data={result} />
        ) : (
          <CertificateNotFound
            message={result.verification.message}
            onRetry={() => setShowManualForm(true)}
          />
        )}

        {!showManualForm && <OcrSummary ocr={result.extraction.ocr} />}
      </div>
    </main>
  );
}
