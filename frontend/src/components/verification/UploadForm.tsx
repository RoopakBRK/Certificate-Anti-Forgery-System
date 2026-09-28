'use client';

import React, { useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { UploadCloud, File as FileIcon, Loader2, XCircle } from 'lucide-react';
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
    <div className="w-full max-w-md mx-auto bg-white rounded-xl shadow-lg border border-slate-200 p-6">
      
      {/* Upload Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200 cursor-pointer
          ${isDragging ? 'border-orange-500 bg-orange-50' : 'border-slate-300 hover:border-slate-400'}
          ${file ? 'bg-slate-50' : ''}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          id="certificate-upload"
          aria-label="Upload a certificate (PDF, PNG, JPG or WebP)"
          aria-describedby={error ? 'upload-error' : undefined}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          onChange={handleFileChange}
          accept=".pdf,.png,.jpg,.jpeg,.webp"
          disabled={isUploading}
        />

        <div className="flex flex-col items-center justify-center space-y-3 pointer-events-none">
          {file ? (
            <>
              <FileIcon className="w-10 h-10 text-orange-600" />
              <div className="text-sm text-slate-700 font-medium truncate max-w-[200px]">
                {file.name}
              </div>
              <p className="text-xs text-slate-500">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </>
          ) : (
            <>
              <UploadCloud className="w-10 h-10 text-slate-400" />
              <div className="text-slate-600">
                <span className="font-semibold text-orange-600">Click to upload</span> or drag and drop
              </div>
              <p className="text-xs text-slate-500">PDF, PNG, JPG, WebP (Max {MAX_SIZE_MB}MB). For PDFs, only the first page is checked.</p>
            </>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div id="upload-error" role="alert" className="mt-4 p-3 bg-red-50 text-red-600 text-sm rounded-md flex items-center gap-2 border border-red-200">
          <XCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Action Button */}
      <button
        onClick={handleVerification}
        disabled={!file || isUploading}
        className={`
          w-full mt-6 flex items-center justify-center py-3 px-4 rounded-lg font-semibold text-white transition-all
          ${!file || isUploading 
            ? 'bg-slate-300 cursor-not-allowed' 
            : 'bg-orange-600 hover:bg-orange-700 shadow-md hover:shadow-lg active:scale-95'
          }
        `}
      >
        {isUploading ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Processing...
          </>
        ) : (
          'Verify Certificate'
        )}
      </button>
    </div>
  );
}