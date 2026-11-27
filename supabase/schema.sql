-- LectureLens Supabase PostgreSQL Schema
-- Run this in Supabase Dashboard -> SQL Editor -> New Query

CREATE TABLE IF NOT EXISTS public.courses (
  id SERIAL PRIMARY KEY,
  code VARCHAR(32) NOT NULL UNIQUE,
  title VARCHAR(200) NOT NULL,
  created_at BIGINT NOT NULL DEFAULT (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT
);

CREATE TABLE IF NOT EXISTS public.sessions (
  id VARCHAR(64) PRIMARY KEY,
  course_id INTEGER REFERENCES public.courses(id) ON DELETE SET NULL,
  course_title VARCHAR(200) NOT NULL,
  topic VARCHAR(255) NOT NULL,
  date VARCHAR(32) NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'live' CHECK (status IN ('live', 'paused', 'ended')),
  language VARCHAR(16) NOT NULL DEFAULT 'id-ID',
  summary_md TEXT,
  polished_transcript_md TEXT,
  polish_status VARCHAR(24) NOT NULL DEFAULT 'idle' CHECK (polish_status IN ('idle', 'processing', 'ready', 'failed')),
  polish_provider VARCHAR(64),
  created_at BIGINT NOT NULL DEFAULT (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT,
  ended_at BIGINT
);

-- Non-destructive migration for existing deployments
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS polished_transcript_md TEXT;
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS polish_status VARCHAR(24) NOT NULL DEFAULT 'idle';
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS polish_provider VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_sessions_course_id ON public.sessions(course_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON public.sessions(status);

CREATE TABLE IF NOT EXISTS public.glossaries (
  id SERIAL PRIMARY KEY,
  session_id VARCHAR(64) NOT NULL REFERENCES public.sessions(id) ON DELETE CASCADE,
  term VARCHAR(160) NOT NULL,
  CONSTRAINT uq_glossary_session_term UNIQUE (session_id, term)
);

CREATE INDEX IF NOT EXISTS idx_glossaries_session_id ON public.glossaries(session_id);

CREATE TABLE IF NOT EXISTS public.transcripts (
  id SERIAL PRIMARY KEY,
  session_id VARCHAR(64) NOT NULL REFERENCES public.sessions(id) ON DELETE CASCADE,
  seq INTEGER NOT NULL,
  timestamp_ms BIGINT NOT NULL DEFAULT (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT,
  raw_text TEXT NOT NULL,
  processed_text TEXT NOT NULL,
  segments_json TEXT NOT NULL DEFAULT '[]',
  formulas_json TEXT NOT NULL DEFAULT '[]',
  glossary_matches_json TEXT NOT NULL DEFAULT '[]',
  is_unclear BOOLEAN NOT NULL DEFAULT FALSE,
  confidence DOUBLE PRECISION,
  language VARCHAR(16) NOT NULL DEFAULT 'id-ID',
  refined_by VARCHAR(32) NOT NULL DEFAULT 'rules',
  CONSTRAINT uq_transcript_session_seq UNIQUE (session_id, seq)
);

CREATE INDEX IF NOT EXISTS idx_transcripts_session_seq ON public.transcripts(session_id, seq);
