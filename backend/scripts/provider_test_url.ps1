param(
  [Parameter(Mandatory=$true)]
  [string]$FeedUrl,

  [int]$TimeoutSeconds = 20
)

Write-Host "Testing feed URL: $FeedUrl"

try {
  $response = Invoke-WebRequest -Uri $FeedUrl -UseBasicParsing -TimeoutSec $TimeoutSeconds
  Write-Host "OK"
  Write-Host "Status code: $($response.StatusCode)"
  Write-Host "Content type: $($response.Headers['Content-Type'])"
  Write-Host "Length: $($response.Content.Length) chars"

  $preview = $response.Content
  if ($preview.Length -gt 600) {
    $preview = $preview.Substring(0, 600) + "..."
  }

  Write-Host ""
  Write-Host "Preview:"
  Write-Host $preview
  exit 0
} catch {
  Write-Host "FAILED"
  Write-Host "Reason: $($_.Exception.Message)"
  Write-Host ""
  Write-Host "Notes:"
  Write-Host "- provider.example.com is only a placeholder, not a real source."
  Write-Host "- Use only official affiliate/feed/API URLs from a real provider."
  Write-Host "- If testing local demo feeds, keep the feed server running on port 9000."
  exit 1
}
