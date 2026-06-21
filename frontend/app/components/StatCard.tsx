interface StatCardProps {
  label: string;
  value: number;
}

export default function StatCard({ label, value }: StatCardProps) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 hover:border-slate-700 transition-colors">
      <div className="text-3xl font-mono text-slate-100">{value}</div>
      <div className="text-slate-400 text-sm mt-1">{label}</div>
    </div>
  );
}
