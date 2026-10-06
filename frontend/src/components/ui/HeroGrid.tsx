"use client";
import React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, ScanSearch, FileText, Globe } from "lucide-react";
import Seal from "@/components/ui/Seal";

interface HeroGridProps {
  onVerifyClick?: () => void;
}

const STATS = [
  { icon: ScanSearch, value: "Forensic", label: "tamper analysis" },
  { icon: FileText, value: "PDF + image", label: "formats accepted" },
  { icon: Globe, value: "Live", label: "issuer-site check" },
];

export const HeroGrid: React.FC<HeroGridProps> = ({ onVerifyClick }) => {
  const reduce = useReducedMotion();
  const rise = (delay: number) =>
    reduce
      ? {}
      : { initial: { opacity: 0, y: 16 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.5, delay } };

  const scrollToVerify = () => {
    if (onVerifyClick) return onVerifyClick();
    document.getElementById("verify")?.scrollIntoView({ behavior: reduce ? "auto" : "smooth" });
  };

  return (
    <section className="guilloche relative overflow-hidden pt-28 pb-20 md:pt-36 md:pb-28">
      {/* soft fade so the texture sits behind the content */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-paper/0 via-paper/60 to-paper" aria-hidden />

      <div className="relative mx-auto grid max-w-7xl items-center gap-14 px-4 sm:px-6 lg:grid-cols-[1.1fr_0.9fr] lg:px-8">
        {/* Left: message */}
        <div>
          <motion.p {...rise(0)} className="eyebrow mb-5 flex items-center gap-2">
            <span className="inline-block h-px w-8 bg-gold-500" /> Certificate Anti Forgery System
          </motion.p>

          <motion.h1
            {...rise(0.05)}
            className="font-display text-[2.6rem] font-semibold leading-[1.05] tracking-tight text-navy-900 sm:text-6xl lg:text-[4.25rem]"
          >
            Know a certificate is real <em className="font-normal italic text-verified-700">before</em> you trust it.
          </motion.h1>

          <motion.p {...rise(0.1)} className="mt-6 max-w-xl text-lg leading-relaxed text-navy-600">
            CAFS scans the document for signs of editing, reads its name and ID, and confirms them on the
            issuer&apos;s own verification page. You get a verdict in seconds and a signed report you can share.
          </motion.p>

          <motion.div {...rise(0.15)} className="mt-9 flex flex-col gap-3 sm:flex-row">
            <button onClick={scrollToVerify} className="btn-primary px-7 py-3.5 text-base">
              Verify a certificate <ArrowRight className="h-4 w-4" />
            </button>
            <a href="#pricing" className="btn-secondary px-7 py-3.5 text-base">
              For HR teams
            </a>
          </motion.div>

          <motion.dl {...rise(0.2)} className="mt-12 grid max-w-lg grid-cols-3 gap-6 border-t border-navy-100 pt-6">
            {STATS.map(({ icon: Icon, value, label }) => (
              <div key={label}>
                <dt className="sr-only">{label}</dt>
                <dd>
                  <Icon className="mb-2 h-5 w-5 text-navy-400" aria-hidden />
                  <div className="font-display text-lg font-semibold text-navy-900 sm:text-xl">{value}</div>
                  <div className="text-xs text-navy-500 sm:text-sm">{label}</div>
                </dd>
              </div>
            ))}
          </motion.dl>
        </div>

        {/* Right: sample report */}
        <motion.div
          {...(reduce ? {} : { initial: { opacity: 0, y: 24, rotate: -1 }, animate: { opacity: 1, y: 0, rotate: 0 }, transition: { duration: 0.7, delay: 0.15 } })}
          className="relative mx-auto w-full max-w-md"
          aria-hidden
        >
          <div className="absolute -inset-4 -z-10 rotate-2 rounded-3xl bg-navy-900/5" />
          <div className="card overflow-hidden shadow-lift">
            <div className="flex items-center justify-between bg-navy-900 px-6 py-4 text-paper">
              <span className="text-xs font-semibold uppercase tracking-[0.18em]">Verification report</span>
              <span className="font-mono text-xs text-navy-300">#CAFS-2F9A</span>
            </div>
            <div className="relative px-6 pb-6 pt-7">
              <Seal tone="verified" mark="check" size={78} className="absolute right-5 top-5 rotate-[-8deg]" />
              <p className="eyebrow">Issued to</p>
              <p className="mt-1 font-display text-2xl text-navy-900">Ananya Sharma</p>

              <dl className="mt-6 space-y-4 text-sm">
                {[
                  ["Credential", "Machine Learning Specialization"],
                  ["Issuer", "Coursera"],
                  ["Certificate ID", "ALS76DHQNMVZ"],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-4 border-b border-dashed border-navy-100 pb-3">
                    <dt className="text-navy-500">{k}</dt>
                    <dd className={`text-right font-medium text-navy-900 ${k === "Certificate ID" ? "font-mono text-xs" : ""}`}>{v}</dd>
                  </div>
                ))}
              </dl>

              <div className="mt-6 grid grid-cols-2 gap-3 text-xs">
                <div className="rounded-lg bg-verified-50 px-3 py-2.5 text-verified-800">
                  <div className="font-semibold">No tampering found</div>
                  <div className="opacity-75">Forensic scan</div>
                </div>
                <div className="rounded-lg bg-verified-50 px-3 py-2.5 text-verified-800">
                  <div className="font-semibold">Matched on issuer</div>
                  <div className="opacity-75">coursera.org/verify</div>
                </div>
              </div>
            </div>
          </div>
          <p className="mt-3 text-center text-xs text-navy-400">Sample report</p>
        </motion.div>
      </div>
    </section>
  );
};
