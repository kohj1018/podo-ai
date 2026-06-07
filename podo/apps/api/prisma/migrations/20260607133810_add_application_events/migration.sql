-- CreateTable
CREATE TABLE "application_events" (
    "id" SERIAL NOT NULL,
    "user_id" TEXT NOT NULL,
    "job_posting_id" INTEGER NOT NULL,
    "action" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "application_events_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "application_events_user_id_job_posting_id_idx" ON "application_events"("user_id", "job_posting_id");

-- CreateIndex
CREATE UNIQUE INDEX "application_events_user_id_job_posting_id_key" ON "application_events"("user_id", "job_posting_id");

-- AddForeignKey
ALTER TABLE "application_events" ADD CONSTRAINT "application_events_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "application_events" ADD CONSTRAINT "application_events_job_posting_id_fkey" FOREIGN KEY ("job_posting_id") REFERENCES "job_postings"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
