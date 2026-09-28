import React from 'react';
import { XCircle, RotateCcw, Home } from 'lucide-react';
import Link from 'next/link';

interface CertificateNotFoundProps {
  message?: string;
  onRetry?: () => void;
}

export default function CertificateNotFound({ message, onRetry }: CertificateNotFoundProps) {
  return (
    <div className="bg-white rounded-xl shadow-lg border border-red-100 p-8 md:p-12 text-center max-w-2xl mx-auto">
      <div className="mb-6 inline-flex p-4 bg-red-50 rounded-full">
        <XCircle className="w-16 h-16 text-red-500" />
      </div>
      
      <h2 className="text-3xl font-bold text-slate-900 mb-4">
        We could not verify this certificate
      </h2>
      
      <p className="text-slate-600 text-lg mb-4 leading-relaxed">
        {message ||
          'The Certificate ID or link may be incorrect, or the certificate may not be publicly accessible on the issuer\'s site.'}
      </p>
      <p className="text-slate-500 text-sm mb-8">
        Check the details and try again, or upload a different file.
      </p>

      <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
        {onRetry && (
          <button 
            onClick={onRetry}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-lg transition-colors"
          >
            <RotateCcw className="w-5 h-5" />
            Try Again
          </button>
        )}
        
        <Link 
          href="/"
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors shadow-md hover:shadow-lg"
        >
          <Home className="w-5 h-5" />
          Back to Home
        </Link>
      </div>
    </div>
  );
}
