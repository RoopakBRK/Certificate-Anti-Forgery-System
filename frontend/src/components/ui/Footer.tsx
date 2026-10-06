import Link from 'next/link';
import Seal from '@/components/ui/Seal';

export default function Footer() {
  return (
    <footer className="bg-navy-950 text-navy-300">
      <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 py-12 sm:px-6 md:flex-row md:items-center md:justify-between lg:px-8">
        <div className="flex items-center gap-3">
          <Seal size={36} tone="navy" className="rounded-full ring-1 ring-navy-700" />
          <div>
            <p className="font-display text-lg font-semibold text-paper">CAFS</p>
            <p className="text-xs">Certificate Anti Forgery System</p>
          </div>
        </div>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-8 gap-y-3 text-sm">
          <Link href="/#verify" className="hover:text-paper">Verify</Link>
          <Link href="/#how-it-works" className="hover:text-paper">How it works</Link>
          <Link href="/#pricing" className="hover:text-paper">Pricing</Link>
          <Link href="/#faq" className="hover:text-paper">FAQ</Link>
        </nav>
        <p className="text-xs">© {new Date().getFullYear()} CAFS. All rights reserved.</p>
      </div>
    </footer>
  );
}
