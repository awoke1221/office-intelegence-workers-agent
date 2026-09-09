-- 1. Upgrade documents table for BGE-M3 (1024-dim)
ALTER TABLE documents ALTER COLUMN embedding TYPE vector(1024)
  USING embedding::text::vector(1024);

-- Re-create the HNSW index for faster search at 1024 dims
DROP INDEX IF EXISTS documents_embedding_idx;
CREATE INDEX documents_embedding_idx ON documents
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- 2. Agent sessions table (for MemoryManager long-term summaries)
CREATE TABLE IF NOT EXISTS agent_sessions (
  session_id    TEXT PRIMARY KEY,
  summary_text  TEXT NOT NULL DEFAULT '',
  event_count   INTEGER NOT NULL DEFAULT 0,
  entity_index  JSONB NOT NULL DEFAULT '{}',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER agent_sessions_updated_at
  BEFORE UPDATE ON agent_sessions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- 3. Code executions audit table (for ReportBuilder)
CREATE TABLE IF NOT EXISTS code_executions (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id    TEXT REFERENCES agent_sessions(session_id) ON DELETE SET NULL,
  code_hash     TEXT NOT NULL,
  code_text     TEXT NOT NULL,
  executed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  success       BOOLEAN NOT NULL,
  stdout_preview TEXT,
  duration_ms   INTEGER,
  blocked_by    TEXT
);

CREATE INDEX IF NOT EXISTS code_executions_session_idx ON code_executions (session_id);
CREATE INDEX IF NOT EXISTS code_executions_hash_idx ON code_executions (code_hash);

-- 4. Tool audit log table (for MCPManager)
CREATE TABLE IF NOT EXISTS tool_audit_log (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id    TEXT,
  tool_name     TEXT NOT NULL,
  args_summary  JSONB NOT NULL DEFAULT '{}',
  status        TEXT NOT NULL,
  duration_ms   INTEGER,
  error_msg     TEXT,
  executed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS tool_audit_session_idx ON tool_audit_log (session_id);
CREATE INDEX IF NOT EXISTS tool_audit_tool_idx ON tool_audit_log (tool_name, executed_at);

-- 5. Row-level security (enable but allow service role full access)
ALTER TABLE agent_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE code_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "service_role_all" ON agent_sessions FOR ALL TO service_role USING (true);
CREATE POLICY IF NOT EXISTS "service_role_all" ON code_executions FOR ALL TO service_role USING (true);
CREATE POLICY IF NOT EXISTS "service_role_all" ON tool_audit_log FOR ALL TO service_role USING (true);
