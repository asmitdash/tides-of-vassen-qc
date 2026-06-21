'use client';

import { useEffect, useState } from 'react';
import StatCard from '../components/StatCard';
import { listShows } from '../lib/api';

export default function Dashboard() {
  const [stats, setStats] = useState({ shows: 0, episodes: 0, chunks: 0, flags: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const shows = await listShows();
        const episodes = shows.reduce((sum, s) => sum + s.episode_count, 0);
        const chunks = shows.reduce((sum, s) => sum + s.chunk_count, 0);
        setStats({ shows: shows.length, episodes, chunks, flags: 0 });
      } catch (err) {
        console.error('Failed to load stats:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold text-slate-100">Overview</h1>
        <p className="text-slate-400 mt-1">Project state at a glance</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-slate-900 border border-slate-800 rounded-lg p-6 h-24 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard label="Shows" value={stats.shows} />
          <StatCard label="Episodes" value={stats.episodes} />
          <StatCard label="Chunks" value={stats.chunks} />
          <StatCard label="Flags" value={stats.flags} />
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-lg p-8">
        <h2 className="text-lg font-semibold text-slate-100 mb-2">Recent Activity</h2>
        <p className="text-slate-400 text-sm">No recent runs yet — use the QC Demo to generate flags.</p>
      </div>
    </div>
  );
}
