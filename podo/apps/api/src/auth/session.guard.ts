import {
  type CanActivate,
  type ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common'

interface SessionAwareRequest {
  isAuthenticated?: () => boolean
}

// 세션 인증 가드 — passport req.isAuthenticated()로 보호 라우트 진입 차단(비로그인=401).
@Injectable()
export class SessionGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const req = context.switchToHttp().getRequest<SessionAwareRequest>()
    if (req.isAuthenticated?.()) {
      return true
    }
    throw new UnauthorizedException({ code: 'UNAUTHENTICATED', message: '로그인이 필요합니다.' })
  }
}
