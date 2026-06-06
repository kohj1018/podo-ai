import { spawn } from 'node:child_process'
import { resolve } from 'node:path'

// 스코어링 트리거 경계(port) — NestJS가 Python worker를 기동(cross-stack, ADR-101 D-LANG).
// 테스트는 fake runner를 주입하고, 실 subprocess는 stabilize E2E가 실증한다(T-037 §8 3계층 검증:
// AC-1 Python이 ranking_run 생성, AC-2 TS가 트리거 계약, E2E가 실 subprocess).
export abstract class WorkerRunner {
  abstract run(resumeId: number): Promise<void>
}

// M3 로컬 단일 사용자: `uv run python -m worker --resume-id N` subprocess
// (scripts/e2e.mjs phase4와 동일 호출 — uv가 워크스페이스 PYTHONPATH·env 셋업).
// exit 0까지 대기 후 resolve(동기 트리거 — 완료 시 200). 큐/폴링은 M4.
export class SubprocessWorkerRunner extends WorkerRunner {
  run(resumeId: number): Promise<void> {
    return new Promise((res, rej) => {
      // api는 podo/apps/api에서 기동(e2e.mjs) → repo root는 3단계 위. REPO_ROOT로 override 가능.
      const repoRoot = process.env.REPO_ROOT ?? resolve(process.cwd(), '..', '..', '..')
      const child = spawn(
        'uv',
        ['run', 'python', '-m', 'worker', '--resume-id', String(resumeId)],
        { cwd: repoRoot, env: process.env, stdio: 'inherit' },
      )
      child.on('error', rej)
      child.on('exit', (code) =>
        code === 0
          ? res()
          : rej(new Error(`worker --resume-id ${resumeId} exited with code ${code}`)),
      )
    })
  }
}
