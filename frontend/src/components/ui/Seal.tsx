import React from 'react';

type Tone = 'navy' | 'verified' | 'warn' | 'danger';

const TONES: Record<Tone, { ring: string; fill: string; mark: string }> = {
  navy: { ring: '#0B1F3A', fill: '#0B1F3A', mark: '#FAF8F3' },
  verified: { ring: '#059669', fill: '#059669', mark: '#FFFFFF' },
  warn: { ring: '#D97706', fill: '#D97706', mark: '#FFFFFF' },
  danger: { ring: '#DC2626', fill: '#DC2626', mark: '#FFFFFF' },
};

interface SealProps {
  tone?: Tone;
  size?: number;
  /** check = verified, alert = flagged, question = unverified, shield = brand mark */
  mark?: 'check' | 'alert' | 'question' | 'shield';
  className?: string;
  label?: string;
}

// Scalloped outer edge, computed once. Rounded so server and browser render identical markup.
const POINTS = 24;
const OUTER = Array.from({ length: POINTS * 2 }, (_, i) => {
  const r = i % 2 === 0 ? 48 : 44;
  const a = (Math.PI * i) / POINTS;
  return `${(50 + r * Math.sin(a)).toFixed(2)},${(50 - r * Math.cos(a)).toFixed(2)}`;
}).join(' ');

/** A rosette-edged seal, like the embossed stamp on an official document. */
export default function Seal({ tone = 'navy', size = 48, mark = 'shield', className, label }: SealProps) {
  const c = TONES[tone];
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      className={className}
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <polygon points={OUTER}fill={c.fill} />
      <circle cx="50" cy="50" r="38" fill="none" stroke={c.mark} strokeOpacity="0.55" strokeWidth="1" />
      <circle cx="50" cy="50" r="34" fill="none" stroke={c.mark} strokeOpacity="0.35" strokeWidth="0.75" strokeDasharray="1.5 2" />
      {mark === 'check' && (
        <path d="M34 51 L45 62 L67 39" fill="none" stroke={c.mark} strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
      )}
      {mark === 'alert' && (
        <>
          <path d="M50 32 V56" stroke={c.mark} strokeWidth="6" strokeLinecap="round" />
          <circle cx="50" cy="67" r="3.8" fill={c.mark} />
        </>
      )}
      {mark === 'question' && (
        <>
          <path d="M40 41 a10 10 0 1 1 14 9 c-3 1.5 -4 3.5 -4 7" fill="none" stroke={c.mark} strokeWidth="5.5" strokeLinecap="round" />
          <circle cx="50" cy="68" r="3.6" fill={c.mark} />
        </>
      )}
      {mark === 'shield' && (
        <>
          <path d="M50 28 L68 35 V50 C68 61 60 69 50 73 C40 69 32 61 32 50 V35 Z" fill="none" stroke={c.mark} strokeWidth="3.5" strokeLinejoin="round" />
          <path d="M42 50 L48 56 L59 44" fill="none" stroke={c.mark} strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
        </>
      )}
    </svg>
  );
}
