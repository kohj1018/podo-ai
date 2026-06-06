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
    const message = exception instanceof HttpException ? exception.message : 'Internal server error'
    const code = HttpStatus[status] ?? 'ERROR'
    response.status(status).json({ error: { code, message } })
  }
}
