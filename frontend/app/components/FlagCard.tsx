'use client';

import { useState } from 'react';
import Badge from './Badge';
import Button from './Button';
import { Flag } from '../lib/api';

interface FlagCardProps {
  flag: Flag;
  onFeedback: (action: 'accept' | 'reject' | 'intentional') => void;
}

export default function FlagCard({ flag, onFeedback }: FlagCardProps) {
  const [expanded, setExpanded] = useState(false);

  const severityMap: Record<Flag['severity'], { variant: 'error' | 'warning' | 'info' | 'default'; label: string }> = {
    HARD_CONTRADICTION: { variant: 'error', label: 'Hard' },
    SOFT_INCONSISTENCY: { variant: 'warning', label: 'Soft' },
    INTERNAL_LOGIC_BREAK: { variant: 'info', label: 'Logic' },
    WORLDBUILDING_DRIFT: { variant: 'info', label: 'Worldbuilding' },
    INTENTIONAL_TENSION: { variant: 'default', label: 'Intentional' },
  };

  const severity = severityMap[flag.severity];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant={severity.variant}>{severity.label}</Badge>
          <Badge variant="default">{flag.flag_type}</Badge>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-slate-500 hover:text-slate-300 transition-colors"
          aria-label={expanded ? 'Collapse' : 'Expand'}
        >
          <ChevronIcon className={`w-5 h-5 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </button>
      </div>

      <p className="text-slate-100 text-sm">{flag.summary}</p>

      {expanded && (
        <div className="space-y-3 pt-2 border-t border-slate-800">
          <div>
            <h4 className="text-xs font-medium text-slate-400 mb-1">Reasoning</h4>
            <p className="text-slate-300 text-sm">{flag.reasoning_trace}</p>
          </div>

          {flag.evidence.canon_citation && (
            <div>
              <h4 className="text-xs font-medium text-slate-400 mb-1">Canon Evidence</h4>
              <div className="bg-slate-950 border border-slate-700 rounded p-3">
                <p className="font-mono text-xs text-slate-300">{flag.evidence.canon_citation.verbatim}</p>
                <p className="text-slate-500 text-xs mt-2">
                  Episode {flag.evidence.canon_citation.episode} · {flag.evidence.canon_citation.scene} ·{' '}
                  {flag.evidence.canon_citation.lines}
                </p>
              </div>
            </div>
          )}

          {flag.evidence.draft_citation && (
            <div>
              <h4 className="text-xs font-medium text-slate-400 mb-1">Draft Citation</h4>
              <p className="text-slate-400 text-xs">Lines: {flag.evidence.draft_citation.lines_range}</p>
            </div>
          )}

          {flag.verifier_outcome && (
            <div>
              <h4 className="text-xs font-medium text-slate-400 mb-1">Verifier Outcome</h4>
              <p className="text-slate-300 text-sm">{flag.verifier_outcome}</p>
            </div>
          )}

          {flag.self_consistency && (
            <details className="text-xs">
              <summary className="cursor-pointer text-slate-400 hover:text-slate-300">Self-consistency JSON</summary>
              <pre className="bg-slate-950 border border-slate-700 rounded p-2 mt-2 text-slate-300 overflow-x-auto">
                {JSON.stringify(flag.self_consistency, null, 2)}
              </pre>
            </details>
          )}
        </div>
      )}

      <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
        <Button variant="secondary" onClick={() => onFeedback('accept')} className="text-xs px-3 py-1.5">
          Accept
        </Button>
        <Button variant="secondary" onClick={() => onFeedback('reject')} className="text-xs px-3 py-1.5">
          Reject
        </Button>
        <Button variant="ghost" onClick={() => onFeedback('intentional')} className="text-xs">
          Mark Intentional
        </Button>
      </div>
    </div>
  );
}

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
      <path d="M19 9l-7 7-7-7" />
    </svg>
  );
}
