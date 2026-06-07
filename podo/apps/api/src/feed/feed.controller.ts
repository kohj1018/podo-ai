import {
  Controller,
  DefaultValuePipe,
  Get,
  ParseIntPipe,
  Query,
  Req,
  UseGuards,
} from '@nestjs/common'
import { SessionGuard } from '../auth/session.guard'
import { type FeedMeta, type FeedPage, FeedService } from './feed.service'

interface AuthedRequest {
  user?: { id: string }
}

@Controller()
@UseGuards(SessionGuard)
export class FeedController {
  constructor(private readonly feed: FeedService) {}

  // GET /api/v1/feed?cursor= — ParseIntPipe가 cursor 검증(비정수 → 400 envelope).
  // 세션 사용자 범위로 격리(타 사용자 피드 미노출 — T-042 데이터 격리).
  @Get('api/v1/feed')
  async getFeed(
    @Query('cursor', new DefaultValuePipe(-1), ParseIntPipe) cursor: number,
    @Req() req: AuthedRequest,
  ): Promise<FeedPage> {
    return this.feed.getFeed(cursor, req.user?.id)
  }

  // GET /api/v1/feed/meta — 피드 진입 8-상태 분기 메타(F-018, T-046). 커서 무관 1회 호출.
  @Get('api/v1/feed/meta')
  async getMeta(@Req() req: AuthedRequest): Promise<FeedMeta> {
    return this.feed.getFeedMeta(req.user?.id)
  }
}
