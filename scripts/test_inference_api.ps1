param(
    [string]$BaseUrl = "http://localhost:8001",
    [string]$ApiKey = "dev-finance-api-key",
    [int]$TimeoutSec = 600
)

$ErrorActionPreference = "Stop"

Write-Host "Testing Finance LLM API at $BaseUrl" -ForegroundColor Cyan

Write-Host "`n[1/4] GET /health" -ForegroundColor Yellow
$health = Invoke-RestMethod `
    -Method Get `
    -Uri "$BaseUrl/health" `
    -TimeoutSec 60

$health | Format-List

Write-Host "`n[2/4] GET /ready" -ForegroundColor Yellow
$ready = Invoke-RestMethod `
    -Method Get `
    -Uri "$BaseUrl/ready" `
    -TimeoutSec 60

$ready | Format-List

Write-Host "`n[3/4] POST /summarize" -ForegroundColor Yellow
$summarizeBody = @{
    text = "Revenue increased 12 percent, but margins declined because input costs and interest expense rose."
    max_new_tokens = 40
    temperature = 0.2
} | ConvertTo-Json

$summarize = Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/summarize" `
    -Headers @{ "X-API-Key" = $ApiKey } `
    -ContentType "application/json" `
    -Body $summarizeBody `
    -TimeoutSec $TimeoutSec

$summarize | Format-List

Write-Host "`n[4/4] POST /risk-analysis" -ForegroundColor Yellow
$riskBody = @{
    text = "The company reported higher revenue, lower gross margin, rising debt service costs, and weaker free cash flow."
    max_new_tokens = 80
    temperature = 0.2
} | ConvertTo-Json

$risk = Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/risk-analysis" `
    -Headers @{ "X-API-Key" = $ApiKey } `
    -ContentType "application/json" `
    -Body $riskBody `
    -TimeoutSec $TimeoutSec

$risk | Format-List

Write-Host "`nInference API smoke test completed." -ForegroundColor Green
