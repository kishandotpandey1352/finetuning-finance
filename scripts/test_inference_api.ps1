param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$ApiKey = "dev-finance-api-key"
)

$ErrorActionPreference = "Stop"

Write-Host "Testing health endpoint..."

Invoke-RestMethod `
    -Method Get `
    -Uri "$BaseUrl/health"

Write-Host ""
Write-Host "Testing readiness endpoint..."

Invoke-RestMethod `
    -Method Get `
    -Uri "$BaseUrl/ready"

Write-Host ""
Write-Host "Testing summarize endpoint..."

$SummarizeBody = @{
    text = "The company reported revenue growth of 12 percent year over year, but gross margin declined due to higher input costs. Interest expense increased after the company refinanced its debt at higher rates. Management expects demand to remain stable but warned that foreign exchange volatility could affect earnings."
    max_new_tokens = 180
    temperature = 0.2
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/summarize" `
    -Headers @{ "X-API-Key" = $ApiKey } `
    -ContentType "application/json" `
    -Body $SummarizeBody

Write-Host ""
Write-Host "Testing QA endpoint..."

$QABody = @{
    question = "What are the main risks in this company update?"
    context = "Revenue increased 12 percent, gross margin declined, and interest expense rose after debt refinancing. Management also highlighted foreign exchange volatility."
    max_new_tokens = 180
    temperature = 0.2
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/qa" `
    -Headers @{ "X-API-Key" = $ApiKey } `
    -ContentType "application/json" `
    -Body $QABody

Write-Host ""
Write-Host "Testing risk-analysis endpoint..."

$RiskBody = @{
    text = "The borrower has declining cash flow, rising leverage, increased short-term debt, and exposure to variable interest rates. Revenue concentration is high because two customers account for more than half of sales."
    max_new_tokens = 220
    temperature = 0.2
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/risk-analysis" `
    -Headers @{ "X-API-Key" = $ApiKey } `
    -ContentType "application/json" `
    -Body $RiskBody

Write-Host ""
Write-Host "Testing metrics endpoint..."

Invoke-RestMethod `
    -Method Get `
    -Uri "$BaseUrl/metrics"

Write-Host ""
Write-Host "API test completed."