'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Button from '../components/Button';
import ShowCard from '../components/ShowCard';
import Drawer from '../components/Drawer';
import Input from '../components/Input';
import Textarea from '../components/Textarea';
import Modal from '../components/Modal';
import { useToast } from '../components/Toast';
import { listShows, createShow, deleteShow, Show } from '../lib/api';

export default function Shows() {
  const router = useRouter();
  const { showToast } = useToast();
  const [shows, setShows] = useState<Show[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteModal, setDeleteModal] = useState<{ open: boolean; show?: Show }>({ open: false });
  const [confirmText, setConfirmText] = useState('');

  const [formData, setFormData] = useState({
    title: '',
    logline: '',
    tone: '',
    world_rules: '',
    season_count: 1,
    episode_count: 0,
  });

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      const data = await listShows();
      setShows(data);
    } catch (err) {
      showToast('Failed to load shows', 'error');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!formData.title.trim()) {
      showToast('Title is required', 'error');
      return;
    }
    try {
      const worldRules = formData.world_rules
        .split('\n')
        .map((r) => r.trim())
        .filter(Boolean);
      const { show_id } = await createShow({
        title: formData.title,
        logline: formData.logline || undefined,
        tone: formData.tone || undefined,
        world_rules: worldRules.length > 0 ? worldRules : undefined,
        season_count: formData.season_count,
        episode_count: formData.episode_count,
      });
      showToast('Show created', 'success');
      setCreateOpen(false);
      setFormData({ title: '', logline: '', tone: '', world_rules: '', season_count: 1, episode_count: 0 });
      router.push(`/shows/${show_id}`);
    } catch (err) {
      showToast((err as Error).message, 'error');
    }
  }

  async function handleDelete() {
    if (!deleteModal.show || confirmText !== deleteModal.show.title) return;
    try {
      await deleteShow(deleteModal.show.show_id);
      showToast('Show deleted', 'success');
      setDeleteModal({ open: false });
      setConfirmText('');
      load();
    } catch (err) {
      showToast((err as Error).message, 'error');
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-semibold text-slate-100">Shows</h1>
        <Button onClick={() => setCreateOpen(true)}>+ New Show</Button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-slate-900 border border-slate-800 rounded-lg p-6 h-40 animate-pulse" />
          ))}
        </div>
      ) : shows.length === 0 ? (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <p className="text-slate-400 text-lg">No shows yet. Create your first show to begin.</p>
            <Button onClick={() => setCreateOpen(true)} className="mt-4">
              + New Show
            </Button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {shows.map((show) => (
            <ShowCard
              key={show.show_id}
              showId={show.show_id}
              title={show.title}
              tagline={`${show.episode_count} episodes · ${show.chunk_count} chunks`}
              onDelete={() => setDeleteModal({ open: true, show })}
            />
          ))}
        </div>
      )}

      <Drawer isOpen={createOpen} onClose={() => setCreateOpen(false)} title="New Show">
        <div className="space-y-4">
          <Input
            label="Title"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            placeholder="Show title"
            required
          />
          <Textarea
            label="Logline"
            value={formData.logline}
            onChange={(e) => setFormData({ ...formData, logline: e.target.value })}
            placeholder="Short description"
            rows={3}
          />
          <Input
            label="Tone"
            value={formData.tone}
            onChange={(e) => setFormData({ ...formData, tone: e.target.value })}
            placeholder="e.g. dark, whimsical"
          />
          <Textarea
            label="World Rules"
            value={formData.world_rules}
            onChange={(e) => setFormData({ ...formData, world_rules: e.target.value })}
            placeholder="One rule per line"
            rows={5}
          />
          <Input
            label="Season Count"
            type="number"
            value={formData.season_count}
            onChange={(e) => setFormData({ ...formData, season_count: parseInt(e.target.value) || 1 })}
            min={1}
          />
          <Input
            label="Episode Count"
            type="number"
            value={formData.episode_count}
            onChange={(e) => setFormData({ ...formData, episode_count: parseInt(e.target.value) || 0 })}
            min={0}
          />
          <div className="flex gap-2 pt-4">
            <Button onClick={handleCreate}>Create</Button>
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
          </div>
        </div>
      </Drawer>

      <Modal isOpen={deleteModal.open} onClose={() => setDeleteModal({ open: false })} title="Delete Show">
        <div className="space-y-4">
          <p className="text-slate-300">
            Type <span className="font-mono text-amber-400">{deleteModal.show?.title}</span> to confirm deletion.
          </p>
          <Input value={confirmText} onChange={(e) => setConfirmText(e.target.value)} placeholder="Show title" />
          <div className="flex gap-2 pt-2">
            <Button variant="destructive" onClick={handleDelete} disabled={confirmText !== deleteModal.show?.title}>
              Delete
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setDeleteModal({ open: false });
                setConfirmText('');
              }}
            >
              Cancel
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
