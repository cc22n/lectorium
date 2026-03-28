#!/bin/bash
# backup_postgres.sh — Backup automatico de PostgreSQL
# Uso: ./scripts/backup_postgres.sh
# Recomendado: agregar a crontab del VPS
#   0 2 * * * /path/to/lectorium/scripts/backup_postgres.sh >> /var/log/lectorium_backup.log 2>&1

set -euo pipefail

BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/lectorium_${TIMESTAMP}.sql.gz"
KEEP_DAYS=7

# Variables de entorno necesarias (cargadas desde docker exec o crontab)
: "${POSTGRES_USER:=lectorium}"
: "${POSTGRES_DB:=lectorium}"

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Iniciando backup de ${POSTGRES_DB}..."

# Ejecutar pg_dump dentro del contenedor postgres
docker compose -f /path/to/lectorium/docker-compose.prod.yml exec -T postgres \
    pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "${BACKUP_FILE}"

echo "[$(date)] Backup guardado: ${BACKUP_FILE} ($(du -sh "${BACKUP_FILE}" | cut -f1))"

# Eliminar backups antiguos
find "${BACKUP_DIR}" -name "lectorium_*.sql.gz" -mtime +${KEEP_DAYS} -delete
echo "[$(date)] Backups anteriores a ${KEEP_DAYS} dias eliminados."

echo "[$(date)] Backup completado."
