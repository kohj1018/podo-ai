import { Injectable } from '@nestjs/common'
import { PrismaService } from '../prisma/prisma.service'

// OAuth provider profile에서 추출한 최소 식별자(ADR-105 Amend1 §2 — 계정 PII 최소 저장).
export interface OAuthProfile {
  providerAccountId: string
  email: string
  displayName: string
  avatarUrl?: string | null
}

@Injectable()
export class AuthService {
  constructor(private readonly prisma: PrismaService) {}

  // (provider, provider_account_id) 복합 unique upsert — 최초=생성, 재로그인=동일 계정 매칭.
  // OAuth access/refresh token은 받지도 저장하지도 않는다(ADR-105 Amend1 §2).
  // 계정 PII(email·display_name)는 log에 출력 금지 — 스코어링 경로 미유입(ADR-105 Amend1).
  async findOrCreateUser(provider: string, profile: OAuthProfile): Promise<{ id: string }> {
    return this.prisma.user.upsert({
      where: {
        provider_provider_account_id: {
          provider,
          provider_account_id: profile.providerAccountId,
        },
      },
      // 재로그인 시 계정 PII를 갱신하지 않는다(최소 변경 — 식별자 안정).
      update: {},
      create: {
        provider,
        provider_account_id: profile.providerAccountId,
        email: profile.email,
        display_name: profile.displayName,
        avatar_url: profile.avatarUrl ?? null,
      },
      select: { id: true },
    })
  }
}
