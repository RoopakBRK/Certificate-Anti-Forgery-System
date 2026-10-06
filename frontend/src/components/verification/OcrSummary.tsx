import { AlertTriangle, ScanText } from 'lucide-react';
import type { OCRFieldAgreement, OCRReport } from '@/types';
import { cn } from '@/lib/utils';

const ENGINE_LABEL: Record<string, string> = {
  tesseract: 'Tesseract',
  paddle: 'PaddleOCR',
  easyocr: 'EasyOCR',
  mistral: 'Mistral OCR',
  pdf_text: 'PDF text layer',
  qr: 'QR code',
};

function Agreement({ label, field, sources }: { label: string; field: OCRFieldAgreement; sources: number }) {
  if (!field.value) return null;
  const strong = field.votes >= 2;
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-2">
      <dt className="text-sm text-navy-500">{label}</dt>
      <dd className={cn('text-sm font-medium', strong ? 'text-verified-700' : 'text-warn-700')}>
        Read identically by {field.votes} of {sources}
        {field.engines.length > 0 && (
          <span className="font-normal text-navy-500"> ({field.engines.map((e) => ENGINE_LABEL[e] ?? e).join(', ')})</span>
        )}
      </dd>
    </div>
  );
}

/** How the parallel OCR engines agreed on the fields used for verification. */
export default function OcrSummary({ ocr }: { ocr?: OCRReport | null }) {
  if (!ocr) return null;
  const ran = ocr.engines.filter((e) => e.name !== 'pdf_text' || e.ok);

  return (
    <section aria-label="OCR cross-check" className="card mt-6 p-6">
      <div className="flex items-center gap-2">
        <ScanText className="h-5 w-5 text-navy-500" aria-hidden />
        <h3 className="font-display text-lg font-semibold text-navy-900">OCR cross-check</h3>
      </div>
      <p className="mt-1 text-sm text-navy-600">
        {ran.length} OCR engines read the document in parallel; fields are accepted when independent engines agree.
        {ocr.mode === 'heuristic' && ' (AI structuring was unavailable, so fields were taken from the OCR layout.)'}
      </p>

      <ul className="mt-4 flex flex-wrap gap-2">
        {ran.map((e) => (
          <li
            key={e.name}
            className={cn(
              'rounded-full border px-2.5 py-1 text-xs font-medium',
              e.ok ? 'border-navy-200 bg-navy-50 text-navy-700' : 'border-danger-200 bg-danger-50 text-danger-700',
            )}
            title={e.error ?? `${e.chars} characters in ${e.seconds}s`}
          >
            {ENGINE_LABEL[e.name] ?? e.name} {e.ok ? '✓' : '✗'}
          </li>
        ))}
        {ocr.qr_codes.length > 0 && (
          <li className="rounded-full border border-navy-200 bg-navy-50 px-2.5 py-1 text-xs font-medium text-navy-700">QR code ✓</li>
        )}
      </ul>

      <dl className="mt-4 divide-y divide-dashed divide-navy-100">
        <Agreement label="Certificate ID" field={ocr.certificate_id} sources={ocr.sources} />
        <Agreement label="Holder's name" field={ocr.candidate_name} sources={ocr.sources} />
      </dl>

      {ocr.warnings.length > 0 && (
        <ul className="mt-4 space-y-2">
          {ocr.warnings.map((w) => (
            <li key={w} className="flex items-start gap-2 rounded-lg border border-warn-200 bg-warn-50 p-3 text-sm text-warn-800">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
              {w}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
