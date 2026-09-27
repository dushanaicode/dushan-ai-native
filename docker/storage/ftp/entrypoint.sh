#!/bin/sh
set -eu
: "${FTP_USER:?FTP_USER is required}"
: "${FTP_PASS:?FTP_PASS is required}"
: "${FTP_PASV_ADDRESS:?FTP_PASV_ADDRESS is required}"
case "$FTP_USER" in *[!A-Za-z0-9_-]*|'') echo 'Invalid FTP_USER' >&2; exit 1;; esac
case "$FTP_PASV_ADDRESS" in *[!A-Za-z0-9_.:-]*|'') echo 'Invalid FTP_PASV_ADDRESS' >&2; exit 1;; esac
ftp_home="/home/vsftpd/$FTP_USER"
if ! id "$FTP_USER" >/dev/null 2>&1; then
    useradd --home-dir "$ftp_home" --shell /usr/sbin/nologin "$FTP_USER"
fi
printf '%s:%s\n' "$FTP_USER" "$FTP_PASS" | chpasswd
mkdir -p "$ftp_home/upload"
chown -R "$FTP_USER:$FTP_USER" "$ftp_home"
grep -qxF /usr/sbin/nologin /etc/shells || printf '%s\n' /usr/sbin/nologin >> /etc/shells
exec /usr/sbin/vsftpd /etc/vsftpd.conf "-opasv_address=$FTP_PASV_ADDRESS"
