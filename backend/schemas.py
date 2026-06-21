from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


# Line ranges may arrive as either a 2-tuple list [start, end], a single int,
# or a string like "12-15". We accept all and normalize at consumption time.
LineRange = Union[List[int], int, str]


class Claim(BaseModel):
    claim_id: str
    claim_text: str
    scene_id: str = ""
    line_range: Optional[LineRange] = None
    claim_type: str
    entities: List[str] = Field(default_factory=list)


class CanonCitation(BaseModel):
    episode: Union[int, str]
    scene: Optional[Union[int, str]] = None
    line_range: Optional[LineRange] = None
    verbatim_quote: str


class Evidence(BaseModel):
    canon_citation: Optional[CanonCitation] = None
    draft_citation: Optional[Dict[str, Any]] = None


class Flag(BaseModel):
    flag_id: Optional[str] = None
    severity: str
    flag_type: str
    summary: str
    evidence: Evidence
    reasoning_trace: Dict[str, Any] = Field(default_factory=dict)
    verifier_outcome: Optional[str] = None
    self_consistency: Dict[str, Any] = Field(default_factory=dict)
    surfaced: bool = True


class Recap(BaseModel):
    recap_text: str
    word_count: int
    target_word_count: int
    scenes_referenced: List[Dict[str, Any]] = Field(default_factory=list)
    threads_set_up_for_next: List[Dict[str, Any]] = Field(default_factory=list)
    voice_match_self_score: float
    alternates: List[Dict[str, Any]] = Field(default_factory=list)


class RecapRequest(BaseModel):
    show_id: str
    draft_episode: int
    surface: str = "qc"


class FlagRequest(BaseModel):
    show_id: str
    draft_episode: int
    draft_text: str
    surface: str = Field(..., pattern="^(writers_room|qc)$")


class FeedbackRequest(BaseModel):
    flag_id: str
    user_action: str = Field(..., pattern="^(accept|reject|explain)$")
    user_explanation: str = ""


# CRUD schemas
class CreateShowRequest(BaseModel):
    title: str
    logline: Optional[str] = None
    tone: Optional[str] = None
    voice_card: Optional[Dict[str, Any]] = None
    world_rules: Optional[List[str]] = None
    season_count: int = 1
    episode_count: int = 0


class ShowSummary(BaseModel):
    show_id: str
    title: str
    episode_count: int
    chunk_count: int
    created: str


class ShowDetail(BaseModel):
    show_id: str
    title: str
    logline: Optional[str] = None
    tone: Optional[str] = None
    voice_card: Optional[Dict[str, Any]] = None
    world_rules: Optional[List[str]] = None
    season_count: int
    episode_count: int
    chunk_count: int
    episode_count_actual: int
    has_bible: bool
    character_count: int
    last_ingested_at: Optional[str] = None


class CreateEpisodeRequest(BaseModel):
    season: int = 1
    episode: int
    title: Optional[str] = None
    script_text: Optional[str] = None


class UpdateEpisodeRequest(BaseModel):
    title: Optional[str] = None
    script_text: Optional[str] = None


class EpisodeSummary(BaseModel):
    episode_id: str
    season: int
    episode: int
    title: Optional[str] = None
    script_present: bool
    chunk_count: int


class BibleResponse(BaseModel):
    bible_text: Optional[str] = None


class BibleUpdateRequest(BaseModel):
    bible_text: str


class CreateCharacterRequest(BaseModel):
    name: str
    sheet_text: str


class UpdateCharacterRequest(BaseModel):
    name: Optional[str] = None
    sheet_text: Optional[str] = None


class CharacterSummary(BaseModel):
    character_id: str
    name: str
    sheet_text: str


class IngestResponse(BaseModel):
    chunks_total: int
    facts_extracted: int
    episodes_ingested: int
    took_ms: int
