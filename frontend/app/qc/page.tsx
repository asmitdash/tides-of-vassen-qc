'use client';

import { useEffect, useState } from 'react';
import Button from '../components/Button';
import Select from '../components/Select';
import Textarea from '../components/Textarea';
import FlagCard from '../components/FlagCard';
import Modal from '../components/Modal';
import { useToast } from '../components/Toast';
import { listShows, listEpisodes, streamFlags, runFlagsSync, runRecap, recordFeedback, Show, Episode, Flag, Recap } from '../lib/api';

type Surface = 'writers_room' | 'qc';

export default function QCDemo() {
  const { showToast } = useToast();

  const [shows, setShows] = useState<Show[]>([]);
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [selectedShow, setSelectedShow] = useState('');
  const [selectedEpisode, setSelectedEpisode] = useState(1);
  const [surface, setSurface] = useState<Surface>('writers_room');
  const [draftText, setDraftText] = useState('');

  const [flags, setFlags] = useState<Flag[]>([]);
  const [streaming, setStreaming] = useState(false);

  const [recap, setRecap] = useState<Recap | null>(null);
  const [recapOpen, setRecapOpen] = useState(false);
  const [recapLoading, setRecapLoading] = useState(false);

  useEffect(() => {
    loadShows();
  }, []);

  useEffect(() => {
    if (selectedShow) {
      loadEpisodes(selectedShow);
    }
  }, [selectedShow]);

  async function loadShows() {
    try {
      const data = await listShows();
      setShows(data);
      const tidesShow = data.find((s) => s.show_id === 'tides-of-vassen');
      if (tidesShow) setSelectedShow(tidesShow.show_id);
      else if (data.length > 0) setSelectedShow(data[0].show_id);
    } catch (err) {
      showToast('Failed to load shows', 'error');
    }
  }

  async function loadEpisodes(showId: string) {
    try {
      const data = await listEpisodes(showId);
      setEpisodes(data);
      if (data.length > 0) {
        setSelectedEpisode(data[0].episode);
      }
    } catch (err) {
      showToast('Failed to load episodes', 'error');
    }
  }

  async function handleRunPlotHoleCheck() {
    if (!draftText.trim() || !selectedShow) return;

    setFlags([]);
    setStreaming(true);

    if (surface === 'writers_room') {
      await streamFlags(
        {
          show_id: selectedShow,
          draft_episode: selectedEpisode,
          draft_text: draftText,
          surface,
        },
        (flag) => setFlags((prev) => [...prev, flag]),
        () => {
          setStreaming(false);
          showToast('Streaming complete', 'success');
        },
        (err) => {
          setStreaming(false);
          showToast(err.message, 'error');
        }
      );
    } else {
      try {
        const data = await runFlagsSync({
          show_id: selectedShow,
          draft_episode: selectedEpisode,
          draft_text: draftText,
          surface,
        });
        setFlags(data);
        showToast('Check complete', 'success');
      } catch (err) {
        showToast((err as Error).message, 'error');
      } finally {
        setStreaming(false);
      }
    }
  }

  async function handleGenerateRecap() {
    if (!draftText.trim() || !selectedShow) return;

    setRecapLoading(true);
    try {
      const data = await runRecap({
        show_id: selectedShow,
        draft_episode: selectedEpisode,
        surface,
      });
      setRecap(data);
      setRecapOpen(true);
      showToast('Recap generated', 'success');
    } catch (err) {
      showToast((err as Error).message, 'error');
    } finally {
      setRecapLoading(false);
    }
  }

  async function handleFeedback(flag: Flag, action: 'accept' | 'reject' | 'intentional') {
    try {
      await recordFeedback({ flag_id: flag.flag_id, user_action: action });
      showToast(`Marked as ${action}`, 'success');
    } catch (err) {
      showToast((err as Error).message, 'error');
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-slate-100">QC Demo</h1>
        <p className="text-slate-400 mt-1">Test plot-hole detection and recap generation</p>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Select
            label="Show"
            value={selectedShow}
            onChange={(e) => setSelectedShow(e.target.value)}
          >
            {shows.map((show) => (
              <option key={show.show_id} value={show.show_id}>
                {show.title}
              </option>
            ))}
          </Select>

          <Select
            label="Episode"
            value={selectedEpisode}
            onChange={(e) => setSelectedEpisode(parseInt(e.target.value))}
          >
            {episodes.map((ep) => (
              <option key={ep.episode_id} value={ep.episode}>
                S{String(ep.season).padStart(2, '0')}E{String(ep.episode).padStart(2, '0')}
                {ep.title && ` - ${ep.title}`}
              </option>
            ))}
          </Select>

          <div className="space-y-1">
            <label className="block text-sm font-medium text-slate-300">Surface</label>
            <div className="flex bg-slate-950 border border-slate-700 rounded-md p-1">
              <button
                onClick={() => setSurface('writers_room')}
                className={`flex-1 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  surface === 'writers_room'
                    ? 'bg-amber-400 text-slate-950'
                    : 'text-slate-400 hover:text-slate-100'
                }`}
              >
                Writers Room
              </button>
              <button
                onClick={() => setSurface('qc')}
                className={`flex-1 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  surface === 'qc' ? 'bg-amber-400 text-slate-950' : 'text-slate-400 hover:text-slate-100'
                }`}
              >
                QC
              </button>
            </div>
          </div>

          <div className="flex items-end gap-2">
            <Button onClick={handleRunPlotHoleCheck} disabled={streaming || !draftText.trim()} className="flex-1">
              Run Check
            </Button>
          </div>
        </div>

        <Button variant="secondary" onClick={handleGenerateRecap} disabled={recapLoading || !draftText.trim()}>
          Generate Recap
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3">
          <Textarea
            label="Draft Scene"
            value={draftText}
            onChange={(e) => setDraftText(e.target.value)}
            placeholder="Paste your draft scene here..."
            rows={30}
            className="font-mono text-sm h-[70vh]"
          />
        </div>

        <div className="lg:col-span-2">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="block text-sm font-medium text-slate-300">Flags</label>
              {streaming && (
                <div className="h-1 w-24 bg-slate-800 rounded overflow-hidden">
                  <div className="h-full bg-amber-400 animate-pulse" />
                </div>
              )}
            </div>
            <div className="h-[70vh] overflow-y-auto space-y-3 pr-2">
              {flags.length === 0 && !streaming && (
                <p className="text-slate-500 text-sm">No flags yet. Run a check to start.</p>
              )}
              {flags.map((flag) => (
                <FlagCard key={flag.flag_id} flag={flag} onFeedback={(action) => handleFeedback(flag, action)} />
              ))}
            </div>
          </div>
        </div>
      </div>

      {recapOpen && recap && (
        <Modal isOpen={recapOpen} onClose={() => setRecapOpen(false)} title="Generated Recap">
          <div className="space-y-6">
            <div>
              <h3 className="text-sm font-medium text-slate-400 mb-2">Primary Recap</h3>
              <p className="text-slate-100 leading-relaxed whitespace-pre-wrap">{recap.recap_text}</p>
              <div className="flex gap-4 mt-3 text-xs text-slate-500">
                <span>{recap.word_count} words</span>
                <span>Target: {recap.target_word_count}</span>
                <span>Voice: {recap.voice_match_self_score.toFixed(2)}</span>
              </div>
            </div>

            {recap.alternates && recap.alternates.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-slate-400 mb-3">Alternates</h3>
                <div className="space-y-2">
                  {recap.alternates.map((alt, idx) => (
                    <details key={idx} className="bg-slate-950 border border-slate-700 rounded p-3">
                      <summary className="cursor-pointer text-sm font-medium text-slate-300 hover:text-slate-100">
                        {alt.delta_label}
                      </summary>
                      <p className="text-slate-300 text-sm mt-2 leading-relaxed whitespace-pre-wrap">{alt.text}</p>
                    </details>
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

            {recap.threads_set_up_for_next && recap.threads_set_up_for_next.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-slate-400 mb-2">Threads for Next Episode</h3>
                <ul className="list-disc list-inside text-slate-300 text-sm space-y-1">
                  {recap.threads_set_up_for_next.map((thread, idx) => (
                    <li key={idx}>{thread}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
