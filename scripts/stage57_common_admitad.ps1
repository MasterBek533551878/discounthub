function Read-DiscountHubEnvFile {
  param([string]$Path = "backend/.env")

  if (!(Test-Path $Path)) {
    throw "Backend .env file was not found: $Path"
  }

  $result = @{}
  $lines = Get-Content -Path $Path -Encoding UTF8
  foreach ($rawLine in $lines) {
    $line = ([string]$rawLine).Trim()
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    if ($line.StartsWith("#")) { continue }
    $idx = $line.IndexOf("=")
    if ($idx -lt 1) { continue }

    $key = $line.Substring(0, $idx).Trim()
    $value = $line.Substring($idx + 1).Trim()

    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
      $value = $value.Substring(1, $value.Length - 2)
    }

    $result[$key] = $value
  }

  return $result
}

function Get-HttpErrorDetail {
  param($ErrorRecord)

  $message = $ErrorRecord.Exception.Message
  $response = $ErrorRecord.Exception.Response
  if ($null -eq $response) {
    return $message
  }

  try {
    $stream = $response.GetResponseStream()
    if ($null -eq $stream) {
      return $message
    }
    $reader = New-Object System.IO.StreamReader($stream)
    $body = $reader.ReadToEnd()
    if (![string]::IsNullOrWhiteSpace($body)) {
      return "$message :: $body"
    }
  } catch {
    return $message
  }

  return $message
}

function Get-AdmitadSettings {
  param([string]$EnvPath = "backend/.env")

  $env = Read-DiscountHubEnvFile -Path $EnvPath
  $clientId = [string]$env["ADMITAD_CLIENT_ID"]
  $clientSecret = [string]$env["ADMITAD_CLIENT_SECRET"]
  $websiteId = [string]$env["ADMITAD_WEBSITE_ID"]
  $apiBaseUrl = [string]$env["ADMITAD_API_BASE_URL"]

  if ([string]::IsNullOrWhiteSpace($apiBaseUrl)) {
    $apiBaseUrl = "https://api.admitad.com"
  }
  $apiBaseUrl = $apiBaseUrl.TrimEnd("/")

  if ([string]::IsNullOrWhiteSpace($clientId)) {
    throw "ADMITAD_CLIENT_ID is missing in $EnvPath"
  }
  if ([string]::IsNullOrWhiteSpace($clientSecret)) {
    throw "ADMITAD_CLIENT_SECRET is missing in $EnvPath"
  }
  if ([string]::IsNullOrWhiteSpace($websiteId)) {
    throw "ADMITAD_WEBSITE_ID is missing in $EnvPath"
  }

  return [pscustomobject]@{
    ClientId = $clientId
    ClientSecret = $clientSecret
    WebsiteId = $websiteId
    ApiBaseUrl = $apiBaseUrl
  }
}

function Get-AdmitadAccessToken {
  param(
    [Parameter(Mandatory=$true)]$Settings,
    [string]$Scope = "advcampaigns advcampaigns_for_website websites"
  )

  $pair = "{0}:{1}" -f $Settings.ClientId, $Settings.ClientSecret
  $basic = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($pair))
  $headers = @{ Authorization = "Basic $basic" }
  $body = @{
    grant_type = "client_credentials"
    client_id = $Settings.ClientId
    scope = $Scope
  }

  try {
    $token = Invoke-RestMethod `
      -Method Post `
      -Uri "$($Settings.ApiBaseUrl)/token/" `
      -Headers $headers `
      -ContentType "application/x-www-form-urlencoded;charset=UTF-8" `
      -Body $body
  } catch {
    $detail = Get-HttpErrorDetail $_
    throw "Admitad token request failed: $detail"
  }

  if ([string]::IsNullOrWhiteSpace([string]$token.access_token)) {
    throw "Admitad token response did not include access_token."
  }

  return $token
}

function Invoke-AdmitadGet {
  param(
    [Parameter(Mandatory=$true)]$Settings,
    [Parameter(Mandatory=$true)][string]$AccessToken,
    [Parameter(Mandatory=$true)][string]$PathAndQuery
  )

  $uri = "$($Settings.ApiBaseUrl)$PathAndQuery"
  try {
    return Invoke-RestMethod -Method Get -Uri $uri -Headers @{ Authorization = "Bearer $AccessToken" }
  } catch {
    $detail = Get-HttpErrorDetail $_
    if ($detail -match "403") {
      throw "Admitad GET failed for $($PathAndQuery): $detail. Check that the token scope includes advcampaigns_for_website and that ADMITAD_WEBSITE_ID belongs to this account."
    }
    throw "Admitad GET failed for $($PathAndQuery): $detail"
  }
}

function Get-AdmitadResultsArray {
  param($Response)

  if ($null -eq $Response) { return @() }
  if ($Response.PSObject.Properties.Name -contains "results") {
    return @($Response.results)
  }
  if ($Response -is [System.Array]) {
    return @($Response)
  }
  return @($Response)
}

function Get-SafeSlug {
  param([string]$Value)
  $slug = $Value.ToLowerInvariant()
  $slug = [regex]::Replace($slug, "[^a-z0-9]+", "_")
  $slug = $slug.Trim("_")
  if ($slug.Length -gt 40) { $slug = $slug.Substring(0, 40).Trim("_") }
  if ([string]::IsNullOrWhiteSpace($slug)) { $slug = "program" }
  return $slug
}
