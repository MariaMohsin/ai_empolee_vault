# CEO Briefing Weekly Scheduler - Windows Task Scheduler Setup
# Run once with: powershell -ExecutionPolicy Bypass -File scripts/schedule_ceo_briefing.ps1

$TaskName    = "AI_Employee_CEO_Briefing"
$ScriptRoot  = Split-Path -Parent $PSScriptRoot
$PythonExe   = (Get-Command python -ErrorAction SilentlyContinue).Source
$SkillScript = Join-Path $ScriptRoot ".claude\skills\ceo-briefing\scripts\ceo_briefing.py"
$LogFile     = Join-Path $ScriptRoot "Logs\ceo_briefing_scheduler.log"

if (-not $PythonExe) {
    Write-Error "Python not found in PATH. Install Python and retry."
    exit 1
}

if (-not (Test-Path $SkillScript)) {
    Write-Error "Skill script not found: $SkillScript"
    exit 1
}

# Ensure Logs directory exists
$LogDir = Join-Path $ScriptRoot "Logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

# Build the action: python <script> >> logfile 2>&1
$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$SkillScript`" >> `"$LogFile`" 2>&1" `
    -WorkingDirectory $ScriptRoot

# Every Monday at 08:00
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "08:00AM"

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false

# Remove old task if exists
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed existing task: $TaskName"
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "AI Employee Gold Tier: Weekly CEO briefing report" `
    -RunLevel Highest | Out-Null

Write-Host ""
Write-Host "================================================="
Write-Host "  CEO Briefing Scheduler Registered"
Write-Host "================================================="
Write-Host "  Task name : $TaskName"
Write-Host "  Schedule  : Every Monday at 08:00 AM"
Write-Host "  Script    : $SkillScript"
Write-Host "  Log       : $LogFile"
Write-Host "================================================="
Write-Host ""
Write-Host "To run immediately:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "To remove:"
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName'"
