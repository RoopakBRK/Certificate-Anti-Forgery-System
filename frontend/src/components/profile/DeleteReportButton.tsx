'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Trash2 } from 'lucide-react';
import { createClient } from '@/lib/supabase/client';

/** Deletes one of the user's own reports (allowed by the cafs_reports RLS delete policy). */
export default function DeleteReportButton({ id }: { id: string }) {
  const [state, setState] = useState<'idle' | 'confirm' | 'busy' | 'error'>('idle');
  const router = useRouter();

  const remove = async () => {
    setState('busy');
    const { error } = (await createClient()?.from('cafs_reports').delete().eq('id', id)) ?? { error: true };
    if (error) {
      setState('error');
      return;
    }
    router.refresh();
  };

  if (state === 'confirm' || state === 'busy') {
    return (
      <span className="inline-flex items-center gap-2">
        <button onClick={remove} disabled={state === 'busy'} className="font-medium text-danger-700 hover:underline disabled:opacity-60">
          {state === 'busy' ? 'Deleting…' : 'Delete'}
        </button>
        <button onClick={() => setState('idle')} className="text-navy-500 hover:underline">
          Cancel
        </button>
      </span>
    );
  }
  return (
    <button
      onClick={() => setState('confirm')}
      className="text-navy-400 transition-colors hover:text-danger-700"
      aria-label="Delete this report"
      title={state === 'error' ? 'Could not delete. Try again.' : 'Delete from history'}
    >
      <Trash2 className="h-4 w-4" aria-hidden />
    </button>
  );
}
