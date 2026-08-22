[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$SeedPath = Join-Path $ProjectRoot 'data\catalogs\repositories-seed.csv'
$OutputPath = Join-Path $ProjectRoot 'data\catalogs\repositories-current.csv'

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw 'GitHub CLI (gh) is required.'
}

$rows = Import-Csv -LiteralPath $SeedPath
$output = foreach ($row in $rows) {
    Write-Host "Inspecting $($row.repository)"
    $json = gh api -X GET "/repos/$($row.repository)"
    if ($LASTEXITCODE -ne 0) {
        [pscustomobject]@{
            category = $row.category
            priority = $row.priority
            download = $row.download
            repository = $row.repository
            html_url = "https://github.com/$($row.repository)"
            description = ''
            stars = ''
            forks = ''
            open_issues = ''
            updated_at = ''
            default_branch = ''
            license = 'UNAVAILABLE'
            archived = ''
            size_kb = ''
            primary_use = $row.primary_use
            notes = $row.notes
        }
        continue
    }
    $repo = $json | ConvertFrom-Json
    [pscustomobject]@{
        category = $row.category
        priority = $row.priority
        download = $row.download
        repository = $repo.full_name
        html_url = $repo.html_url
        description = $repo.description
        stars = $repo.stargazers_count
        forks = $repo.forks_count
        open_issues = $repo.open_issues_count
        updated_at = $repo.updated_at
        default_branch = $repo.default_branch
        license = if ($repo.license.spdx_id) { $repo.license.spdx_id } else { 'NOASSERTION' }
        archived = $repo.archived
        size_kb = $repo.size
        primary_use = $row.primary_use
        notes = $row.notes
    }
}

$output | Export-Csv -LiteralPath $OutputPath -NoTypeInformation -Encoding utf8
Write-Host "Wrote $($output.Count) rows to $OutputPath"
