-- T-065: coarse_candidates (후보 밖 공고 coarse projection — worker 소유, api typed read)
-- fit_level 없음(유사도 rank만). resume_id 범위(현재 run). DML은 Python worker(ADR-108 D3).

-- CreateTable
CREATE TABLE "coarse_candidates" (
    "job_posting_id" INTEGER NOT NULL,
    "resume_id" INTEGER NOT NULL,
    "user_id" TEXT,
    "similarity_rank" DOUBLE PRECISION NOT NULL,
    "cache_key_version" TEXT NOT NULL,
    "scored_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "coarse_candidates_pkey" PRIMARY KEY ("job_posting_id", "resume_id")
);

-- CreateIndex
CREATE INDEX "coarse_candidates_resume_id_idx" ON "coarse_candidates"("resume_id");

-- AddForeignKey
ALTER TABLE "coarse_candidates" ADD CONSTRAINT "coarse_candidates_job_posting_id_fkey" FOREIGN KEY ("job_posting_id") REFERENCES "job_postings"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "coarse_candidates" ADD CONSTRAINT "coarse_candidates_resume_id_fkey" FOREIGN KEY ("resume_id") REFERENCES "resumes"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "coarse_candidates" ADD CONSTRAINT "coarse_candidates_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
