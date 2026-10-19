#!/usr/bin/env bash
# Prava.uz — kunlik zaxira: PostgreSQL (pg_dump, custom format) + media/ (savol rasmlari).
#
# Cron (deploy/prava_uz.cron -> /etc/cron.d/prava_uz):
#   30 3 * * * prava /srv/prava_uz/deploy/backup.sh >> /var/log/prava_uz/backup.log 2>&1
#
# Qo'lda: sudo -u prava /srv/prava_uz/deploy/backup.sh
# Tiklash:
#   pg_restore --clean --if-exists --no-owner -h localhost -U prava -d prava_uz /var/backups/prava_uz/db-YYYYmmdd-HHMM.dump
#   tar -xzf /var/backups/prava_uz/media-YYYYmmdd-HHMM.tar.gz -C /srv/prava_uz
#
# Sozlash (ixtiyoriy, muhit o'zgaruvchilari): APP_DIR, BACKUP_DIR, KEEP_DAYS.
# Baza ulanishi .env dan o'qiladi (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT).

set -euo pipefail

APP_DIR="${APP_DIR:-/srv/prava_uz}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/prava_uz}"
KEEP_DAYS="${KEEP_DAYS:-14}"
ENV_FILE="$APP_DIR/.env"

log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
fail() { log "XATO: $*" >&2; exit 1; }

[ -r "$ENV_FILE" ] || fail "$ENV_FILE topilmadi yoki o'qib bo'lmaydi"

# .env ni `source` qilmaymiz (qiymatlarda maxsus belgilar bo'lishi mumkin) — faqat kerakli kalitlarni o'qiymiz
env_get() {
    local value
    value="$(grep -E "^$1=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- | tr -d '\r')" || true
    value="${value%\"}"; value="${value#\"}"
    printf '%s' "${value:-$2}"
}

DB_ENGINE="$(env_get DB_ENGINE sqlite)"
[ "$DB_ENGINE" = "postgres" ] || fail "DB_ENGINE=postgres emas ($DB_ENGINE) — bu skript faqat PostgreSQL uchun"
DB_NAME="$(env_get DB_NAME prava_uz)"
DB_USER="$(env_get DB_USER prava)"
DB_HOST="$(env_get DB_HOST localhost)"
DB_PORT="$(env_get DB_PORT 5432)"
PGPASSWORD="$(env_get DB_PASSWORD '')"
export PGPASSWORD

command -v pg_dump >/dev/null || fail "pg_dump topilmadi (sudo apt install postgresql-client)"

umask 077   # zaxiralarda parol xeshlari bor — faqat egasi o'qiy olsin
mkdir -p "$BACKUP_DIR"

STAMP="$(date +%Y%m%d-%H%M)"
DB_FILE="$BACKUP_DIR/db-$STAMP.dump"
MEDIA_FILE="$BACKUP_DIR/media-$STAMP.tar.gz"

log "Boshlandi: $DB_NAME@$DB_HOST:$DB_PORT -> $BACKUP_DIR"

# 1) Baza. Avval .part ga yozamiz — yarim qolgan fayl "tayyor zaxira" bo'lib ko'rinmasin
pg_dump --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" --no-password \
    --format=custom --compress=9 --no-owner --file="$DB_FILE.part" "$DB_NAME"
# Fayl o'qiladimi — tekshiruv (buzilgan dump'ni saqlamaymiz)
pg_restore --list "$DB_FILE.part" >/dev/null || fail "pg_restore dump'ni o'qiy olmadi"
mv "$DB_FILE.part" "$DB_FILE"

# 2) Media (yuklangan savol rasmlari)
if [ -d "$APP_DIR/media" ]; then
    tar -czf "$MEDIA_FILE.part" -C "$APP_DIR" media
    mv "$MEDIA_FILE.part" "$MEDIA_FILE"
fi

# 3) Eski zaxiralarni tozalash (KEEP_DAYS kundan eski) — faqat shu skript yaratgan fayl nomlari
find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'db-*.dump' -o -name 'media-*.tar.gz' \) -mtime +"$KEEP_DAYS" -print -delete \
    | sed 's/^/  o'"'"'chirildi: /'

log "Tayyor: $(du -h "$DB_FILE" | cut -f1) baza, $( [ -f "$MEDIA_FILE" ] && du -h "$MEDIA_FILE" | cut -f1 || echo 0) media"
