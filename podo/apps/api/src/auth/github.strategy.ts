import { Injectable } from '@nestjs/common'
import { PassportStrategy } from '@nestjs/passport'
import { type Profile, Strategy } from 'passport-github2'
import { AuthService } from './auth.service'

// GitHub OAuth 전략 — 환경변수 기반(GITHUB_CLIENT_ID/SECRET/CALLBACK_URL).
// 미설정 시 placeholder로 구성만 가능(실 로그인 불가) — 무키 E2E는 test-session 우회로 진행.
@Injectable()
export class GitHubStrategy extends PassportStrategy(Strategy, 'github') {
  constructor(private readonly authService: AuthService) {
    super({
      clientID: process.env.GITHUB_CLIENT_ID ?? 'unset',
      clientSecret: process.env.GITHUB_CLIENT_SECRET ?? 'unset',
      callbackURL: process.env.GITHUB_CALLBACK_URL ?? 'http://localhost:3001/auth/github/callback',
      scope: ['user:email'],
    })
  }

  // accessToken/refreshToken은 받되 저장하지 않는다(ADR-105 Amend1 §2). 계정 PII는 log 금지.
  async validate(
    _accessToken: string,
    _refreshToken: string,
    profile: Profile,
  ): Promise<{ id: string }> {
    return this.authService.findOrCreateUser('github', {
      providerAccountId: profile.id,
      email: profile.emails?.[0]?.value ?? '',
      displayName: profile.displayName ?? profile.username ?? '',
      avatarUrl: profile.photos?.[0]?.value ?? null,
    })
  }
}
