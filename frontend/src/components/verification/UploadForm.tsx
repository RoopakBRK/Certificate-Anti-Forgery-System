'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { UploadCloud, File as FileIcon, Loader2, XCircle, Check, ShieldCheck } from 'lucide-react';
import { verificationService } from '@/services/api';

const MAX_SIZE_MB = 10; // keep in sync with backend MAX_UPLOAD_BYTES
const VALID_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.webp'];
const VALID_TYPES = ['application/pdf', 'image/png', 'image/jpeg', 'image/webp'];

export default function UploadForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Handle Drag Events
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  // Handle File Input
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
    // Allow re-selecting the same file after an error
    e.target.value = '';
  };

  const validateAndSetFile = (selectedFile: File) => {
    // Some browsers report an empty MIME type, so fall back to the extension.
    // (The server re-checks the real file contents.)
    const name = selectedFile.name.toLowerCase();
    const typeOk = selectedFile.type ? VALID_TYPES.includes(selectedFile.type) : VALID_EXTENSIONS.some((ext) => name.endsWith(ext));
    if (!typeOk) {
      setError('Invalid file type. Please upload a PDF, PNG, JPG or WebP file.');
      return;
    }
    
    if (selectedFile.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`File size exceeds ${MAX_SIZE_MB}MB. Please upload a smaller file.`);
      return;
    }
    
    setFile(selectedFile);
    setError(null);
  };

  // Handle Submission
  const handleVerification = async () => {
    if (!file) return;

    setIsUploading(true);
    setError(null);

    try {
      const data = await verificationService.uploadCertificate(file);
      
      // Hand the result to the results page (sessionStorage can be unavailable, e.g. private mode)
      try {
        sessionStorage.setItem('verificationResult', JSON.stringify(data));
      } catch {
        setError('Your browser blocked temporary storage, so the result cannot be shown. Please disable private mode and try again.');
        setIsUploading(false);
        return;
      }
      
      router.push('/verify-result');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong connecting to the server.');
      setIsUploading(false);
    }
  };

  return (
    <div className="card w-full p-6 sm:p-8">
      {isUploading ? (
        <ProgressStages />
      ) : (
        <>
          {/* Upload area */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`relative cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-colors ${
              isDragging
                ? 'border-navy-500 bg-navy-50'
                : file
                  ? 'border-verified-200 bg-verified-50/50'
                  : 'border-navy-200 hover:border-navy-400 hover:bg-navy-50/50'
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              id="certificate-upload"
              aria-label="Upload a certificate (PDF, PNG, JPG or WebP)"
              aria-describedby={error ? 'upload-error' : undefined}
              className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
              onChange={handleFileChange}
              accept=".pdf,.png,.jpg,.jpeg,.webp"
              disabled={isUploading}
            />

            <div className="pointer-events-none flex flex-col items-center justify-center gap-3">
              {file ? (
                <>
                  <FileIcon className="h-10 w-10 text-verified-600" />
                  <div className="max-w-[240px] truncate text-sm font-medium text-navy-900">{file.name}</div>
                  <p className="text-xs text-navy-500">{(file.size / 1024 / 1024).toFixed(2)} MB · click to change</p>
                </>
              ) : (
                <>
                  <UploadCloud className="h-10 w-10 text-navy-300" />
                  <div className="text-navy-700">
                    <span className="font-semibold text-navy-900 underline underline-offset-4">Choose a file</span> or drag it here
                  </div>
                  <p className="text-xs text-navy-500">
                    PDF, PNG, JPG or WebP, up to {MAX_SIZE_MB} MB. For PDFs, the first page is checked.
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div id="upload-error" role="alert" className="mt-4 flex items-start gap-2 rounded-lg border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">
              <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          <button onClick={handleVerification} disabled={!file} className="btn-primary mt-6 w-full py-3.5 text-base">
            <ShieldCheck className="h-5 w-5" />
            Verify certificate
          </button>
          <p className="mt-3 text-center text-xs text-navy-400">Your file is checked in memory and never stored.</p>
        </>
      )}
    </div>
  );
}

// The server does these steps in order; timings are typical, not reported live.
const STAGES = [
  { label: 'Scanning for signs of editing', after: 0 },
  { label: 'Reading name, ID and issuer', after: 4 },
  { label: "Checking the issuer's verification page", after: 9 },
  { label: 'Preparing your report', after: 20 },
];

function ProgressStages() {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const current = STAGES.reduce((idx, st, i) => (elapsed >= st.after ? i : idx), 0);

  return (
    <div role="status" aria-live="polite" className="py-4">
      <p className="font-display text-2xl font-semibold text-navy-900">Verifying your certificate</p>
      <p className="mt-1 text-sm text-navy-500">This usually takes 15–30 seconds. Please keep this page open.</p>
      <ol className="mt-8 space-y-4">
        {STAGES.map((st, i) => {
          const done = i < current;
          const active = i === current;
          return (
            <li key={st.label} className="flex items-center gap-3 text-sm">
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
                  done ? 'bg-verified-600 text-white' : active ? 'bg-navy-900 text-white' : 'bg-navy-100 text-navy-400'
                }`}
              >
                {done ? <Check className="h-3.5 w-3.5" /> : active ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <span className="text-[10px] font-semibold">{i + 1}</span>}
              </span>
              <span className={done || active ? 'font-medium text-navy-900' : 'text-navy-400'}>{st.label}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
