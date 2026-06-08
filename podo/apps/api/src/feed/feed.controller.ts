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
import { type CoarsePage, type FeedMeta, type FeedPage, FeedService } from './feed.service'

interface AuthedRequest {
  user?: { id: string }
}

@Controller()
@UseGuards(SessionGuard)
export class FeedController {
  constructor(private readonly feed: FeedService) {}

  // GET /api/v1/feed?cursor=[&section=coarse] — ParseIntPipe가 cursor 검증(비정수 → 400).
  // section=coarse면 후보 밖 coarse 섹션(fit_level 없음, ADR-108 D3). 세션 사용자 범위 격리.
  @Get('api/v1/feed')
  async getFeed(
    @Query('cursor', new DefaultValuePipe(-1), ParseIntPipe) cursor: number,
    @Query('section') section: string | undefined,
    @Req() req: AuthedRequest,
  ): Promise<FeedPage | CoarsePage> {
    if (section === 'coarse') {
      return this.feed.getCoarseFeed(cursor, req.user?.id)
    }
    return this.feed.getFeed(cursor, req.user?.id)
  }

  // GET /api/v1/feed/meta — 피드 진입 8-상태 분기 메타(F-018, T-046). 커서 무관 1회 호출.
  @Get('api/v1/feed/meta')
  async getMeta(@Req() req: AuthedRequest): Promise<FeedMeta> {
    return this.feed.getFeedMeta(req.user?.id)
  }
}
