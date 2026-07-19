param(
    [string]$BaseUrl,
    [string]$ApiKey = "dev-finance-api-key"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    throw "BaseUrl is required. Example: -BaseUrl http://your-alb-dns-name"
}

Write-Host "Testing public Finance LLM API:"
Write-Host $BaseUrl

Write-Host ""
Write-Host "Testing /health..."

Invoke-RestMethod `
    -Method Get `
    -Uri "$BaseUrl/health"

Write-Host ""
Write-Host "Testing /ready..."

Invoke-RestMethod `
    -Method Get `
    -Uri "$BaseUrl/ready"

Write-Host ""
Write-Host "Testing unauthorized /summarize call..."

try {
    $BadBody = @{
        text = "Revenue increased but margins declined due to rising costs."
        max_new_tokens = 120
        temperature = 0.2
    } | ConvertTo-Json

    Invoke-RestMethod `
        -Method Post `
        -Uri "$BaseUrl/summarize" `
        -ContentType "application/json" `
        -Body $BadBody

    throw "Unauthorized request unexpectedly succeeded."
} catch {
    Write-Host "Unauthorized request rejected as expected."
}

Write-Host ""
Write-Host "Testing authorized /summarize call..."

$SummarizeBody = @{
    text = "The company reported revenue growth of 12 percent, but gross margin declined due to higher input costs and interest expense increased after debt refinancing."
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
Write-Host "Testing /metrics..."

Invoke-RestMethod `
    -Method Get `
    -Uri "$BaseUrl/metrics"

Write-Host ""
Write-Host "Public endpoint test completed."