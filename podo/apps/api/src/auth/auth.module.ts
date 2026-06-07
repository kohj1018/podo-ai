import { Module } from '@nestjs/common'
import { PassportModule } from '@nestjs/passport'
import { PrismaService } from '../prisma/prisma.service'
import { AuthController } from './auth.controller'
import { AuthService } from './auth.service'
import { GitHubStrategy } from './github.strategy'
import { GoogleStrategy } from './google.strategy'
import { SessionSerializer } from './session.serializer'

@Module({
  imports: [PassportModule.register({ session: true })],
  controllers: [AuthController],
  providers: [AuthService, PrismaService, GitHubStrategy, GoogleStrategy, SessionSerializer],
})
export class AuthModule {}
