import {
  type ArgumentsHost,
  Catch,
  type ExceptionFilter,
  HttpException,
  HttpStatus,
} from '@nestjs/common'

interface JsonResponse {
  status(code: number): { json(body: unknown): void }
}

// 모든 예외를 단일 envelope `{ error: { code, message } }`로 직렬화(ARCH §7-1).
@Catch()
export class AllExceptionsFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost): void {
    const response = host.switchToHttp().getResponse<JsonResponse>()
    const status =
      exception instanceof HttpException ? exception.getStatus() : HttpStatus.INTERNAL_SERVER_ERROR

    // 도메인 code 우선: 컨트롤러가 throw new HttpException({ code, message }, status)로 주입한
    // code를 그대로 사용(RESUME_TOO_LARGE 등). 없으면 HttpStatus 이름으로 폴백.
    let code = HttpStatus[status] ?? 'ERROR'
    let message = exception instanceof HttpException ? exception.message : 'Internal server error'
    if (exception instanceof HttpException) {
      const res = exception.getResponse()
      if (typeof res === 'object' && res !== null) {
        const r = res as { code?: unknown; message?: unknown }
        if (typeof r.code === 'string') code = r.code
        if (typeof r.message === 'string') message = r.message
      }
    }
    response.status(status).json({ error: { code, message } })
  }
}
