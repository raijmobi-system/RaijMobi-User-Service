#!/bin/bash
set -e

# Lê as variáveis de ambiente (passadas pelo docker-compose)
DB_NAME="${DB_NAME:-raijmobi_user_db}"
DB_USER="${DB_USER:-raijmobi_user}"
DB_PASSWORD="${DB_PASSWORD:-raijmobi_pass}"
DB_HOST="${DB_HOST:-postgres-user}"
DB_PORT="${DB_PORT:-5432}"

export PGPASSWORD="$DB_PASSWORD"

echo "[$(date)] Iniciando manutenção do banco..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f /scripts/maintenance.sql
unset PGPASSWORD
echo "[$(date)] Manutenção concluída."