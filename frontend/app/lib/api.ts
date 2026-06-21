const BASE = '/api/backend';

async function fetcher<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    const text = await res.text();
    let msg = `HTTP ${res.status}`;
    try {
      const json = JSON.parse(text);
      msg = json.error || json.message || msg;
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

export interface Show {
  show_id: string;
  title: string;
  episode_count: number;
  chunk_count: number;
  created: string;
}

export interface ShowDetail {
  show_id: string;
  title: string;
  logline?: string;
  tone?: string;
  voice_card?: object;
  world_rules?: string[];
  season_count?: number;
  episode_count?: number;
  chunk_count: number;
  episode_count_actual: number;
  has_bible: boolean;
  character_count: number;
  last_ingested_at?: string;
}

export interface Episode {
  episode_id: string;
  season: number;
  episode: number;
  title?: string;
  script_present: boolean;
  chunk_count: number;
}

export interface Character {
  character_id: string;
  name: string;
  sheet_text: string;
}

export interface Flag {
  flag_id: string;
  severity: 'HARD_CONTRADICTION' | 'SOFT_INCONSISTENCY' | 'INTERNAL_LOGIC_BREAK' | 'WORLDBUILDING_DRIFT' | 'INTENTIONAL_TENSION';
  flag_type: string;
  summary: string;
  reasoning_trace: string;
  evidence: {
    canon_citation?: {
      verbatim: string;
      episode?: number;
      scene?: string;
      lines?: string;
    };
    draft_citation?: {
      lines_range: string;
    };
  };
  verifier_outcome?: string;
  self_consistency?: object;
}

export interface Recap {
  recap_text: string;
  word_count: number;
  target_word_count: number;
  scenes_referenced: string[];
  threads_set_up_for_next: string[];
  voice_match_self_score: number;
  alternates: Array<{
    text: string;
    delta_label: string;
  }>;
}

export async function listShows(): Promise<Show[]> {
  return fetcher('/shows');
}

export async function createShow(params: {
  title: string;
  logline?: string;
  tone?: string;
  voice_card?: object;
  world_rules?: string[];
  season_count?: number;
  episode_count?: number;
}): Promise<{ show_id: string; title: string }> {
  return fetcher('/shows', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
}

export async function getShow(showId: string): Promise<ShowDetail> {
  return fetcher(`/shows/${showId}`);
}

export async function deleteShow(showId: string): Promise<{ ok: boolean }> {
  return fetcher(`/shows/${showId}`, { method: 'DELETE' });
}

export async function listEpisodes(showId: string): Promise<Episode[]> {
  return fetcher(`/shows/${showId}/episodes`);
}

export async function createEpisode(
  showId: string,
  params: { season: number; episode: number; title?: string; script_text?: string }
): Promise<Episode> {
  return fetcher(`/shows/${showId}/episodes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
}

export async function updateEpisode(
  showId: string,
  episodeId: string,
  params: { title?: string; script_text?: string }
): Promise<Episode> {
  return fetcher(`/shows/${showId}/episodes/${episodeId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
}

export async function deleteEpisode(showId: string, episodeId: string): Promise<{ ok: boolean }> {
  return fetcher(`/shows/${showId}/episodes/${episodeId}`, { method: 'DELETE' });
}

export async function getBible(showId: string): Promise<{ bible_text: string | null }> {
  return fetcher(`/shows/${showId}/bible`);
}

export async function setBible(showId: string, bibleText: string): Promise<{ ok: boolean }> {
  return fetcher(`/shows/${showId}/bible`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bible_text: bibleText }),
  });
}

export async function listCharacters(showId: string): Promise<Character[]> {
  return fetcher(`/shows/${showId}/characters`);
}

export async function createCharacter(
  showId: string,
  params: { name: string; sheet_text: string }
): Promise<Character> {
  return fetcher(`/shows/${showId}/characters`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
}

export async function updateCharacter(
  showId: string,
  characterId: string,
  params: { name?: string; sheet_text?: string }
): Promise<Character> {
  return fetcher(`/shows/${showId}/characters/${characterId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
}

export async function deleteCharacter(showId: string, characterId: string): Promise<{ ok: boolean }> {
  return fetcher(`/shows/${showId}/characters/${characterId}`, { method: 'DELETE' });
}

export async function ingest(showId: string): Promise<{
  chunks_total: number;
  facts_extracted: number;
  episodes_ingested: number;
  took_ms: number;
}> {
  return fetcher(`/shows/${showId}/ingest`, { method: 'POST' });
}

export async function runFlagsSync(params: {
  show_id: string;
  draft_episode: number;
  draft_text: string;
  surface: 'writers_room' | 'qc';
}): Promise<Flag[]> {
  return fetcher('/flag-claims', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
}

export async function streamFlags(
  params: {
    show_id: string;
    draft_episode: number;
    draft_text: string;
    surface: 'writers_room' | 'qc';
  },
  onFlag: (flag: Flag) => void,
  onComplete: () => void,
  onError: (err: Error) => void
): Promise<void> {
  try {
    const res = await fetch(`${BASE}/stream-flags`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error('No reader');

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim();
          if (data) {
            try {
              const flag = JSON.parse(data);
              onFlag(flag);
            } catch (e) {
              console.error('Parse SSE error:', e);
            }
          }
        }
      }
    }

    onComplete();
  } catch (err) {
    onError(err as Error);
  }
}

export async function runRecap(params: {
  show_id: string;
  draft_episode: number;
  surface: 'writers_room' | 'qc';
}): Promise<Recap> {
  return fetcher('/recap', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
}

export async function recordFeedback(params: {
  flag_id: string;
  user_action: 'accept' | 'reject' | 'intentional';
  user_explanation?: string;
}): Promise<{ ok: boolean }> {
  return fetcher('/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
}
