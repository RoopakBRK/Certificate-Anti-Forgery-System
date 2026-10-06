import { Upload, ScanSearch, FileSearch, Globe } from "lucide-react";
import type React from "react";

interface HowItWorksProps extends React.HTMLAttributes<HTMLElement> {}

// Mirrors the backend pipeline in backend/app/main.py (/verify)
const STEPS = [
  {
    icon: Upload,
    title: "Upload",
    description: "Drop in a PDF, PNG, JPG or WebP up to 10 MB. For PDFs, the first page is checked.",
  },
  {
    icon: ScanSearch,
    title: "Forensic scan",
    description: "Error-level analysis looks for regions that were pasted in or edited after the certificate was issued.",
  },
  {
    icon: FileSearch,
    title: "Read the details",
    description: "OCR and an AI model pull out the holder's name, the certificate ID and the issuer.",
  },
  {
    icon: Globe,
    title: "Confirm with issuer",
    description: "We open the issuer's own verification page and check that the ID and name match.",
  },
];

export const HowItWorks: React.FC<HowItWorksProps> = ({ className = "", ...props }) => (
  <section id="how-it-works" className={`bg-navy-900 py-20 text-paper sm:py-28 ${className}`} {...props}>
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl">
        <p className="eyebrow text-gold-400">How it works</p>
        <h2 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
          Four checks. One clear verdict.
        </h2>
        <p className="mt-4 text-lg text-navy-200">
          A forged certificate has to fool every step. Most fail at the first or the last.
        </p>
      </div>

      <ol className="mt-14 grid gap-px overflow-hidden rounded-2xl border border-navy-700 bg-navy-700 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map(({ icon: Icon, title, description }, i) => (
          <li key={title} className="bg-navy-900 p-7">
            <div className="flex items-center justify-between">
              <Icon className="h-6 w-6 text-gold-400" aria-hidden />
              <span className="font-display text-3xl text-navy-600">0{i + 1}</span>
            </div>
            <h3 className="mt-8 text-lg font-semibold text-white">{title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-navy-300">{description}</p>
          </li>
        ))}
      </ol>

      <div className="mt-10 grid gap-4 text-sm sm:grid-cols-3">
        {[
          ["Verified", "Clean scan and matched on the issuer's site.", "bg-verified-600"],
          ["Unverified", "Couldn't be confirmed. Try the manual check.", "bg-warn-600"],
          ["Flagged", "Signs of editing found. Don't rely on it.", "bg-danger-600"],
        ].map(([label, text, dot]) => (
          <div key={label} className="flex items-start gap-3 rounded-xl border border-navy-700 p-4">
            <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${dot}`} aria-hidden />
            <p>
              <span className="font-semibold text-white">{label}.</span>{" "}
              <span className="text-navy-300">{text}</span>
            </p>
          </div>
        ))}
      </div>
    </div>
  </section>
);
