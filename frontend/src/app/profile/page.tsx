import { redirect } from 'next/navigation';
import Navbar from '@/components/ui/Navbar';
import UserProfile from '@/components/profile/UserProfile';
import { createClient } from '@/lib/supabase/server';
import type { CafsReport } from '@/types';

export const metadata = { title: 'My verifications - CAFS' };
export const dynamic = 'force-dynamic';

export default async function ProfilePage() {
  const supabase = createClient();
  if (!supabase) redirect('/login');

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect('/login?next=/profile');

  // RLS limits both queries to the signed-in user's own rows
  const [{ data: profile }, { data: reports, error }] = await Promise.all([
    supabase.from('profiles').select('full_name, avatar_url, plan, created_at').eq('id', user.id).maybeSingle(),
    supabase
      .from('cafs_reports')
      .select('id, mode, filename, final_verdict, candidate_name, certificate_id, issuer_name, verification_url, is_verified, is_high_risk, report_token, created_at')
      .order('created_at', { ascending: false })
      .limit(100),
  ]);

  return (
    <main className="min-h-screen">
      <Navbar />
      <div className="pt-24 md:pt-28">
        <UserProfile
          name={profile?.full_name || user.user_metadata?.full_name || user.email || 'Your account'}
          email={user.email ?? ''}
          avatarUrl={profile?.avatar_url || user.user_metadata?.avatar_url}
          plan={profile?.plan ?? 'free'}
          reports={(reports as CafsReport[] | null) ?? []}
          loadError={error ? 'Could not load your verification history.' : null}
        />
      </div>
    </main>
  );
}
