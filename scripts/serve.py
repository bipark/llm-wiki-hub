#!/usr/bin/env python3
"""LLM-Wiki-Hub 뷰어 서버.

- wiki/ 를 docsify 로 브라우저에 서빙한다 (정적 파일 + 클라이언트 렌더).
- 시작 시 1회 + LLMWIKIHUB_REFRESH_SECONDS(기본 3600초)마다 aggregate.py 를 재실행한다.
- GET /refresh 는 즉시 재집계 후 / 로 리다이렉트한다 (수동 새로고침 버튼).
- 단방향 원칙 유지: 어느 프로젝트도 수정하지 않고, aggregate 가 wiki/ 만 다시 쓴다.

설정 (환경변수):
    LLMWIKIHUB_PORT=8787              서빙 포트 (localhost 전용)
    LLMWIKIHUB_REFRESH_SECONDS=3600  주기 재집계 간격

pm2 로 구동:
    pm2 start ecosystem.config.cjs
"""

import os
import sys
import time
import threading
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HUB = Path(__file__).resolve().parent.parent
WIKI = HUB / "wiki"
AGGREGATE = HUB / "scripts" / "aggregate.py"
PORT = int(os.environ.get("LLMWIKIHUB_PORT", "8787"))
REFRESH_SECONDS = int(os.environ.get("LLMWIKIHUB_REFRESH_SECONDS", "3600"))

_agg_lock = threading.Lock()


def aggregate(reason: str):
    # 동시 재집계 방지 (주기 스레드 + /refresh 동시 진입).
    with _agg_lock:
        print(f"[llm-wiki-hub] 재집계 ({reason})", flush=True)
        try:
            subprocess.run([sys.executable, str(AGGREGATE)],
                           cwd=str(HUB), timeout=120)
        except Exception as e:
            print(f"[llm-wiki-hub] 재집계 실패: {e}", flush=True)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WIKI), **kwargs)

    def do_GET(self):
        if self.path.rstrip("/") == "/refresh":
            aggregate("수동 새로고침")
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            return
        super().do_GET()

    def log_message(self, *args):
        pass  # 접근 로그 침묵


def periodic_refresher():
    while True:
        time.sleep(REFRESH_SECONDS)
        aggregate(f"주기 {REFRESH_SECONDS}s")


def main():
    aggregate("시작")  # 첫 화면을 신선하게
    threading.Thread(target=periodic_refresher, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[llm-wiki-hub] http://127.0.0.1:{PORT}  ·  갱신 주기 {REFRESH_SECONDS}s", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
