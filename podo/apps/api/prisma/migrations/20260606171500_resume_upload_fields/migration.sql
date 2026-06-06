-- AlterTable
ALTER TABLE "resumes" ADD COLUMN     "masked" BOOLEAN NOT NULL DEFAULT false,
ADD COLUMN     "source" TEXT NOT NULL DEFAULT 'seed',
ADD COLUMN     "upload_format" TEXT NOT NULL DEFAULT 'txt';
