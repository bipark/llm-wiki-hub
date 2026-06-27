// LLM-Wiki-Hub 뷰어 서비스 (pm2)
//   pm2 start ecosystem.config.cjs
//   pm2 save && pm2 startup   # 부팅 시 자동 시작
// 접속: http://127.0.0.1:8787
module.exports = {
  apps: [
    {
      name: 'llm-wiki-hub',
      script: 'scripts/serve.py',
      interpreter: 'python3',
      cwd: __dirname,
      autorestart: true,
      env: {
        LLMWIKIHUB_PORT: '8787',
        LLMWIKIHUB_REFRESH_SECONDS: '3600', // 1시간마다 재집계
        LLMWIKIHUB_STALE_DAYS: '7',
      },
    },
  ],
};
