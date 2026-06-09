import {
  Body,
  Controller,
  Delete,
  Get,
  HttpCode,
  HttpStatus,
  Param,
  Post,
  Query,
  Req,
  UseGuards,
} from '@nestjs/common'
import { SessionGuard } from '../auth/session.guard'
import {
  type ApplicationAction,
  type ApplicationEventRow,
  type ApplicationEventWithPosting,
  ApplicationsService,
} from './applications.service'
import type { CreateApplicationDto } from './dto/create-application.dto'

interface AuthedRequest {
  user?: { id: string }
}

// 지원/스킵·즐겨찾기 CRUD — 모든 조회/쓰기가 세션 사용자 범위(F-016 인가).
@Controller('api/v1/applications')
@UseGuards(SessionGuard)
export class ApplicationsController {
  constructor(private readonly applications: ApplicationsService) {}

  @Post()
  @HttpCode(HttpStatus.CREATED)
  async record(
    @Body() body: CreateApplicationDto,
    @Req() req: AuthedRequest,
  ): Promise<{ data: ApplicationEventRow }> {
    const userId = req.user?.id ?? ''
    const ev = await this.applications.recordAction(userId, body.job_posting_id, body.action)
    return { data: ev }
  }

  @Get()
  async list(
    @Req() req: AuthedRequest,
    @Query('filter') filter?: ApplicationAction,
  ): Promise<{ data: ApplicationEventWithPosting[] }> {
    const userId = req.user?.id ?? ''
    return { data: await this.applications.getActions(userId, filter) }
  }

  @Delete(':id')
  async remove(
    @Param('id') id: string,
    @Req() req: AuthedRequest,
  ): Promise<{ data: { ok: true } }> {
    const userId = req.user?.id ?? ''
    await this.applications.deleteAction(userId, Number.parseInt(id, 10))
    return { data: { ok: true } }
  }
}
