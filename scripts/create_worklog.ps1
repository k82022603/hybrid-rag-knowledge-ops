# 작업 일지 생성 스크립트 (PowerShell)

param(
    [string]$Date = (Get-Date -Format "yyyy-MM-dd")
)

# 날짜 파싱
$dateObj = [DateTime]::ParseExact($Date, "yyyy-MM-dd", $null)
$year = $dateObj.ToString("yyyy")
$month = $dateObj.ToString("MM-MMMM", [System.Globalization.CultureInfo]::InvariantCulture)

# 경로 설정
$worklogDir = "docs\work_logs\$year\$month"
$worklogFile = "$worklogDir\$Date.md"

# 디렉토리 생성
if (-not (Test-Path $worklogDir)) {
    New-Item -ItemType Directory -Path $worklogDir -Force | Out-Null
    Write-Host "📁 Created directory: $worklogDir" -ForegroundColor Green
}

# 이미 파일이 있으면 열기만
if (Test-Path $worklogFile) {
    Write-Host "📝 Opening existing worklog: $worklogFile" -ForegroundColor Yellow
    code $worklogFile
    exit 0
}

# 템플릿 생성
$template = @"
# Work Log - $Date

## 📌 Today's Focus
- [ ] 주요 작업 1
- [ ] 주요 작업 2

## ✅ Completed Tasks
1. **작업명**
   - 상세 내용

## 💡 Key Decisions
-

## 🐛 Issues & Blockers
- (없음)

## 📚 Learnings
-

## 📅 Next Steps
- [ ] 내일 작업 1

## 📊 Time Spent
-

## 🔗 References
-
"@

# 파일 생성
Set-Content -Path $worklogFile -Value $template -Encoding UTF8

Write-Host "✅ Created worklog: $worklogFile" -ForegroundColor Green
code $worklogFile
