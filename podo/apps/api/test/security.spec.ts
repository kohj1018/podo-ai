import 'reflect-metadata'
import { readFileSync } from 'node:fs'
import type { Server } from 'node:http'
import { join } from 'node:path'
import express from 'express'
import rateLimit from 'express-rate-limit'
import helmet from 'helmet'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'

// T-089 AC-3 — 보안 헤더 + 레이트리밋 baseline.
// main.ts와 동일한 미들웨어(helmet + express-rate-limit)를 작은 express 앱에 적용해 실 응답
// 헤더를 검증하고, main.ts가 둘을 실제로 배선했는지 정적으로 확인한다(둘 중 하나라도 빠지면 red).

describe('security middleware (T-089 AC-3)', () => {
  let server: Server
  let baseUrl: string

  beforeAll(async () => {
    const app = express()
    app.use(helmet())
    app.use(
      rateLimit({ windowMs: 60_000, limit: 300, standardHeaders: true, legacyHeaders: false }),
    )
    app.get('/probe', (_req, res) => {
      res.json({ ok: true })
    })
    await new Promise<void>((resolve) => {
      server = app.listen(0, () => resolve())
    })
    const addr = server.address()
    const port = typeof addr === 'object' && addr ? addr.port : 0
    baseUrl = `http://127.0.0.1:${port}`
  })

  afterAll(async () => {
    await new Promise<void>((resolve) => server.close(() => resolve()))
  })

  it('test_AC_3_security_headers_present', async () => {
    const res = await fetch(`${baseUrl}/probe`)
    // helmet: MIME 스니핑 차단 + HSTS(프로덕션 HTTPS 전제) 헤더 노출
    expect(res.headers.get('x-content-type-options')).toBe('nosniff')
    expect(res.headers.get('strict-transport-security')).toBeTruthy()
    // express-rate-limit standardHeaders → RateLimit-* 노출
    expect(res.headers.get('ratelimit-limit')).toBe('300')
  })

  it('test_AC_3_main_wires_helmet_and_ratelimit', () => {
    const src = readFileSync(join(__dirname, '..', 'src', 'main.ts'), 'utf-8')
    expect(src).toMatch(/helmet\(\)/)
    expect(src).toMatch(/rateLimit\(/)
  })
})
