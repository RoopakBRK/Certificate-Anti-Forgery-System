import type { Metadata } from 'next';
import { Suspense } from 'react';
import ValidationView from './ValidationView';

export const metadata: Metadata = {
  title: 'Verification Report - CAFS (Certificate Anti Forgery System)',
  robots: { index: false, follow: false },
};

export default function ValidationCertificatePage() {
  return (
    <Suspense fallback={null}>
      <ValidationView />
    </Suspense>
  );
}
