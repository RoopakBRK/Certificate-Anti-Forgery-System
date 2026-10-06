'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Menu, X } from 'lucide-react';
import Seal from '@/components/ui/Seal';
import UserMenu from '@/components/auth/UserMenu';

const NAV_ITEMS = [
  { label: 'Verify', href: '/#verify' },
  { label: 'How it works', href: '/#how-it-works' },
  { label: 'Issuers', href: '/issuers' },
  { label: 'Pricing', href: '/#pricing' },
  { label: 'FAQ', href: '/#faq' },
];

export default function Navbar() {
  const [isOpen, setIsOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 12);
    handleScroll();
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Close the mobile menu with Escape
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setIsOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen]);

  return (
    <nav
      aria-label="Main"
      className={`fixed inset-x-0 top-0 z-50 transition-colors duration-300 ${
        scrolled || isOpen ? 'border-b border-navy-100 bg-paper/90 backdrop-blur-md' : 'bg-transparent'
      }`}
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Wordmark */}
          <Link href="/" className="flex items-center gap-2.5" aria-label="CAFS home">
            <Seal size={34} />
            <span className="flex flex-col leading-none">
              <span className="font-display text-xl font-semibold tracking-tight text-navy-900">CAFS</span>
              <span className="hidden text-[10px] font-medium uppercase tracking-[0.16em] text-navy-500 sm:block">
                Certificate Anti Forgery System
              </span>
            </span>
          </Link>

          {/* Desktop navigation */}
          <div className="hidden items-center gap-8 md:flex">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                className="text-sm font-medium text-navy-600 transition-colors hover:text-navy-900"
              >
                {item.label}
              </Link>
            ))}
            <UserMenu />
            <Link href="/#verify" className="btn-primary px-5 py-2.5">
              Verify now
            </Link>
          </div>

          {/* Mobile menu button */}
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="rounded-lg p-2 text-navy-900 transition-colors hover:bg-navy-50 md:hidden"
            aria-label="Toggle menu"
            aria-expanded={isOpen}
            aria-controls="mobile-menu"
          >
            {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {/* Mobile navigation */}
      {isOpen && (
        <div id="mobile-menu" className="space-y-1 border-t border-navy-100 bg-paper px-4 pb-4 pt-2 md:hidden">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className="block rounded-lg px-3 py-3 font-medium text-navy-700 transition-colors hover:bg-navy-50"
              onClick={() => setIsOpen(false)}
            >
              {item.label}
            </Link>
          ))}
          <div className="px-3 py-3">
            <UserMenu onNavigate={() => setIsOpen(false)} />
          </div>
          <Link href="/#verify" className="btn-primary mt-2 w-full" onClick={() => setIsOpen(false)}>
            Verify now
          </Link>
        </div>
      )}
    </nav>
  );
}
