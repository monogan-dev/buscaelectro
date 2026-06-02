# Crea una tarea programada en Windows para actualizar precios cada 12 horas
# Ejecutar como Administrador: powershell -ExecutionPolicy Bypass -File instalar_tarea.ps1

$NombreTarea  = "BuscaElectro-Actualizar"
$Python       = "C:\Users\guill\AppData\Local\Programs\Python\Python39-32\python.exe"
$Script       = "C:\Users\guill\Documents\proyectos claude\busqueda de productos\actualizar.py"
$Directorio   = "C:\Users\guill\Documents\proyectos claude\busqueda de productos"
$LogFile      = "$Directorio\actualizaciones.log"

# Eliminar tarea anterior si existe
Unregister-ScheduledTask -TaskName $NombreTarea -Confirm:$false -ErrorAction SilentlyContinue

# Crear acción
$Accion = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "`"$Script`"" `
    -WorkingDirectory $Directorio

# Ejecutar cada 12 horas empezando a las 6am
$Trigger1 = New-ScheduledTaskTrigger -Daily -At "06:00"
$Trigger2 = New-ScheduledTaskTrigger -Daily -At "18:00"

# Configuración: correr aunque no haya usuario conectado
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 10)

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $NombreTarea `
    -Action $Accion `
    -Trigger $Trigger1, $Trigger2 `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Actualiza precios de electrodomésticos en BuscaElectro cada 12 horas" `
    -Force

Write-Host ""
Write-Host "Tarea '$NombreTarea' creada exitosamente." -ForegroundColor Green
Write-Host "Se ejecutará a las 6:00 AM y 6:00 PM todos los dias." -ForegroundColor Cyan
Write-Host ""
Write-Host "Comandos utiles:" -ForegroundColor Yellow
Write-Host "  Ver tareas:     Get-ScheduledTask -TaskName '$NombreTarea'"
Write-Host "  Ejecutar ahora: Start-ScheduledTask -TaskName '$NombreTarea'"
Write-Host "  Eliminar:       Unregister-ScheduledTask -TaskName '$NombreTarea' -Confirm:`$false"
