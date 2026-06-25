@echo off
REM 每天 8 点触发 GitHub Trending 日报推送
cd /d D:\codex\dev\bd\百度\github-trending-digest
gh workflow run daily.yml
echo %date% %time% 已触发 >> trigger.log
