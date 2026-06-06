import { Controller, DefaultValuePipe, Get, ParseIntPipe, Query } from '@nestjs/common'
import type { FeedPage, FeedService } from './feed.service'

@Controller()
export class FeedController {
  constructor(private readonly feed: FeedService) {}

  // GET /api/v1/feed?cursor= — ParseIntPipe가 cursor 검증(비정수 → 400 envelope).
  @Get('api/v1/feed')
  async getFeed(
    @Query('cursor', new DefaultValuePipe(-1), ParseIntPipe) cursor: number,
  ): Promise<FeedPage> {
    return this.feed.getFeed(cursor)
  }
}
