"""20-pair golden eval (capstone) — podo-ai LIVE vs prototype baseline 16/20.

ONE-OFF 검증 하니스. 프로토타입(podo-algorithm-test) 레포의 인간 라벨/이력서/raw JD를
크로스-레포로 읽어 podo-ai의 run_scoring을 LIVE로 돌리고, podo-ai 자체 evaluate_pairs로
채점한다. 첫 실행은 LLM 라이브, 이후는 .cache/llm 히트로 결정적·무료 재현.

  PROTOTYPE_ROOT env로 프로토타입 레포 경로 override 가능
  (기본 = C:\\Users\\kbwdesktop\\Desktop\\dev-practice\\podo-algorithm-test).

메트릭 정합성 체크포인트 (검증 대상):
  (1) METRIC  : eval.golden_pairs.load_pairs + evaluate_pairs (strict A/B by RANK,
                tie-aware by equal fit_level) — 프로토타입 이식본 그대로.
  (2) LIVE    : worker.pipeline.run_scoring (실제 LLM/캐시). NOT rescore_persona(오프라인).
  (3) MAPPING : 각 쌍을 자기 persona 랭킹으로 채점.
  (4) NO LEAK : expected_winner는 채점에만, run_scoring엔 resume+jobs만. 20쌍 전수 + unavailable 명시.

산출: result.txt(리포트) + detail.json(per-pair).
재실행: `python validation/golden20_capstone/runner.py` (레포 루트에서; 캐시 히트로 결정적).
"""

import json
import os
import traceback
from collections import defaultdict
from pathlib import Path

PROTO = Path(
    os.environ.get(
        "PROTOTYPE_ROOT",
        r"C:\Users\kbwdesktop\Desktop\dev-practice\podo-algorithm-test",
    )
)
HERE = Path(__file__).parent
OUT_TXT = HERE / "result.txt"
OUT_JSON = HERE / "detail.json"

_lines: list[str] = []


def log(s: str = "") -> None:
    _lines.append(s)


def flush() -> None:
    OUT_TXT.write_text("\n".join(_lines), encoding="utf-8")


def persona_inputs(persona: str):
    resume_text = (PROTO / "data" / "eval" / "resumes" / f"{persona}.md").read_text(
        encoding="utf-8"
    )
    jp = json.loads(
        (PROTO / "outputs" / "eval" / persona / "jobs_parsed.json").read_text(
            encoding="utf-8"
        )
    )
    items = jp if isinstance(jp, list) else jp.get("jobs", jp)
    jobs = [
        {
            "job_id": j["job_id"],
            "company": j.get("company", ""),
            "title": j.get("title", ""),
            "url": j.get("url", ""),
            "raw_text": j.get("raw_text", ""),
        }
        for j in items
    ]
    fr = json.loads(
        (PROTO / "outputs" / "eval" / persona / "final_ranking.json").read_text(
            encoding="utf-8"
        )
    )
    up = fr.get("user_profile") or {}
    return (
        resume_text,
        jobs,
        up.get("primary_domains") or [],
        up.get("secondary_domains") or [],
    )


