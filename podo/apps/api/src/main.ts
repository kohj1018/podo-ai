import 'reflect-metadata'
import { NestFactory } from '@nestjs/core'
import session from 'express-session'
import passport from 'passport'
import { AppModule } from './app.module'
import { AllExceptionsFilter } from './common/error.filter'

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule)
  app.useGlobalFilters(new AllExceptionsFilter()) // 단일 envelope { error: { code, message } } (ARCH §7-1)

  // httpOnly 쿠키 세션(express-session) + passport. DB 세션 테이블 없음(stateless 서명 쿠키, ADR-006 단순성).
  // 쿠키: 로컬(web:3000↔api:3001 same-site)=lax, 프로덕션(Vercel↔AWS cross-site)=none+secure(M6 T-087).
  const isProd = process.env.NODE_ENV === 'production'
  app.use(
    session({
      secret: process.env.SESSION_SECRET ?? 'dev-insecure-session-secret',
      resave: false,
      saveUninitialized: false,
      cookie: {
        httpOnly: true,
        sameSite: isProd ? 'none' : 'lax',
        secure: isProd,
        maxAge: 1000 * 60 * 60 * 24 * 7, // 7일
      },
    }),
  )
  app.use(passport.initialize())
  app.use(passport.session())

  // credentials 쿠키 전송을 위해 origin 명시(와일드카드 금지 — T-087). web fetch는 credentials:'include'.
  app.enableCors({ origin: process.env.WEB_ORIGIN ?? 'http://localhost:3000', credentials: true })

  await app.listen(process.env.PORT ?? 3001)
}

void bootstrap()
