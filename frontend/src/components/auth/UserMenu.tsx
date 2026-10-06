'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import type { User } from '@supabase/supabase-js';
import { LogOut, UserRound } from 'lucide-react';
import { createClient, isAuthConfigured } from '@/lib/supabase/client';

function initials(user: User) {
  const name: string = user.user_metadata?.full_name || user.email || '?';
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('');
}

/** Current Supabase user, kept in sync with sign-in / sign-out in any tab. */
export function useUser() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(isAuthConfigured);

  useEffect(() => {
    const supabase = createClient();
    if (!supabase) return;
    supabase.auth.getUser().then(({ data }) => {
      setUser(data.user);
      setLoading(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => setUser(session?.user ?? null));
    return () => sub.subscription.unsubscribe();
  }, []);

  return { user, loading };
}

export default function UserMenu({ onNavigate }: { onNavigate?: () => void }) {
  const { user, loading } = useUser();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => !menuRef.current?.contains(e.target as Node) && setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', esc);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', esc);
    };
  }, [open]);

  if (!isAuthConfigured || loading) return null;

  if (!user) {
    return (
      <Link href="/login" onClick={onNavigate} className="text-sm font-medium text-navy-600 transition-colors hover:text-navy-900">
        Sign in
      </Link>
    );
  }

  const signOut = async () => {
    await createClient()?.auth.signOut();
    setOpen(false);
    onNavigate?.();
    router.push('/');
    router.refresh();
  };

  const avatar: string | undefined = user.user_metadata?.avatar_url || user.user_metadata?.picture;

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-full border border-navy-200 bg-navy-50 text-xs font-semibold text-navy-800"
        aria-label="Account menu"
        aria-expanded={open}
        aria-haspopup="menu"
      >
        {avatar ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={avatar} alt="" className="h-full w-full object-cover" referrerPolicy="no-referrer" />
        ) : (
          initials(user)
        )}
      </button>
      {open && (
        <div role="menu" className="card absolute right-0 mt-2 w-60 overflow-hidden p-1.5 text-sm">
          <div className="px-3 py-2">
            <p className="truncate font-medium text-navy-900">{user.user_metadata?.full_name || 'Signed in'}</p>
            <p className="truncate text-xs text-navy-500">{user.email}</p>
          </div>
          <Link
            href="/profile"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              onNavigate?.();
            }}
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-navy-700 hover:bg-navy-50"
          >
            <UserRound className="h-4 w-4" /> My verifications
          </Link>
          <button role="menuitem" onClick={signOut} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-navy-700 hover:bg-navy-50">
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}
