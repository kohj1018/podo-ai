import { Injectable } from '@nestjs/common'
import { PassportStrategy } from '@nestjs/passport'
import { type Profile, Strategy } from 'passport-google-oauth20'
import { AuthService } from './auth.service'

// Google OAuth 전략 — 환경변수 기반(GOOGLE_CLIENT_ID/SECRET/CALLBACK_URL).
// 미설정 시 placeholder로 구성만 가능(실 로그인 불가) — 무키 E2E는 test-session 우회로 진행.
@Injectable()
export class GoogleStrategy extends PassportStrategy(Strategy, 'google') {
  constructor(private readonly authService: AuthService) {
    super({
      // `||` (not `??`): 미설정 env가 빈 문자열("")로 주입되는 경우에도 placeholder로 fallback.
      clientID: process.env.GOOGLE_CLIENT_ID || 'unset',
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || 'unset',
      callbackURL: process.env.GOOGLE_CALLBACK_URL || 'http://localhost:3001/auth/google/callback',
      scope: ['email', 'profile'],
    })
  }

  // accessToken/refreshToken은 받되 저장하지 않는다(ADR-105 Amend1 §2). 계정 PII는 log 금지.
  async validate(
    _accessToken: string,
    _refreshToken: string,
    profile: Profile,
  ): Promise<{ id: string }> {
    return this.authService.findOrCreateUser('google', {
      providerAccountId: profile.id,
      email: profile.emails?.[0]?.value ?? '',
      displayName: profile.displayName ?? '',
      avatarUrl: profile.photos?.[0]?.value ?? null,
    })
  }
}
