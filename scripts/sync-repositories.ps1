[CmdletBinding()]
param(
    [switch]$IncludePriorityB
)

$ErrorActionPreference = 'Continue'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$SeedPath = Join-Path $ProjectRoot 'data\catalogs\repositories-seed.csv'
$DestinationRoot = Join-Path $ProjectRoot 'external\repos'
$RevisionPath = Join-Path $ProjectRoot 'data\catalogs\repository-revisions.csv'

New-Item -ItemType Directory -Force -Path $DestinationRoot | Out-Null
$rows = Import-Csv -LiteralPath $SeedPath | Where-Object {
    $_.download -eq 'yes' -and ($_.priority -eq 'A' -or $IncludePriorityB)
}

$results = foreach ($row in $rows) {
    $folder = $row.repository.Replace('/', '__')
    $destination = Join-Path $DestinationRoot $folder
    $url = "https://github.com/$($row.repository).git"

    if (-not (Test-Path -LiteralPath $destination)) {
        Write-Host "Cloning $($row.repository)"
        git clone --depth 1 --filter=blob:none --no-tags $url $destination
    }
    else {
        Write-Host "Fetching $($row.repository)"
        git -C $destination fetch --depth 1 --no-tags origin
    }

    if (Test-Path -LiteralPath (Join-Path $destination '.git')) {
        $revision = git -C $destination rev-parse HEAD
        $branch = git -C $destination branch --show-current
        [pscustomobject]@{
            repository = $row.repository
            local_path = "external/repos/$folder"
            revision = $revision
            branch = $branch
            captured_at = (Get-Date).ToUniversalTime().ToString('o')
            status = 'available'
        }
    }
    else {
        [pscustomobject]@{
            repository = $row.repository
            local_path = "external/repos/$folder"
            revision = ''
            branch = ''
            captured_at = (Get-Date).ToUniversalTime().ToString('o')
            status = 'failed'
        }
    }
}

$results | Export-Csv -LiteralPath $RevisionPath -NoTypeInformation -Encoding utf8
Write-Host "Recorded $($results.Count) repository revisions in $RevisionPath"
