# 작업 일지 커밋 스크립트

$date = Get-Date -Format "yyyy-MM-dd"
$message = "[DOCS] Work log for $date"

Write-Host "📝 Committing work logs..." -ForegroundColor Cyan

# 작업 일지 추가
git add docs/work_logs/

# 변경사항 확인
$status = git status --porcelain docs/work_logs/
if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Host "⚠️  No changes to commit in work logs" -ForegroundColor Yellow
    exit 0
}

# 커밋
git commit -m $message

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Successfully committed work logs" -ForegroundColor Green
    Write-Host "   Message: $message" -ForegroundColor Gray
} else {
    Write-Host "❌ Failed to commit" -ForegroundColor Red
    exit 1
}