def main() -> None:
    from core.models import Resume
    from eval.golden_pairs import evaluate_pairs, load_pairs
    from worker.pipeline import run_scoring

    gp = json.loads(
        (PROTO / "data" / "eval" / "golden_pairs" / "golden_pairs_20.json").read_text(
            encoding="utf-8"
        )
    )
    raw_pairs = gp["pairs"]

    # golden json -> podo-ai GoldenPair shape, grouped by persona (checkpoint 3 + 4)
    by_persona: dict[str, list[dict]] = defaultdict(list)
    for p in raw_pairs:
        by_persona[p["persona"]].append(
            {
                "pair_id": p["pair_id"],
                "job_a": p["job_a_id"],  # id, NOT inline JD
                "job_b": p["job_b_id"],
                "label": p["expected_winner"],  # ground truth — scoring ONLY
                "category": p.get("category", "same_domain_close"),
                "hardness": p.get("hardness", 1),
            }
        )

    log("20-PAIR GOLDEN EVAL (capstone) — podo-ai LIVE vs prototype baseline 16/20")
    log(
        f"personas: { {k: len(v) for k, v in by_persona.items()} } | total pairs={len(raw_pairs)}"
    )
    log(
        "metric: podo-ai eval.golden_pairs.evaluate_pairs (strict A/B by rank, tie-aware by fit)"
    )
    log("")

    all_eval = []
    detail = []
    persona_rows = []
    for persona, rows in by_persona.items():
        labeled, _unlabeled = load_pairs(rows)  # validates labels (checkpoint 1)
        resume_text, jobs, prim, sec = persona_inputs(persona)
        log(f"[{persona}] run_scoring LIVE on {len(jobs)} jobs (domains {prim}/{sec})")
        flush()
        resume = Resume(
            raw_text=resume_text, primary_domains=prim, secondary_domains=sec
        )
        out = run_scoring(
            resume, jobs, ranking_mode="domain_fit_bt"
        )  # checkpoint 2: LIVE
        rk = out["final_ranking"]["ranking"]
        ranking_map = {r["job_id"]: r["rank"] for r in rk}
        fit_by_id = {r["job_id"]: r["fit_level"] for r in rk}
        available = set(ranking_map)
        pending = sorted(out.get("pending_job_ids") or [])

        evald = evaluate_pairs(labeled, ranking_map, fit_by_id, available)
        all_eval.extend(evald)
        sc = sum(1 for e in evald if e.correct_strict is True)
        st = sum(
            1
            for e in evald
            if e.pair.label in ("A_better", "B_better") and not e.unavailable
        )
        ua = sum(1 for e in evald if e.unavailable)
        persona_rows.append((persona, sc, st, ua, pending))
        log(f"  -> strict {sc}/{st}  unavailable={ua}  pending={pending}")
        for r in sorted(rk, key=lambda r: r["rank"]):
            log(
                f"     #{r['rank']} {r['job_id']:24} fit={r['fit_level']} dom={r['domain_alignment']}"
            )
        for e in evald:
            detail.append(
                {
                    "persona": persona,
                    "pair_id": e.pair.pair_id,
                    "job_a": e.pair.job_a,
                    "job_b": e.pair.job_b,
                    "label": e.pair.label,
                    "system_winner": e.system_winner,
                    "rank_a": ranking_map.get(e.pair.job_a),
                    "rank_b": ranking_map.get(e.pair.job_b),
                    "fit_a": fit_by_id.get(e.pair.job_a),
                    "fit_b": fit_by_id.get(e.pair.job_b),
                    "correct_strict": e.correct_strict,
                    "correct_tie_aware": e.correct_tie_aware,
                    "unavailable": e.unavailable,
                    "category": e.pair.category,
                }
            )
        log("")
        flush()

    strict_correct = sum(1 for e in all_eval if e.correct_strict is True)
    strict_total = sum(
        1
        for e in all_eval
        if e.pair.label in ("A_better", "B_better") and not e.unavailable
    )
    unavailable = sum(1 for e in all_eval if e.unavailable)
    tie_correct = sum(1 for e in all_eval if e.correct_tie_aware is True)
    tie_total = sum(
        1
        for e in all_eval
        if e.pair.label in ("A_better", "B_better", "tie") and not e.unavailable
    )

    log("=" * 64)
    log("RESULT")
    log("=" * 64)
    for persona, sc, st, ua, pending in persona_rows:
        log(f"  {persona:24} strict {sc}/{st}  unavailable={ua}  pending={pending}")
    log("")
    acc = (strict_correct / strict_total) if strict_total else 0.0
    log(
        f"  STRICT (rank-based, A_better/B_better): {strict_correct}/{strict_total}  acc={acc:.2f}"
    )
    log(f"  tie-aware: {tie_correct}/{tie_total}")
    log(
        f"  unavailable pairs (excluded): {unavailable}  | total scored: {strict_total}/20"
    )
    log("  prototype baseline: 16/20 (acc=0.80)")
    log("")
    log("DISAGREEMENTS (system != human, strict):")
    for e in all_eval:
        if (
            e.pair.label in ("A_better", "B_better")
            and e.correct_strict is False
            and not e.unavailable
        ):
            log(
                f"  {e.pair.pair_id}: label={e.pair.label} system={e.system_winner} "
                f"a={e.pair.job_a} b={e.pair.job_b} cat={e.pair.category}"
            )

    OUT_JSON.write_text(
        json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log(f"\nper-pair detail -> {OUT_JSON.name}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("\n[ERROR]\n" + traceback.format_exc())
    finally:
        flush()
    print("done ->", OUT_TXT)
