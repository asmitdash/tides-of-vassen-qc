'use client';

interface EpisodeSelectorProps {
  selected: number;
  onChange: (episode: number) => void;
}

export default function EpisodeSelector({ selected, onChange }: EpisodeSelectorProps) {
  const episodes = [1, 2, 3, 4, 5];

  return (
    <div className="flex gap-2">
      {episodes.map((ep) => (
        <button
          key={ep}
          onClick={() => onChange(ep)}
          className={`px-4 py-2 rounded border transition-colors ${
            selected === ep
              ? 'bg-slate-700 border-slate-600 text-slate-100'
              : 'bg-slate-900 border-slate-700 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
          }`}
        >
          Episode {ep}
        </button>
      ))}
    </div>
  );
}
