'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import Button from '../../../../components/Button';
import Input from '../../../../components/Input';
import Textarea from '../../../../components/Textarea';
import Modal from '../../../../components/Modal';
import { useToast } from '../../../../components/Toast';
import { getShow, listEpisodes, updateEpisode, deleteEpisode, Episode, ShowDetail } from '../../../../lib/api';

export default function EpisodePage() {
  const router = useRouter();
  const params = useParams();
  const showId = params.showId as string;
  const episodeId = params.episodeId as string;
  const { showToast } = useToast();

  const [show, setShow] = useState<ShowDetail | null>(null);
  const [episode, setEpisode] = useState<Episode | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [title, setTitle] = useState('');
  const [scriptText, setScriptText] = useState('');

  const [deleteModal, setDeleteModal] = useState(false);

  useEffect(() => {
    load();
  }, [showId, episodeId]);

  async function load() {
    try {
      const [showData, episodesData] = await Promise.all([getShow(showId), listEpisodes(showId)]);
      setShow(showData);
      const ep = episodesData.find((e) => e.episode_id === episodeId);
      if (!ep) throw new Error('Episode not found');
      setEpisode(ep);
      setTitle(ep.title || '');
    } catch (err) {
      showToast((err as Error).message, 'error');
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(reChunk = false) {
    setSaving(true);
    try {
      await updateEpisode(showId, episodeId, { title, script_text: scriptText || undefined });
      showToast(reChunk ? 'Saved and re-chunking...' : 'Saved', 'success');
      load();
    } catch (err) {
      showToast((err as Error).message, 'error');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    try {
      await deleteEpisode(showId, episodeId);
      showToast('Episode deleted', 'success');
      router.push(`/shows/${showId}`);
    } catch (err) {
      showToast((err as Error).message, 'error');
    }
  }

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 h-32 animate-pulse" />
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 h-96 animate-pulse" />
      </div>
    );
  }

  if (!episode || !show) {
    return <div className="text-slate-400">Episode not found.</div>;
  }

  return (
    <div className="space-y-8">
      <div>
        <div className="text-slate-500 text-sm mb-2">
          <Link href="/shows" className="hover:text-amber-400 transition-colors">
            Shows
          </Link>
          {' / '}
          <Link href={`/shows/${showId}`} className="hover:text-amber-400 transition-colors">
            {show.title}
          </Link>
          {' / '}
          <span className="text-slate-400">
            S{String(episode.season).padStart(2, '0')}E{String(episode.episode).padStart(2, '0')}
          </span>
        </div>
        <h1 className="text-3xl font-semibold text-slate-100">
          S{String(episode.season).padStart(2, '0')}E{String(episode.episode).padStart(2, '0')}
          {episode.title && `: ${episode.title}`}
        </h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-4">
          <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Episode title" />
          <Textarea
            label="Script"
            value={scriptText}
            onChange={(e) => setScriptText(e.target.value)}
            placeholder="Paste screenplay text..."
            rows={30}
            className="font-mono text-sm h-[70vh]"
          />
        </div>

        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-slate-100 mb-4">Info</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Chunks</span>
                <span className="text-slate-100 font-mono">{episode.chunk_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Script</span>
                <span className="text-slate-100">{episode.script_present ? 'Present ✓' : 'Not present'}</span>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <Button onClick={() => handleSave(false)} disabled={saving} className="w-full">
              Save
            </Button>
            <Button variant="secondary" onClick={() => handleSave(true)} disabled={saving} className="w-full">
              Save & Re-chunk
            </Button>
          </div>

          <div className="pt-4 border-t border-slate-800">
            <Button variant="destructive" onClick={() => setDeleteModal(true)} className="w-full">
              Delete Episode
            </Button>
          </div>
        </div>
      </div>

      <Modal isOpen={deleteModal} onClose={() => setDeleteModal(false)} title="Delete Episode">
        <div className="space-y-4">
          <p className="text-slate-300">
            Delete S{String(episode.season).padStart(2, '0')}E{String(episode.episode).padStart(2, '0')}?
          </p>
          <div className="flex gap-2 pt-2">
            <Button variant="destructive" onClick={handleDelete}>
              Delete
            </Button>
            <Button variant="secondary" onClick={() => setDeleteModal(false)}>
              Cancel
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
