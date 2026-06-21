'use client';

import { useState } from 'react';
import { Recap } from '../lib/api';

interface RecapPanelProps {
  recap: Recap;
  onClose: () => void;
}

export default function RecapPanel({ recap, onClose }: RecapPanelProps) {
  const [expandedAlternate, setExpandedAlternate] = useState<number | null>(null);

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-8">
      <div className="bg-slate-900 border border-slate-700 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-slate-900 border-b border-slate-700 p-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-slate-100">Generated Recap</h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 transition-colors"
            aria-label="Close"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div>
            <h3 className="text-sm font-medium text-slate-400 mb-2">Primary Recap</h3>
            <p className="text-slate-100 leading-relaxed whitespace-pre-wrap">{recap.recap_text}</p>
          </div>

          {recap.alternates && recap.alternates.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-slate-400 mb-3">Alternates</h3>
              <div className="space-y-2">
                {recap.alternates.map((alt, idx) => (
                  <div key={idx} className="border border-slate-700 rounded">
                    <button
                      onClick={() => setExpandedAlternate(expandedAlternate === idx ? null : idx)}
                      className="w-full p-3 flex items-center justify-between text-left hover:bg-slate-800 transition-colors"
                    >
                      <span className="text-sm text-slate-300">
                        <span className="font-medium text-slate-100">{alt.delta_label}</span>
                      </span>
                      <svg
                        className={`w-4 h-4 text-slate-400 transition-transform ${
                          expandedAlternate === idx ? 'rotate-180' : ''
                        }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    {expandedAlternate === idx && (
                      <div className="p-3 border-t border-slate-700 bg-slate-950">
                        <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">{alt.text}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {recap.scenes_referenced && recap.scenes_referenced.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-slate-400 mb-2">Scenes Referenced</h3>
              <div className="flex flex-wrap gap-2">
                {recap.scenes_referenced.map((scene, idx) => (
                  <span key={idx} className="text-xs px-2 py-1 bg-slate-800 border border-slate-700 rounded text-slate-300">
                    {scene}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
