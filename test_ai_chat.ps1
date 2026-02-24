# AI Chat Validation Tests
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "AI CHAT ORCHESTRATION VALIDATION TESTS" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

function Test-ChatQuery {
    param(
        [string]$TestNumber,
        [string]$TestName,
        [string]$Query,
        [string]$ExpectedIntent,
        [bool]$ShouldHaveSources
    )
    
    Write-Host "=== TEST $TestNumber - $TestName ===" -ForegroundColor Yellow
    Write-Host "Query: `"$Query`"" -ForegroundColor White
    Write-Host "Expected Intent: $ExpectedIntent" -ForegroundColor Gray
    Write-Host "Should have sources: $ShouldHaveSources" -ForegroundColor Gray
    
    try {
        $body = @{ query = $Query } | ConvertTo-Json
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/ai/query" -Method POST -Body $body -ContentType "application/json"
        
        $answerLength = $response.answer.Length
        $sourcesCount = $response.sources.Count
        
        Write-Host "`n[RESULT]" -ForegroundColor Green
        Write-Host "  Answer length: $answerLength chars" -ForegroundColor White
        Write-Host "  Sources: $sourcesCount" -ForegroundColor White
        Write-Host "`n  Answer preview:" -ForegroundColor Cyan
        Write-Host "  $($response.answer.Substring(0, [Math]::Min(200, $answerLength)))..." -ForegroundColor White
        
        # Validation
        if ($ShouldHaveSources -and $sourcesCount -eq 0) {
            Write-Host "`n  [WARNING] Expected sources but got none!" -ForegroundColor Red
        } elseif (-not $ShouldHaveSources -and $sourcesCount -gt 0) {
            Write-Host "`n  [WARNING] Expected no sources but got $sourcesCount!" -ForegroundColor Red
        } else {
            Write-Host "`n  [PASS] Source count is as expected" -ForegroundColor Green
        }
        
        Write-Host "`n" -ForegroundColor White
    } catch {
        Write-Host "`n[ERROR] Test failed: $_" -ForegroundColor Red
        Write-Host "`n" -ForegroundColor White
    }
    
    Start-Sleep -Seconds 1
}

# Test 1: General Knowledge (no database)
Test-ChatQuery -TestNumber "1" -TestName "GENERAL KNOWLEDGE" `
    -Query "What is regulatory affairs?" `
    -ExpectedIntent "GENERAL_KNOWLEDGE" `
    -ShouldHaveSources $false

# Test 2: Database Query (recent updates)
Test-ChatQuery -TestNumber "2" -TestName "DATABASE QUERY" `
    -Query "Latest FDA updates this week" `
    -ExpectedIntent "DATABASE_QUERY" `
    -ShouldHaveSources $true

# Test 3: List Request
Test-ChatQuery -TestNumber "3" -TestName "LIST REQUEST" `
    -Query "List ICH quality guidelines" `
    -ExpectedIntent "LIST_REQUEST" `
    -ShouldHaveSources $true

# Test 4: Comparison Request
Test-ChatQuery -TestNumber "4" -TestName "COMPARISON REQUEST" `
    -Query "Compare FDA and EMA approval process" `
    -ExpectedIntent "COMPARISON_REQUEST" `
    -ShouldHaveSources $false

# Test 5: Summary Request
Test-ChatQuery -TestNumber "5" -TestName "SUMMARY REQUEST" `
    -Query "Summarize ICH Q10" `
    -ExpectedIntent "SUMMARY_REQUEST" `
    -ShouldHaveSources $true

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ALL TESTS COMPLETED" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
Write-Host "Check backend logs for intent detection details" -ForegroundColor Yellow
