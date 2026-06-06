-- CreateIndex
CREATE UNIQUE INDEX "recommendations_run_id_job_posting_id_key" ON "recommendations"("run_id", "job_posting_id");
