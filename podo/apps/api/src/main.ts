import 'reflect-metadata'
import { NestFactory } from '@nestjs/core'
import { AppModule } from './app.module'

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule)
  app.enableCors() // 로컬 E2E: web(:3000)에서 api(:3001) 호출 허용
  await app.listen(process.env.PORT ?? 3001)
}

void bootstrap()
