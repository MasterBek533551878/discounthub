param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$AdminToken = "dev-local-admin-token",
  [int]$IntervalSeconds = 3600,
  [switch]$RunOnStartup
)

$runOnStartupValue = if ($RunOnStartup) { "true" } else { "false" }

Invoke-RestMethod `
  -Method Post `
  -Uri "$BaseUrl/admin/feed-providers/scheduler/start?interval_seconds=$IntervalSeconds&run_on_startup=$runOnStartupValue" `
  -Headers @{ "X-Admin-Token" = $AdminToken }
