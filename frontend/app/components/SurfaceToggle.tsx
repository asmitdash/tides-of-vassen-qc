'use client';

type Surface = 'writers_room' | 'qc';

interface SurfaceToggleProps {
  selected: Surface;
  onChange: (surface: Surface) => void;
}

export default function SurfaceToggle({ selected, onChange }: SurfaceToggleProps) {
  return (
    <div className="inline-flex rounded border border-slate-700 bg-slate-900">
      <button
        onClick={() => onChange('writers_room')}
        className={`px-4 py-2 rounded-l transition-colors ${
          selected === 'writers_room'
            ? 'bg-slate-700 text-slate-100'
            : 'text-slate-400 hover:text-slate-200'
        }`}
      >
        Writers Room
      </button>
      <button
        onClick={() => onChange('qc')}
        className={`px-4 py-2 rounded-r transition-colors ${
          selected === 'qc'
            ? 'bg-slate-700 text-slate-100'
            : 'text-slate-400 hover:text-slate-200'
        }`}
      >
        QC
      </button>
    </div>
  );
}
