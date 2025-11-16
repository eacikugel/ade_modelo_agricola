# Script para configurar y hacer push a GitHub
# Este script configura el remoto y hace push de tu código

$repoName = "ade_modelo_agricola"
$githubUser = Read-Host "Ingresa tu nombre de usuario de GitHub"

# Verificar si ya existe un remoto
$existingRemote = git remote get-url origin 2>$null
if ($existingRemote) {
    Write-Host "Ya existe un remoto 'origin': $existingRemote" -ForegroundColor Yellow
    $sobreescribir = Read-Host "¿Deseas reemplazarlo? (s/n)"
    if ($sobreescribir -eq "s" -or $sobreescribir -eq "S") {
        git remote remove origin
    } else {
        Write-Host "Operación cancelada." -ForegroundColor Red
        exit
    }
}

# Agregar el remoto
Write-Host "`nConfigurando remoto..." -ForegroundColor Cyan
git remote add origin "https://github.com/$githubUser/$repoName.git"

# Verificar que se agregó correctamente
Write-Host "`nRemoto configurado:" -ForegroundColor Green
git remote -v

# Verificar estado antes de push
Write-Host "`nEstado del repositorio:" -ForegroundColor Cyan
git status

# Hacer push
Write-Host "`nHaciendo push a GitHub..." -ForegroundColor Yellow
try {
    git push -u origin master
    Write-Host "`n¡Éxito! Tu repositorio está en GitHub." -ForegroundColor Green
    Write-Host "URL: https://github.com/$githubUser/$repoName" -ForegroundColor Cyan
} catch {
    Write-Host "`nError al hacer push. Verifica:" -ForegroundColor Red
    Write-Host "1. Que el repositorio existe en GitHub" -ForegroundColor Yellow
    Write-Host "2. Que tienes permisos para hacer push" -ForegroundColor Yellow
    Write-Host "3. Que tu nombre de usuario es correcto" -ForegroundColor Yellow
    Write-Host "`nSi el repositorio no existe, créalo en: https://github.com/new" -ForegroundColor Cyan
}

