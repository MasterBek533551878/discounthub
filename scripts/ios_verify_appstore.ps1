$ErrorActionPreference = "Stop"

Write-Host "Checking iOS project settings..."

$projectFile = "ios/Runner.xcodeproj/project.pbxproj"
$infoPlist = "ios/Runner/Info.plist"

if (!(Test-Path $projectFile)) { throw "Missing $projectFile" }
if (!(Test-Path $infoPlist)) { throw "Missing $infoPlist" }

[xml]$xml = Get-Content $infoPlist -Raw
Write-Host "Info.plist XML: OK"

Write-Host "Bundle identifiers:"
Select-String -Path $projectFile -Pattern "PRODUCT_BUNDLE_IDENTIFIER" -Context 0,0

Write-Host "Target device family:"
Select-String -Path $projectFile -Pattern "TARGETED_DEVICE_FAMILY" -Context 0,0

Write-Host "Info.plist app identity/device family:"
Select-String -Path $infoPlist -Pattern "CFBundleDisplayName|CFBundleName|UIDeviceFamily" -Context 2,4

Write-Host "Done. Expected values: uz.discounthub.app, TARGETED_DEVICE_FAMILY = 1, UIDeviceFamily integer 1."
