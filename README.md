# LLM-Wiki-Hub

여러 프로젝트를 동시에 굴리다 보니, 어느 순간부터 머릿속에서 상태를 추적하는 게
조금씩 버거워졌다. ESP32 펌웨어 몇 개, RTK GPS, LiDAR, 온도 수집 서버… 저장소가
늘어날수록 "지난주에 이거 어디까지 했지", "이건 왜 막혀 있었지", "다음에 뭐 하기로
했지" 같은 걸 매번 디렉토리를 옮겨 다니며 `git log` 로 더듬는 일이 잦아졌다.

LLM-Wiki-Hub 는 그게 귀찮아서 만들어본 도구다. 흩어진 프로젝트들을 되도록 건드리지 않고,
그 위에 살짝 얹어서 한 화면으로 보려고 한 읽기 전용 대시보드 정도라고 보면 된다.

> 왜, 어떤 흐름으로 이걸 만들게 됐는지에 대한 더 긴 이야기는 따로 적어뒀다 —
> [LLM-Wiki 로 LLM-Wiki 들을 관리하기](blog/llm-wiki로-llm-wiki들을-관리하기.md).

## 어쩌다 만들게 됐나

먼저 각 프로젝트를 [Karpathy 의 "LLM Wiki" 패턴](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
을 참고해서 정리하기 시작했다. 코드 옆에 LLM(나는 Claude Code 를 쓴다)이 같이 읽고
쓰는 평문 지식층을 두는 방식인데, 프로젝트마다 `STATUS.md` 로 지금 상태를 적고, 할 일은
`TODO.md` 같은 파일에, 설계 결정은 `docs/adr/` 에 한 장씩 쌓아두는 식으로 해봤다.

이걸 몇 달 하다 보니 한 가지가 눈에 들어왔다. 각 프로젝트가 이미 자기 상태를 평문으로
들고 있으니까, 그걸 가로질러 긁어모으기만 해도 대충 전체 현황판이 되겠더라. 새 도구를
위해 프로젝트마다 뭔가를 더 설치할 필요도 없었다. 이미 거기 있는 `git`, `STATUS.md`,
할일 파일을 읽기만 하면 됐으니까. LLM-Wiki-Hub 는 그 "읽어 모으는" 일을 대신해주는 얇은
한 겹 정도에 가깝다.

그러다 보니 결과적으로는 LLM-Wiki 로 관리하던 프로젝트들을, 다시 LLM-Wiki 비슷한
방식으로 한 층 위에서 들여다보는 도구가 된 셈이다.

## 내가 할일은 이것만

`projects.txt` 에 보고 싶은 프로젝트 경로를 한 줄씩 적는다.

```
~/work/esp32-mesh
~/work/rtk-gps
~/work/lidar-monitor
```

그리고 돌린다.

```
python scripts/aggregate.py
```

그러면 `wiki/index.md` 에 전체 프로젝트 요약표가 생긴다. 7일 넘게 커밋이 없는
프로젝트는 💤 로, `STATUS.md` 에 `status: blocked` 를 적어둔 프로젝트는 🚫 로
맨 위에 경고처럼 올라온다. 통합 할일은 `wiki/todos.md`, 모아둔 설계 결정은 `wiki/adr.md`
쪽에 정리된다. 별도 의존성은 따로 없고, Python 3 와 `git` 정도면 돌아간다.

## 두 단계의 이득

사실 아무 git 저장소나 경로에 넣어도 동작은 한다. 마지막 커밋이 언제였는지, 정체됐는지,
미커밋이 몇 개인지 정도는 `git` 만 읽어도 나오니까.

다만 이 도구가 좀 더 쓸모 있어지는 건 그 프로젝트가 LLM-Wiki 로 관리되고 있을 때인 것
같다. 상태·마일스톤·블로커 경고, 통합 할일, 통합 ADR 같은 건 전부 `STATUS.md`·할일 파일·
`docs/adr/` 에서 긁어오는 거라, 그게 채워져 있는 프로젝트일수록 현황판이 풍부해진다.
대충 채워둔 만큼 나온다고 보면 맞을 것 같다.

그래서 나는 새 프로젝트를 시작할 때 `templates/STATUS.md` 를 복사해서 이런 식으로
채워두는 편이다:

```markdown
# STATUS
status: active          # active / paused / blocked / done
milestone: 펌웨어 OTA 안정화
updated: 2026-06-27
blockers: 없음           # 막힌 게 있으면 적는다 → 대시보드 맨 위 🚫 로 뜸
```

이 파일은 LLM-Wiki-Hub 가 아니라 그 프로젝트 git 에 커밋한다. LLM-Wiki-Hub 쪽은 읽기만 하고,
상태를 바꾸는 건 늘 프로젝트 쪽에서 하는 걸 원칙으로 삼았다.

## 건드리지 않는 걸 원칙으로

만들면서 스스로 정해둔 규칙이 하나 있다. LLM-Wiki-Hub 는 어떤 프로젝트도 수정하지 않는다는
것. `git log`, `git status`, 그리고 평문 파일 몇 개를 읽는 정도에서 그친다. 합치지도,
양방향으로 동기화하지도 않는다. 흩어진 저장소들은 그냥 흩어진 채로 둔다.

덕분에 부작용을 걱정할 일이 거의 없다. 몇 번을 돌려도 결과가 같고, 산출물인 `wiki/*.md`
는 언제 지워도 다시 만들어진다. 망가질 상태가 딱히 없어서 부담 없이 돌리는 편이다.
(대신 직접 편집하면 다음 집계 때 덮어쓰니 주의. `wiki/index.html` 만은 뷰어 셸이라
집계가 안 건드린다.)

## 브라우저로 띄워두기

매번 스크립트를 돌리기 번거로워서, 나는 뷰어를 백그라운드에 띄워두고 브라우저 탭으로
열어둔다.

```
pm2 start ecosystem.config.cjs     # 백그라운드 구동
pm2 save && pm2 startup            # 부팅 시 자동 시작 (선택)
```

→ http://127.0.0.1:8787 . `scripts/serve.py` 가 `wiki/` 를 docsify 로 서빙하면서
1시간마다 자동으로 재집계하고, 우상단 ↻ 버튼을 누르면 그 자리에서 다시 모은다.
포트·주기는 `ecosystem.config.cjs` 의 `LLMWIKIHUB_PORT` / `LLMWIKIHUB_REFRESH_SECONDS` 로 바꾼다.
(pm2 가 싫으면 그냥 `python scripts/serve.py` 로 띄워도 된다.)

주기적으로 그냥 재집계만 돌리고 싶다면 `scripts/` 안에 macOS launchd(`com.llmwikihub.aggregate.plist`)
와 Linux systemd(`llm-wiki-hub.service` + `llm-wiki-hub.timer`) 예시를 넣어뒀으니 경로만 본인 것으로
바꿔서 쓰면 된다.

## 알아두면 좋은 것들

- 할일은 '할일 목적' 파일에서만 모은다. 기본값은 `TODO.md`, `*-tasks.md`, `PLAN.md`,
  `ROADMAP.md`, `STATUS.md` 의 `- [ ]` 항목. README 나 설계문서의 체크박스까지 긁으면
  노이즈가 너무 심해서 일부러 좁혀뒀다. 다른 파일에 할일을 둔다면 `STATUS.md` 에
  `todos: README.md, docs/*-tasks.md` 처럼 글롭으로 재정의하면 된다.
- ADR 은 `docs/adr/`, `adr/`, `wiki/decisions/`, `decisions/` 중 처음 발견된 디렉토리에서
  모은다.
- 정체 기준은 기본 7일. `LLMWIKIHUB_STALE_DAYS=10 python scripts/aggregate.py` 로 바꿀 수 있다.

## 동작 방식 한 장 요약

```
[독립 프로젝트들 — 수정 안 함]
  esp32-mesh/  (자기 git)
  rtk-gps/     (자기 git)
  lidar-proj/  (자기 git)
       ↑ 읽기만 (git log / status / STATUS.md / 할일 / ADR)
[LLM-Wiki-Hub] aggregate.py 가 긁어와 wiki/*.md 생성
```

LLM(나는 Claude Code) 운영 규칙은 `CLAUDE.md` 에 적어뒀다.

## 라이선스

MIT. 가져다 본인 방식대로 고쳐 쓰면 된다.
