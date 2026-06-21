'use client';

import FlagCard from './FlagCard';
import { Flag } from '../lib/api';

interface StreamingFlagsProps {
  flags: Flag[];
  streaming: boolean;
  onFeedback: (flag: Flag, action: 'accept' | 'reject' | 'intentional') => void;
}

export default function StreamingFlags({ flags, streaming, onFeedback }: StreamingFlagsProps) {
  return (
    <div className="space-y-3">
      {streaming && (
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
          Streaming...
        </div>
      )}

      {flags.length === 0 && !streaming && (
        <div className="text-center text-slate-500 py-12">
          No flags yet. Run a plot-hole check to see results here.
        </div>
      )}

      {flags.map((flag) => (
        <FlagCard key={flag.flag_id} flag={flag} onFeedback={(action) => onFeedback(flag, action)} />
      ))}
    </div>
  );
}
