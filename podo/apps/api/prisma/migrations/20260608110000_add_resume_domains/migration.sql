-- T-066: resume_domains (이력서 도메인 자동 분류 결과 — worker 소유, api typed read)
-- 일반 컬럼(text[]) → Prisma 모델. DML은 Python worker(단일 writer, ARCH §3-2).

-- CreateTable
CREATE TABLE "resume_domains" (
    "resume_id" INTEGER NOT NULL,
    "primary_domains" TEXT[],
    "secondary_domains" TEXT[],
    "confidence" TEXT NOT NULL,
    "classifier_version" TEXT NOT NULL,

    CONSTRAINT "resume_domains_pkey" PRIMARY KEY ("resume_id")
);

-- AddForeignKey
ALTER TABLE "resume_domains" ADD CONSTRAINT "resume_domains_resume_id_fkey" FOREIGN KEY ("resume_id") REFERENCES "resumes"("id") ON DELETE CASCADE ON UPDATE CASCADE;
