import React from 'react';
import UploadForm from '@/components/verification/UploadForm';
import Navbar from '@/components/ui/Navbar';
import { HeroGrid } from '@/components/ui/HeroGrid';
import { HowItWorks } from '@/components/ui/HowItWorks';
import SupportedIssuers from '@/components/ui/SupportedIssuers';
import Pricing from '@/components/ui/Pricing';
import FAQ from '@/components/ui/FAQ';
import Footer from '@/components/ui/Footer';

export default function LandingPage() {
  return (
    <>
      <Navbar />
      <main>
        <HeroGrid />
        <SupportedIssuers />

        {/* Verify */}
        <section id="verify" className="py-20 sm:py-28">
          <div className="mx-auto grid max-w-7xl items-start gap-12 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
            <div className="lg:pt-6">
              <p className="eyebrow">Start verification</p>
              <h2 className="mt-3 font-display text-4xl font-semibold tracking-tight text-navy-900 sm:text-5xl">
                Upload a certificate.
              </h2>
              <p className="mt-4 max-w-md text-lg text-navy-600">
                Results take about 20 seconds. The file is checked in memory and never stored.
              </p>
              <ul className="mt-8 space-y-3 text-sm text-navy-700">
                <li>• Works with Coursera, Udemy, edX, NPTEL, LinkedIn Learning, Credly and <a href="/issuers" className="underline underline-offset-4">70+ issuers</a></li>
                <li>• Verified results come with a signed link and QR code to share</li>
                <li>• Couldn&apos;t be matched automatically? You can confirm the ID by hand</li>
              </ul>
            </div>
            <UploadForm />
          </div>
        </section>

        <HowItWorks />
        <Pricing />
        <FAQ />
      </main>
      <Footer />
    </>
  );
}
