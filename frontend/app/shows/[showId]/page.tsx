'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Tabs from '../../components/Tabs';
import Button from '../../components/Button';
import Drawer from '../../components/Drawer';
import Modal from '../../components/Modal';
import Input from '../../components/Input';
import Textarea from '../../components/Textarea';
import { useToast } from '../../components/Toast';
import {
  getShow,
  deleteShow,
  listEpisodes,
  createEpisode,
  deleteEpisode,
  getBible,
  setBible,
  listCharacters,
  createCharacter,
  updateCharacter,
  deleteCharacter,
  ingest,
  ShowDetail,
  Episode,
  Character,
} from '../../lib/api';

export default function ShowPage() {
  const router = useRouter();
  const params = useParams();
  const showId = params.showId as string;
  const { showToast } = useToast();

  const [show, setShow] = useState<ShowDetail | null>(null);
  const [activeTab, setActiveTab] = useState('episodes');
  const [loading, setLoading] = useState(true);

  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [episodesLoading, setEpisodesLoading] = useState(false);
  const [episodeDrawer, setEpisodeDrawer] = useState(false);
  const [episodeForm, setEpisodeForm] = useState({ season: 1, episode: 1, title: '', script_text: '' });

  const [bibleText, setBibleText] = useState('');
  const [bibleLoading, setBibleLoading] = useState(false);

  const [characters, setCharacters] = useState<Character[]>([]);
  const [charactersLoading, setCharactersLoading] = useState(false);
  const [characterDrawer, setCharacterDrawer] = useState(false);
  const [editingCharacter, setEditingCharacter] = useState<Character | null>(null);
  const [characterForm, setCharacterForm] = useState({ name: '', sheet_text: '' });

  const [deleteModal, setDeleteModal] = useState<{ open: boolean; type?: 'show' | 'episode' | 'character'; item?: any }>(
    { open: false }
  );
  const [confirmText, setConfirmText] = useState('');
  const [ingestResult, setIngestResult] = useState<any>(null);

  useEffect(() => {
    loadShow();
  }, [showId]);

  useEffect(() => {
    if (activeTab === 'episodes' && !episodesLoading && episodes.length === 0) loadEpisodes();
    if (activeTab === 'bible' && !bibleLoading && bibleText === '') loadBible();
    if (activeTab === 'characters' && !charactersLoading && characters.length === 0) loadCharacters();
  }, [activeTab]);

  async function loadShow() {
    try {
      const data = await getShow(showId);
      setShow(data);
    } catch (err) {
      showToast((err as Error).message, 'error');
    } finally {
      setLoading(false);
    }
  }

  async function loadEpisodes() {
    setEpisodesLoading(true);
    try {
      const data = await listEpisodes(showId);
      setEpisodes(data);
    } catch (err) {
      showToast((err as Error).message, 'error');
    } finally {
      setEpisodesLoading(false);
    }
  }

  async function handleCreateEpisode() {
    try {
      await createEpisode(showId, episodeForm);
      showToast('Episode created', 'success');
      setEpisodeDrawer(false);
      setEpisodeForm({ season: 1, episode: 1, title: '', script_text: '' });
      loadEpisodes();
    } catch (err) {
      showToast((err as Error).message, 'error');
    }
  }

  async function handleDeleteEpisode() {
    if (!deleteModal.item) return;
    try {
      await deleteEpisode(showId, deleteModal.item.episode_id);
      showToast('Episode deleted', 'success');
      setDeleteModal({ open: false });
      loadEpisodes();
    } catch (err) {
      showToast((err as Error).message, 'error');
    }
  }

  async function loadBible() {
    setBibleLoading(true);
    try {
      const data = await getBible(showId);
      setBibleText(data.bible_text || '');
    } catch (err) {
      showToast((err as Error).message, 'error');
    } finally {
      setBibleLoading(false);
    }
  }

  async function handleSaveBible() {
    try {
      await setBible(showId, bibleText);
      showToast('Bible saved', 'success');
    } catch (err) {
      showToast((err as Error).message, 'error');
    }
  }

  async function loadCharacters() {
    setCharactersLoading(true);
    try {
      const data = await listCharacters(showId);
      setCharacters(data);
    } catch (err) {
      showToast((err as Error).message, 'error');
    } finally {
      setCharactersLoading(false);
    }
  }

  async function handleSaveCharacter() {
    try {
      if (editingCharacter) {
        await updateCharacter(showId, editingCharacter.character_id, characterForm);
        showToast('Character updated', 'success');
      } else {
        await createCharacter(showId, characterForm);
        showToast('Character created', 'success');
      }
      setCharacterDrawer(false);
      setEditingCharacter(null);
      setCharacterForm({ name: '', sheet_text: '' });
      loadCharacters();
    } catch (err) {
      showToast((err as Error).message, 'error');
    }
  }

  async function handleDeleteCharacter() {
    if (!deleteModal.item) return;
    try {
      await deleteCharacter(showId, deleteModal.item.character_id);
      showToast('Character deleted', 'success');
      setDeleteModal({ open: false });
      loadCharacters();
    } catch (err) {
      showToast((err as Error).message, 'error');
    }
  }

  async function handleIngest() {
    try {
      const result = await ingest(showId);
      setIngestResult(result);
      showToast(`Ingested ${result.episodes_ingested} episodes`, 'success');
      loadShow();
    } catch (err) {
      showToast((err as Error).message, 'error');
    }
  }

  async function handleDeleteShow() {
    if (!show || confirmText !== show.title) return;
    try {
      await deleteShow(showId);
      showToast('Show deleted', 'success');
      router.push('/shows');
    } catch (err) {
      showToast((err as Error).message, 'error');
    }
  }

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 h-32 animate-pulse" />
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 h-64 animate-pulse" />
      </div>
    );
  }

  if (!show) {
    return <div className="text-slate-400">Show not found.</div>;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold text-slate-100">{show.title}</h1>
        <p className="text-slate-500 text-sm font-mono mt-1">Show ID: {show.show_id.slice(0, 8)}</p>
      </div>

      <Tabs
        tabs={[
          { id: 'episodes', label: 'Episodes' },
          { id: 'bible', label: 'Bible' },
          { id: 'characters', label: 'Characters' },
          { id: 'settings', label: 'Settings' },
        ]}
        activeTab={activeTab}
        onChange={setActiveTab}
      >
        {activeTab === 'episodes' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold text-slate-100">Episodes</h2>
              <Button onClick={() => setEpisodeDrawer(true)}>+ Add Episode</Button>
            </div>
            {episodesLoading ? (
              <div className="space-y-2">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="bg-slate-900 border border-slate-800 rounded-lg p-4 h-16 animate-pulse" />
                ))}
              </div>
            ) : episodes.length === 0 ? (
              <p className="text-slate-400">No episodes yet.</p>
            ) : (
              <div className="space-y-2">
                {episodes.map((ep) => (
                  <div
                    key={ep.episode_id}
                    className="bg-slate-900 border border-slate-800 rounded-lg p-4 hover:border-slate-700 transition-colors flex items-center justify-between"
                  >
                    <button
                      onClick={() => router.push(`/shows/${showId}/episodes/${ep.episode_id}`)}
                      className="flex-1 text-left flex items-center gap-4"
                    >
                      <span className="font-mono text-sm text-slate-400">
                        S{String(ep.season).padStart(2, '0')}E{String(ep.episode).padStart(2, '0')}
                      </span>
                      <span className="text-slate-100">{ep.title || 'Untitled'}</span>
                      <span className="text-slate-500 text-xs">{ep.chunk_count} chunks</span>
                      {ep.script_present && <span className="text-emerald-400 text-xs">script ✓</span>}
                    </button>
                    <button
                      onClick={() => setDeleteModal({ open: true, type: 'episode', item: ep })}
                      className="text-slate-500 hover:text-red-400 transition-colors"
                    >
                      <TrashIcon className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'bible' && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-slate-100">Show Bible</h2>
            {bibleLoading ? (
              <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 h-64 animate-pulse" />
            ) : (
              <>
                <Textarea
                  value={bibleText}
                  onChange={(e) => setBibleText(e.target.value)}
                  placeholder="Enter show bible content..."
                  rows={20}
                  className="font-mono text-sm"
                />
                <div className="flex items-center gap-4">
                  <Button onClick={handleSaveBible}>Save Bible</Button>
                  <span className="text-slate-500 text-sm">
                    {bibleText.split(/\s+/).filter(Boolean).length} words · {bibleText.length} chars
                  </span>
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === 'characters' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold text-slate-100">Characters</h2>
              <Button onClick={() => setCharacterDrawer(true)}>+ Add Character</Button>
            </div>
            {charactersLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="bg-slate-900 border border-slate-800 rounded-lg p-4 h-32 animate-pulse" />
                ))}
              </div>
            ) : characters.length === 0 ? (
              <p className="text-slate-400">No characters yet.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {characters.map((char) => (
                  <div
                    key={char.character_id}
                    className="bg-slate-900 border border-slate-800 rounded-lg p-4 hover:border-slate-700 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-semibold text-slate-100">{char.name}</h3>
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            setEditingCharacter(char);
                            setCharacterForm({ name: char.name, sheet_text: char.sheet_text });
                            setCharacterDrawer(true);
                          }}
                          className="text-slate-500 hover:text-amber-400 transition-colors"
                        >
                          <EditIcon className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setDeleteModal({ open: true, type: 'character', item: char })}
                          className="text-slate-500 hover:text-red-400 transition-colors"
                        >
                          <TrashIcon className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                    <p className="text-slate-400 text-sm line-clamp-3">{char.sheet_text.slice(0, 200)}...</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-slate-100 mb-2">Re-ingest Show</h3>
              <p className="text-slate-400 text-sm mb-4">
                Re-chunk all episodes and extract facts. This will update the knowledge base.
              </p>
              <Button onClick={handleIngest}>Run Ingestion</Button>
              {ingestResult && (
                <div className="mt-4 p-4 bg-slate-950 border border-slate-700 rounded text-sm font-mono">
                  <p className="text-slate-300">Chunks: {ingestResult.chunks_total}</p>
                  <p className="text-slate-300">Facts: {ingestResult.facts_extracted}</p>
                  <p className="text-slate-300">Episodes: {ingestResult.episodes_ingested}</p>
                  <p className="text-slate-500">Took: {ingestResult.took_ms}ms</p>
                </div>
              )}
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-red-400 mb-2">Delete Show</h3>
              <p className="text-slate-400 text-sm mb-4">
                Permanently delete this show and all its episodes, chunks, and characters.
              </p>
              <Button variant="destructive" onClick={() => setDeleteModal({ open: true, type: 'show' })}>
                Delete Show
              </Button>
            </div>
          </div>
        )}
      </Tabs>

      <Drawer isOpen={episodeDrawer} onClose={() => setEpisodeDrawer(false)} title="Add Episode">
        <div className="space-y-4">
          <Input
            label="Season"
            type="number"
            value={episodeForm.season}
            onChange={(e) => setEpisodeForm({ ...episodeForm, season: parseInt(e.target.value) || 1 })}
            min={1}
          />
          <Input
            label="Episode"
            type="number"
            value={episodeForm.episode}
            onChange={(e) => setEpisodeForm({ ...episodeForm, episode: parseInt(e.target.value) || 1 })}
            min={1}
          />
          <Input
            label="Title"
            value={episodeForm.title}
            onChange={(e) => setEpisodeForm({ ...episodeForm, title: e.target.value })}
            placeholder="Episode title"
          />
          <Textarea
            label="Script"
            value={episodeForm.script_text}
            onChange={(e) => setEpisodeForm({ ...episodeForm, script_text: e.target.value })}
            placeholder="Paste screenplay text..."
            rows={12}
            className="font-mono text-sm"
          />
          <div className="flex gap-2 pt-4">
            <Button onClick={handleCreateEpisode}>Create</Button>
            <Button variant="secondary" onClick={() => setEpisodeDrawer(false)}>
              Cancel
            </Button>
          </div>
        </div>
      </Drawer>

      <Drawer isOpen={characterDrawer} onClose={() => setCharacterDrawer(false)} title={editingCharacter ? 'Edit Character' : 'Add Character'}>
        <div className="space-y-4">
          <Input
            label="Name"
            value={characterForm.name}
            onChange={(e) => setCharacterForm({ ...characterForm, name: e.target.value })}
            placeholder="Character name"
          />
          <Textarea
            label="Character Sheet"
            value={characterForm.sheet_text}
            onChange={(e) => setCharacterForm({ ...characterForm, sheet_text: e.target.value })}
            placeholder="Background, traits, arc..."
            rows={12}
          />
          <div className="flex gap-2 pt-4">
            <Button onClick={handleSaveCharacter}>{editingCharacter ? 'Update' : 'Create'}</Button>
            <Button
              variant="secondary"
              onClick={() => {
                setCharacterDrawer(false);
                setEditingCharacter(null);
              }}
            >
              Cancel
            </Button>
          </div>
        </div>
      </Drawer>

      <Modal isOpen={deleteModal.open} onClose={() => setDeleteModal({ open: false })} title={`Delete ${deleteModal.type}`}>
        <div className="space-y-4">
          {deleteModal.type === 'show' ? (
            <>
              <p className="text-slate-300">
                Type <span className="font-mono text-amber-400">{show?.title}</span> to confirm deletion.
              </p>
              <Input value={confirmText} onChange={(e) => setConfirmText(e.target.value)} placeholder="Show title" />
              <div className="flex gap-2 pt-2">
                <Button variant="destructive" onClick={handleDeleteShow} disabled={confirmText !== show?.title}>
                  Delete
                </Button>
                <Button variant="secondary" onClick={() => setDeleteModal({ open: false })}>
                  Cancel
                </Button>
              </div>
            </>
          ) : deleteModal.type === 'episode' ? (
            <>
              <p className="text-slate-300">Delete this episode?</p>
              <div className="flex gap-2 pt-2">
                <Button variant="destructive" onClick={handleDeleteEpisode}>
                  Delete
                </Button>
                <Button variant="secondary" onClick={() => setDeleteModal({ open: false })}>
                  Cancel
                </Button>
              </div>
            </>
          ) : deleteModal.type === 'character' ? (
            <>
              <p className="text-slate-300">Delete {deleteModal.item?.name}?</p>
              <div className="flex gap-2 pt-2">
                <Button variant="destructive" onClick={handleDeleteCharacter}>
                  Delete
                </Button>
                <Button variant="secondary" onClick={() => setDeleteModal({ open: false })}>
                  Cancel
                </Button>
              </div>
            </>
          ) : null}
        </div>
      </Modal>
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

function EditIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  );
}
