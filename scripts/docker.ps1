# Wrapper so `docker` works in PowerShell when Docker Desktop isn't on PATH.
$dockerBin = "C:\Program Files\Docker\Docker\resources\bin"
if (Test-Path $dockerBin) {
    $env:Path = "$dockerBin;C:\Program Files\Docker\Docker\resources;$env:Path"
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error @"
Docker was not found. Install Docker Desktop from https://www.docker.com/products/docker-desktop/
or ensure 'C:\Program Files\Docker\Docker\resources\bin' is on your PATH.
"@
    exit 1
}

& docker @args
