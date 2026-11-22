param([ValidateSet(0,1,2)][int]$PartyId=0)
Set-Location (Split-Path -Parent $PSScriptRoot)
$settings=@{}
Get-Content ".env" | ForEach-Object { if ($_ -match "^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$") { $settings[$matches[1]]=$matches[2].Trim() } }
$env:MPC_PARTY_ID="$PartyId"
$env:MPC_PARTIES_COUNT="3"
$env:MPC_BASE_PORT="11365"
$stateDir=Join-Path (Get-Location) ".state"
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
$env:MPC_PARTY_STATE_DB_PATH=Join-Path $stateDir "party_$PartyId.sqlite3"
$env:MPC_ENABLE_TLS="true"
$env:MPC_COORDINATOR_TOKEN=$settings["MPC_NODE${PartyId}_TOKEN"]
$env:MPC_FOUNDER_TOKEN_SECRET=$settings["MPC_FOUNDER_TOKEN_SECRET_$PartyId"]
$env:MPC_PARTY_ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
0..2 | ForEach-Object { Set-Item -Path "Env:MPC_PARTY_${_}_HOST" -Value "127.0.0.1" }
$cert="infrastructure/certs/party_$PartyId/control"
$port=8100+$PartyId
& ".\.venv\Scripts\python.exe" -m uvicorn backend.mpc.party_service:app --host 127.0.0.1 --port $port --ssl-certfile "$cert/control.crt" --ssl-keyfile "$cert/control.key" --ssl-ca-certs "infrastructure/certs/ca/ca.crt"
