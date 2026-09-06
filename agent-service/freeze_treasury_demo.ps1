$ErrorActionPreference = "Stop"

Write-Host "Treasury demo final freeze" -ForegroundColor Cyan
Write-Host "Running Treasury T1-T9 and core 3I-A through 3I-D regressions..."

$tests = @(
    "test_treasury_t1_domain.py",
    "test_treasury_t2_tools.py",
    "test_treasury_t3_agents.py",
    "test_treasury_t4_dag.py",
    "test_treasury_t5_approval.py",
    "test_treasury_t6_failures.py",
    "test_treasury_t7_least_privilege.py",
    "test_treasury_t8_trace_evaluation.py",
    "test_treasury_t9_demo.py",
    "test_3i_a_contracts.py",
    "test_3i_a_registry.py",
    "test_3i_b_specialist_wrappers.py",
    "test_3i_c_coordinator.py",
    "test_3i_d_runtime.py"
)

foreach ($test in $tests) {
    Write-Host ">>> python $test" -ForegroundColor Yellow
    python $test
    if ($LASTEXITCODE -ne 0) {
        throw "Regression failed: $test. Branch was NOT frozen."
    }
}

Write-Host ">>> python run_treasury_demo.py --compact" -ForegroundColor Yellow
python run_treasury_demo.py --compact
if ($LASTEXITCODE -ne 0) {
    throw "Demo smoke test failed. Branch was NOT frozen."
}

$status = git status --porcelain
if ($status) {
    Write-Host ""
    Write-Host "Working tree is not clean. Commit intended T9 changes first:" -ForegroundColor Red
    git status --short
    throw "Refusing to freeze a dirty working tree."
}

$branch = git branch --show-current
if (-not $branch) {
    throw "Could not determine current Git branch."
}

$tag = "treasury-demo-t9-final"

git rev-parse $tag 2>$null
if ($LASTEXITCODE -eq 0) {
    throw "Tag '$tag' already exists. Refusing to overwrite it."
}

Write-Host ""
Write-Host "All regressions passed." -ForegroundColor Green
Write-Host "Current branch: $branch"
Write-Host "Creating annotated tag: $tag"

git tag -a $tag -m "Freeze Treasury interview demo after T9 regression gate"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create Git tag."
}

Write-Host ""
Write-Host "FREEZE COMPLETE" -ForegroundColor Green
Write-Host "Branch: $branch"
Write-Host "Tag:    $tag"
Write-Host ""
Write-Host "Push when ready:"
Write-Host "  git push origin $branch"
Write-Host "  git push origin $tag"
