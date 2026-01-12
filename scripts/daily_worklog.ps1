# 일일 작업 일지 통합 스크립트
# 작업 일지 생성 + 커밋을 한 번에 처리

param(
    [switch]$Commit,
    [switch]$Push
)

$date = Get-Date -Format "yyyy-MM-dd"

Write-Host "🚀 Daily Work Log - $date" -ForegroundColor Cyan
Write-Host ""

# 1. 작업 일지 생성/열기
Write-Host "📝 Opening work log..." -ForegroundColor Yellow
& .\scripts\create_worklog.ps1

# Commit 플래그가 있으면 커밋 수행
if ($Commit) {
    Write-Host ""
    Write-Host "💾 Committing changes..." -ForegroundColor Yellow
    & .\scripts\commit_worklog.ps1

    # Push 플래그가 있으면 푸시
    if ($Push) {
        Write-Host ""
        Write-Host "📤 Pushing to remote..." -ForegroundColor Yellow
        git push

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Successfully pushed to remote" -ForegroundColor Green
        } else {
            Write-Host "❌ Failed to push" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "✨ Done!" -ForegroundColor Green
