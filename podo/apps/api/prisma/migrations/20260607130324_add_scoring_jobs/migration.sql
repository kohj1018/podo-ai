-- CreateTable
CREATE TABLE "scoring_jobs" (
    "id" TEXT NOT NULL,
    "resume_id" INTEGER NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'queued',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "scoring_jobs_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "scoring_jobs" ADD CONSTRAINT "scoring_jobs_resume_id_fkey" FOREIGN KEY ("resume_id") REFERENCES "resumes"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
