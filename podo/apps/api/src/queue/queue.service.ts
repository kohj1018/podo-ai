import { SQSClient, SendMessageCommand } from '@aws-sdk/client-sqs'
import { Injectable } from '@nestjs/common'

// SQS enqueue 서비스 — 채점 요청을 scoring-queue에 전달(T-044, ADR-106 D1/D2).
// 환경변수: SQS_QUEUE_URL(필수), SQS_ENDPOINT_URL(LocalStack 시 설정, 미설정 시 실 AWS).
// 메시지 페이로드에 계정 PII(email 등) 미포함(ADR-105 Amend1).
@Injectable()
export class QueueService {
  private readonly client: SQSClient
  private readonly queueUrl: string

  constructor() {
    const endpoint = process.env.SQS_ENDPOINT_URL
    this.client = new SQSClient({
      region: process.env.AWS_REGION ?? 'us-east-1',
      ...(endpoint ? { endpoint } : {}),
    })
    // SQS_QUEUE_URL 미설정 시 startup에서 명시적 실패를 유도(환경변수 누락 early detection).
    this.queueUrl = process.env.SQS_QUEUE_URL ?? ''
  }

  async enqueue(resumeId: number, jobId: string): Promise<void> {
    const body = JSON.stringify({ resume_id: resumeId, job_id: jobId })
    await this.client.send(
      new SendMessageCommand({
        QueueUrl: this.queueUrl,
        MessageBody: body,
      }),
    )
  }
}
