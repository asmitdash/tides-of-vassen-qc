import Link from 'next/link';
import Button from './Button';

interface ShowCardProps {
  showId: string;
  title: string;
  tagline: string;
  onDelete: () => void;
}

export default function ShowCard({ showId, title, tagline, onDelete }: ShowCardProps) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 hover:border-slate-700 transition-colors">
      <h3 className="text-lg font-semibold text-slate-100">{title}</h3>
      <p className="text-slate-400 text-sm mt-2">{tagline}</p>
      <div className="flex items-center justify-between mt-4">
        <Link href={`/shows/${showId}`} className="text-amber-400 hover:text-amber-300 text-sm font-medium">
          Open →
        </Link>
        <button
          onClick={(e) => {
            e.preventDefault();
            onDelete();
          }}
          className="text-slate-500 hover:text-red-400 transition-colors"
          aria-label="Delete show"
        >
          <TrashIcon className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}

function TrashIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
      <path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14z" />
      <path d="M10 11v6M14 11v6" />
    </svg>
  );
}
