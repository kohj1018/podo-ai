-- CreateTable
CREATE TABLE "source_crawl_status" (
    "source_id" TEXT NOT NULL,
    "tier" TEXT,
    "method" TEXT,
    "status" TEXT NOT NULL,
    "last_success_at" TIMESTAMP(3),
    "last_error" TEXT,

    CONSTRAINT "source_crawl_status_pkey" PRIMARY KEY ("source_id")
);
