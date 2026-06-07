-- T-064: job_embeddings + resume_embeddings (pgvector 1536 HNSW)
-- vector 타입은 Prisma 모델 불가 → raw SQL DDL (ADR-108 D1/D3)
-- DML은 Python psycopg worker 전용(api는 벡터 미접근)

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE job_embeddings (
  job_posting_id INTEGER PRIMARY KEY REFERENCES job_postings(id) ON DELETE CASCADE,
  embedding vector(1536),
  embedding_version TEXT NOT NULL,
  model_id TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON job_embeddings USING hnsw (embedding vector_cosine_ops);

CREATE TABLE resume_embeddings (
  resume_id INTEGER PRIMARY KEY REFERENCES resumes(id) ON DELETE CASCADE,
  embedding vector(1536),
  embedding_version TEXT NOT NULL,
  model_id TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON resume_embeddings USING hnsw (embedding vector_cosine_ops);
