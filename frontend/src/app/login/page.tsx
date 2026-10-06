import Link from 'next/link';
import { redirect } from 'next/navigation';
import Navbar from '@/components/ui/Navbar';
import Seal from '@/components/ui/Seal';
import GoogleSignInButton from '@/components/auth/GoogleSignInButton';
import { createClient } from '@/lib/supabase/server';

export const metadata = { title: 'Sign in - CAFS' };

function safeNext(value?: string) {
  return value && value.startsWith('/') && !value.startsWith('//') ? value : '/profile';
}

export default async function LoginPage({ searchParams }: { searchParams: { next?: string; error?: string } }) {
  const next = safeNext(searchParams.next);
  const supabase = createClient();
  if (supabase) {
    const { data } = await supabase.auth.getUser();
    if (data.user) redirect(next);
  }

  return (
    <>
      <Navbar />
      <main className="flex min-h-screen items-center justify-center px-4 pb-16 pt-28">
        <div className="card w-full max-w-md p-8 text-center sm:p-10">
          <Seal size={56} className="mx-auto" />
          <h1 className="mt-5 font-display text-3xl font-semibold tracking-tight text-navy-900">Sign in to CAFS</h1>
          <p className="mt-2 text-navy-600">
            Keep a history of every certificate you check and share signed reports from your profile.
          </p>

          {searchParams.error && (
            <p role="alert" className="mt-6 rounded-lg border border-danger-200 bg-danger-50 p-3 text-sm text-danger-800">
              {searchParams.error}
            </p>
          )}

          <div className="mt-8">
            <GoogleSignInButton next={next} />
          </div>

          <p className="mt-6 text-xs text-navy-500">
            You can still verify certificates without an account.{' '}
            <Link href="/#verify" className="font-medium text-navy-800 underline underline-offset-4">
              Verify now
            </Link>
          </p>
        </div>
      </main>
    </>
  );
}
