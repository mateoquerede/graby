param(
    [string]$SettingsPath = "shared/settings.json",
    [string]$ExamplePath = "shared/settings.example.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Is-MissingCredential {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $true
    }

    return ($Value -like "tu_*")
}

if (-not (Test-Path -LiteralPath $SettingsPath)) {
    if (-not (Test-Path -LiteralPath $ExamplePath)) {
        throw "Settings file and example file not found."
    }

    Copy-Item -LiteralPath $ExamplePath -Destination $SettingsPath
    Write-Host "Created $SettingsPath from example."
}

$raw = Get-Content -LiteralPath $SettingsPath -Raw -Encoding UTF8

try {
    $settings = $raw | ConvertFrom-Json
} catch {
    $settings = [pscustomobject]@{}
}

if ($null -eq $settings.coto) {
    $settings | Add-Member -MemberType NoteProperty -Name coto -Value ([pscustomobject]@{})
}

$email = [string]$settings.coto.email
$password = [string]$settings.coto.password

$needsEmail = Is-MissingCredential $email
$needsPassword = Is-MissingCredential $password

if (-not $needsEmail -and -not $needsPassword) {
    Write-Host "Coto credentials already configured."
    exit 0
}

Write-Host ""
Write-Host "Coto credentials are missing in $SettingsPath"

if ($needsEmail) {
    do {
        $email = Read-Host "Enter Coto email/user"
    } while ([string]::IsNullOrWhiteSpace($email))

    $settings.coto.email = $email.Trim()
}

if ($needsPassword) {
    do {
        $secure = Read-Host "Enter Coto password" -AsSecureString

        $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)

        try {
            $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
        } finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
        }
    } while ([string]::IsNullOrWhiteSpace($password))

    $settings.coto.password = $password
}

$json = $settings | ConvertTo-Json -Depth 20
Set-Content -LiteralPath $SettingsPath -Value $json -Encoding UTF8

Write-Host "Credentials saved to $SettingsPath"
