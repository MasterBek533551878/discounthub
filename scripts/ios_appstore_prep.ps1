param(
  [string]$BundleId = "uz.discounthub.app",
  [string]$AppName = "DiscountHub"
)

$ErrorActionPreference = "Stop"

function Backup-Once([string]$Path) {
  if (!(Test-Path $Path)) { throw "File not found: $Path" }
  $backup = "$Path.bak"
  if (!(Test-Path $backup)) {
    Copy-Item $Path $backup -Force
    Write-Host "Backup created: $backup"
  }
}

$pbxproj = "ios/Runner.xcodeproj/project.pbxproj"
$plist = "ios/Runner/Info.plist"

Backup-Once $pbxproj
Backup-Once $plist

# Patch Xcode project: app bundle id + iPhone only.
$text = Get-Content $pbxproj -Raw
$text = $text -replace 'PRODUCT_BUNDLE_IDENTIFIER = com\.discounthub\.discounthub;', "PRODUCT_BUNDLE_IDENTIFIER = $BundleId;"
$text = $text -replace 'PRODUCT_BUNDLE_IDENTIFIER = com\.discounthub\.discounthub\.RunnerTests;', "PRODUCT_BUNDLE_IDENTIFIER = $BundleId.RunnerTests;"
$text = $text -replace 'TARGETED_DEVICE_FAMILY = "1,2";', 'TARGETED_DEVICE_FAMILY = 1;'
$text = $text -replace 'TARGETED_DEVICE_FAMILY = "1";', 'TARGETED_DEVICE_FAMILY = 1;'
Set-Content -Path $pbxproj -Value $text -NoNewline -Encoding UTF8

# Patch Info.plist display name/name and add UIDeviceFamily = iPhone only if missing.
$plistText = Get-Content $plist -Raw
$plistText = $plistText -replace '(?s)<key>CFBundleDisplayName</key>\s*<string>.*?</string>', "<key>CFBundleDisplayName</key>`n`t<string>$AppName</string>"
$plistText = $plistText -replace '(?s)<key>CFBundleName</key>\s*<string>.*?</string>', "<key>CFBundleName</key>`n`t<string>$AppName</string>"

if ($plistText -match '<key>UIDeviceFamily</key>') {
  $plistText = $plistText -replace '(?s)<key>UIDeviceFamily</key>\s*<array>.*?</array>', "<key>UIDeviceFamily</key>`n`t<array>`n`t`t<integer>1</integer>`n`t</array>"
} else {
  $uidBlock = "`t<key>UIDeviceFamily</key>`n`t<array>`n`t`t<integer>1</integer>`n`t</array>`n"
  $plistText = $plistText -replace '</dict>', "$uidBlock</dict>"
}
Set-Content -Path $plist -Value $plistText -NoNewline -Encoding UTF8

Write-Host "iOS App Store prep complete." -ForegroundColor Green
Write-Host "Bundle ID: $BundleId"
Write-Host "App name: $AppName"
Write-Host "Target device family: iPhone only"
Write-Host ""
Write-Host "Verify with:"
Write-Host "Select-String -Path .\ios\Runner.xcodeproj\project.pbxproj -Pattern 'PRODUCT_BUNDLE_IDENTIFIER|TARGETED_DEVICE_FAMILY' -Context 0,0"
Write-Host "Select-String -Path .\ios\Runner\Info.plist -Pattern 'CFBundleDisplayName|CFBundleName|UIDeviceFamily' -Context 2,4"
