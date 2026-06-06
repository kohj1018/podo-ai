-- pgvector extension (ARCH §3-2 규칙2: DDL은 Prisma 소유 — raw SQL, 테이블보다 먼저)
CREATE EXTENSION IF NOT EXISTS vector;

-- CreateTable
CREATE TABLE "job_postings" (
    "id" SERIAL NOT NULL,
    "source" TEXT NOT NULL,
    "company" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "url" TEXT NOT NULL,
    "raw_text" TEXT NOT NULL,
    "role_family" TEXT,
    "posted_at" TIMESTAMP(3),
    "closing_at" TIMESTAMP(3),
    "diff_status" TEXT,
    "fetched_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "job_postings_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "crawl_runs" (
    "id" SERIAL NOT NULL,
    "channel" TEXT NOT NULL,
    "run_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "status" TEXT NOT NULL,
    "new_count" INTEGER NOT NULL DEFAULT 0,
    "closed_count" INTEGER NOT NULL DEFAULT 0,
    "error" TEXT,

    CONSTRAINT "crawl_runs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ranking_runs" (
    "id" SERIAL NOT NULL,
    "resume_id" INTEGER NOT NULL,
    "job_set_hash" TEXT NOT NULL,
    "model" TEXT NOT NULL,
    "prompt_version" TEXT NOT NULL,
    "scoring_mode" TEXT NOT NULL,
    "ranking_mode" TEXT NOT NULL,
    "cache_key_version" TEXT NOT NULL,
    "result" JSONB NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ranking_runs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "recommendations" (
    "id" SERIAL NOT NULL,
    "run_id" INTEGER NOT NULL,
    "job_posting_id" INTEGER NOT NULL,
    "rank_position" INTEGER NOT NULL,
    "fit_level" INTEGER,
    "domain_alignment" TEXT,
    "status" TEXT NOT NULL,

    CONSTRAINT "recommendations_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "resumes" (
    "id" SERIAL NOT NULL,
    "content" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "resumes_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "job_postings_url_key" ON "job_postings"("url");

-- CreateIndex
CREATE UNIQUE INDEX "ranking_runs_resume_id_job_set_hash_model_prompt_version_sc_key" ON "ranking_runs"("resume_id", "job_set_hash", "model", "prompt_version", "scoring_mode", "ranking_mode", "cache_key_version");

-- CreateIndex
CREATE INDEX "recommendations_run_id_rank_position_idx" ON "recommendations"("run_id", "rank_position");

-- AddForeignKey
ALTER TABLE "ranking_runs" ADD CONSTRAINT "ranking_runs_resume_id_fkey" FOREIGN KEY ("resume_id") REFERENCES "resumes"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "recommendations" ADD CONSTRAINT "recommendations_run_id_fkey" FOREIGN KEY ("run_id") REFERENCES "ranking_runs"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "recommendations" ADD CONSTRAINT "recommendations_job_posting_id_fkey" FOREIGN KEY ("job_posting_id") REFERENCES "job_postings"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
