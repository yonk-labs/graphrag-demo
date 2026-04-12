CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    doc_type TEXT NOT NULL CHECK (doc_type IN (
        'meeting_note', 'architecture_doc', 'incident_report', 'decision_record'
    )),
    author_id TEXT NOT NULL,
    project_id TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    embedding vector(384)
);

CREATE INDEX idx_documents_embedding ON documents
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);

CREATE INDEX idx_documents_author ON documents (author_id);
CREATE INDEX idx_documents_project ON documents (project_id);
CREATE INDEX idx_documents_doc_type ON documents (doc_type);
