import 'reflect-metadata'
import { describe, expect, it } from 'vitest'
import { HealthController } from '../src/health.controller'

describe('HealthController', () => {
  it('test_AC_1_health_returns_ok', () => {
    const controller = new HealthController()
    expect(controller.check()).toEqual({ status: 'ok' })
  })
})
