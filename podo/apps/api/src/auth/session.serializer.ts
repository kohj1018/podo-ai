import { Injectable } from '@nestjs/common'
import { PassportSerializer } from '@nestjs/passport'

// 세션에는 userId만 직렬화(계정 PII는 세션에 미저장 — 매 요청 rehydrate는 { id }로 충분).
@Injectable()
export class SessionSerializer extends PassportSerializer {
  serializeUser(user: { id: string }, done: (err: Error | null, id?: string) => void): void {
    done(null, user.id)
  }

  deserializeUser(id: string, done: (err: Error | null, user?: { id: string }) => void): void {
    done(null, { id })
  }
}
