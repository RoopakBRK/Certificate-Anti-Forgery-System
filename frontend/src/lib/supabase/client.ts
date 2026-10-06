import { createBrowserClient } from '@supabase/ssr';
import type { SupabaseClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

export const isAuthConfigured = Boolean(SUPABASE_URL && SUPABASE_KEY);

let browserClient: SupabaseClient | null = null;

/** Shared browser client (sessions live in cookies so the server can read them too). */
export function createClient(): SupabaseClient | null {
  if (!isAuthConfigured) return null;
  browserClient ??= createBrowserClient(SUPABASE_URL!, SUPABASE_KEY!);
  return browserClient;
}

/** Start Google sign-in; Supabase redirects back to /auth/callback. */
export async function signInWithGoogle(next = '/') {
  const supabase = createClient();
  if (!supabase) throw new Error('Sign-in is not configured.');
  const redirectTo = `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`;
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo, queryParams: { prompt: 'select_account' } },
  });
  if (error) throw error;
}

/** Access token for API calls, or null when signed out. */
export async function getAccessToken(): Promise<string | null> {
  const supabase = createClient();
  if (!supabase) return null;
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}
