param(
  [string]$Id = 'ebay_browse_headphones',
  [string]$Name = 'eBay Browse API - Headphones',
  [string]$Query = 'wireless headphones',
  [string]$MarketplaceId = 'EBAY_US',
  [int]$Limit = 50,
  [string]$Sort = 'price',
  [bool]$Enabled = $false,
  [string]$ConfigPath = "$PSScriptRoot\..\config\feed_providers.json"
)

$ErrorActionPreference = 'Stop'

$encodedQuery = [System.Uri]::EscapeDataString($Query)
$url = "ebay://browse?q=$encodedQuery&marketplace_id=$MarketplaceId&limit=$Limit"
if ($Sort.Trim().Length -gt 0) {
  $url = "$url&sort=$([System.Uri]::EscapeDataString($Sort))"
}

& "$PSScriptRoot\provider_add_to_config.ps1" `
  -Id $Id `
  -Name $Name `
  -Url $url `
  -Adapter 'ebay_browse_api' `
  -Enabled $Enabled `
  -ReplaceOnSync $false `
  -ConfigPath $ConfigPath

Write-Host ''
Write-Host 'Note: provider is disabled by default until EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are configured.' -ForegroundColor Yellow
Write-Host "Provider URL: $url"
