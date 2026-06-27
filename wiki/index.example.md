# 프로젝트 대시보드

_자동 생성됨: 2026-06-16 02:59 · `scripts/aggregate.py` · 직접 편집하지 말 것_

## ⚠️ 주의

- 🚫 **fake-sensor** — blocked: EC2 디스크 용량
- 💤 **fake-lidar** — 12일째 커밋 없음 (정체)

## 요약

| 프로젝트 | 상태 | 브랜치 | 마지막 커밋 | 미커밋 | 할일 | ADR | 마일스톤 |
|---|---|---|---|---|---|---|---|
| **fake-esp32** | active | `master` | 오늘 | ✓ | 2 | 2 | ESP-NOW 재전송 로직 |
| **fake-sensor** | blocked | `master` | 오늘 | ⚠️1 | 0 | 0 | TimescaleDB 마이그레이션 |
| **fake-lidar** | paused | `master` | 💤 12일 전 | ✓ | 0 | 0 | Mid-360 포인트클라우드 정합 |

## 상세

### fake-esp32
- 상태: active  ·  마일스톤: ESP-NOW 재전송 로직
- 마지막 커밋: 2026-06-16 02:59 (오늘) — ESP-NOW 초기 구현
- 브랜치: `master`  ·  미커밋 변경: 0개  ·  미완료 할일: 2개  ·  ADR: 2개
- 블로커: 없음

### fake-sensor
- 상태: blocked  ·  마일스톤: TimescaleDB 마이그레이션
- 마지막 커밋: 2026-06-16 02:59 (오늘) — 초기 스키마
- 브랜치: `master`  ·  미커밋 변경: 1개  ·  미완료 할일: 0개  ·  ADR: 0개
- 블로커: EC2 디스크 용량

### fake-lidar
- 상태: paused  ·  마일스톤: Mid-360 포인트클라우드 정합  ·  💤 정체
- 마지막 커밋: 2026-06-04 10:00 (12일 전) — 초기 파이프라인
- 브랜치: `master`  ·  미커밋 변경: 0개  ·  미완료 할일: 0개  ·  ADR: 0개
- 블로커: 없음

---

관련: [통합 할일](todos.md) · [결정사항(ADR)](adr.md)

