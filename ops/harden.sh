#!/usr/bin/env bash
# Durcissement serveur letterbookd (Ubuntu 26.04, hôte Docker).
# Couvre le groupe A du tri CIS : SSH, sudo, PAM, perms, logs, NTP, sysctl.
# Ne touche PAS à : IP forwarding (Docker), ufw/nftables (géré à part), USB,
# wifi/bluetooth, partitions, GDM, grub.
#
# Idempotent. Usage :
#   sudo ./harden.sh            # applique
#   sudo ./harden.sh --dry-run  # montre ce qui changerait

set -euo pipefail

DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1

log() { printf '\033[1;34m[*]\033[0m %s\n' "$*"; }
ok()  { printf '\033[1;32m[✓]\033[0m %s\n' "$*"; }
warn(){ printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
skip(){ printf '\033[0;37m[-]\033[0m %s\n' "$*"; }

run() {
    if [[ $DRY -eq 1 ]]; then
        echo "    would run: $*"
    else
        eval "$@"
    fi
}

# write_file <path> <mode> <owner> <content>
write_file() {
    local path=$1 mode=$2 owner=$3 content=$4
    if [[ -f $path ]] && diff -q <(echo "$content") "$path" >/dev/null 2>&1; then
        skip "$path déjà conforme"
        return
    fi
    if [[ $DRY -eq 1 ]]; then
        echo "    would write $path (mode $mode, owner $owner):"
        echo "$content" | sed 's/^/        /'
    else
        mkdir -p "$(dirname "$path")"
        echo "$content" > "$path"
        chmod "$mode" "$path"
        chown "$owner" "$path"
        ok "$path écrit"
    fi
}

ensure_perm() {
    local path=$1 mode=$2 owner=$3
    [[ -e $path ]] || { skip "$path absent"; return; }
    local cur_mode cur_owner
    cur_mode=$(stat -c '%a' "$path")
    cur_owner=$(stat -c '%U:%G' "$path")
    if [[ $cur_mode == "$mode" && $cur_owner == "$owner" ]]; then
        skip "$path déjà $mode $owner"
    else
        run "chmod $mode '$path' && chown $owner '$path'"
        ok "$path → $mode $owner"
    fi
}

[[ $EUID -eq 0 ]] || { echo "Lance en root (sudo)."; exit 1; }
[[ $DRY -eq 1 ]] && log "DRY-RUN — rien ne sera écrit."

###############################################################################
log "SSH"
###############################################################################
write_file /etc/ssh/sshd_config.d/99-hardening.conf 0600 root:root "# Durcissement SSH (CIS)
PermitRootLogin no
PermitEmptyPasswords no
MaxAuthTries 4
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2
LogLevel INFO
HostbasedAuthentication no
IgnoreRhosts yes
PermitUserEnvironment no
UsePAM yes
X11Forwarding no
AllowTcpForwarding no
"
# PasswordAuthentication : on NE force PAS 'no' tant qu'on n'a pas vérifié
# que des clés SSH sont posées pour tous les comptes humains.
if [[ -s /root/.ssh/authorized_keys ]] || getent passwd | awk -F: '$3>=1000 && $3<65534 {print $6}' | while read -r h; do [[ -s "$h/.ssh/authorized_keys" ]] && echo yes; done | grep -q yes; then
    warn "Clés SSH présentes, mais vérifie TOI-MÊME qu'elles couvrent ton accès avant de passer PasswordAuthentication à 'no'."
fi
run "sshd -t && systemctl reload ssh"
for f in /etc/ssh/ssh_host_*_key; do [[ -f $f ]] && ensure_perm "$f" 600 root:root; done
for f in /etc/ssh/ssh_host_*_key.pub; do [[ -f $f ]] && ensure_perm "$f" 644 root:root; done
ensure_perm /etc/ssh/sshd_config 600 root:root

###############################################################################
log "sudo"
###############################################################################
if ! dpkg -s sudo >/dev/null 2>&1; then
    run "apt-get install -y sudo"
fi
write_file /etc/sudoers.d/99-hardening 0440 root:root "# CIS sudo hardening
# Logs vont vers syslog -> /var/log/auth.log via rsyslog (sudo-rs n'a pas log_file).
Defaults use_pty
Defaults !visiblepw
Defaults timestamp_timeout=15
"
run "visudo -cf /etc/sudoers.d/99-hardening"

###############################################################################
log "PAM : complexité + historique + lockout"
###############################################################################
run "apt-get install -y libpam-pwquality"

write_file /etc/security/pwquality.conf 0644 root:root "# CIS password quality
minlen = 14
dcredit = -1
ucredit = -1
lcredit = -1
ocredit = -1
minclass = 4
maxrepeat = 3
difok = 8
enforce_for_root
"

# pwhistory dans /etc/pam.d/common-password
if ! grep -qE '^\s*password\s+required\s+pam_pwhistory.so' /etc/pam.d/common-password; then
    run "sed -i '/^password\\s*\\[success=.*\\]\\s*pam_unix.so/i password required pam_pwhistory.so remember=5 use_authtok' /etc/pam.d/common-password"
    ok "pam_pwhistory ajouté"
else
    skip "pam_pwhistory déjà configuré"
fi

# pam_faillock dans /etc/pam.d/common-auth
if ! grep -q 'pam_faillock.so' /etc/pam.d/common-auth; then
    run "sed -i '1i auth required pam_faillock.so preauth silent deny=5 unlock_time=900' /etc/pam.d/common-auth"
    # authfail après pam_unix : plus sûr de l'ajouter manuellement si pattern complexe
    warn "Ajoute manuellement après pam_unix.so dans /etc/pam.d/common-auth :"
    warn "  auth [default=die] pam_faillock.so authfail deny=5 unlock_time=900"
    warn "  auth sufficient    pam_faillock.so authsucc"
else
    skip "pam_faillock déjà configuré"
fi

###############################################################################
log "login.defs : âge mdp, umask"
###############################################################################
for kv in "PASS_MAX_DAYS 90" "PASS_MIN_DAYS 1" "PASS_WARN_AGE 7" "UMASK 027" "ENCRYPT_METHOD YESCRYPT"; do
    k=${kv%% *}; v=${kv#* }
    if grep -qE "^\s*${k}\s" /etc/login.defs; then
        run "sed -i 's|^\\s*${k}\\s.*|${k}  ${v}|' /etc/login.defs"
    else
        run "echo '${k}  ${v}' >> /etc/login.defs"
    fi
done
ok "login.defs mis à jour"

###############################################################################
log "umask 027 + TMOUT dans /etc/profile.d"
###############################################################################
write_file /etc/profile.d/99-hardening.sh 0644 root:root "# CIS umask + inactivity timeout
umask 027
readonly TMOUT=900
export TMOUT
"

###############################################################################
log "Permissions /etc : passwd/shadow/group + backups"
###############################################################################
ensure_perm /etc/passwd    644 root:root
ensure_perm /etc/passwd-   644 root:root
ensure_perm /etc/group     644 root:root
ensure_perm /etc/group-    644 root:root
ensure_perm /etc/shadow    640 root:shadow
ensure_perm /etc/shadow-   640 root:shadow
ensure_perm /etc/gshadow   640 root:shadow
ensure_perm /etc/gshadow-  640 root:shadow
ensure_perm /etc/shells    644 root:root

###############################################################################
log "Permissions cron.*"
###############################################################################
ensure_perm /etc/crontab        600 root:root
for d in /etc/cron.d /etc/cron.hourly /etc/cron.daily /etc/cron.weekly /etc/cron.monthly; do
    ensure_perm "$d" 700 root:root
done
# at/cron allow
[[ -f /etc/cron.deny ]] && run "rm /etc/cron.deny"
[[ -f /etc/cron.allow ]] || run "touch /etc/cron.allow"
ensure_perm /etc/cron.allow 640 root:root

###############################################################################
log "Permissions /var/log"
###############################################################################
for f in /var/log/auth.log /var/log/syslog /var/log/messages; do
    [[ -f $f ]] && ensure_perm "$f" 640 syslog:adm
done
[[ -f /var/log/lastlog ]] && ensure_perm /var/log/lastlog 664 root:utmp
[[ -f /var/log/wtmp   ]] && ensure_perm /var/log/wtmp     664 root:utmp
[[ -f /var/log/btmp   ]] && ensure_perm /var/log/btmp     600 root:utmp

###############################################################################
log "journald persistant + rsyslog"
###############################################################################
write_file /etc/systemd/journald.conf.d/99-hardening.conf 0644 root:root "[Journal]
Storage=persistent
Compress=yes
ForwardToSyslog=yes
"
run "systemctl restart systemd-journald"
run "apt-get install -y rsyslog"
run "systemctl enable --now rsyslog"

###############################################################################
log "Synchro horaire (chrony OU timesyncd, pas les deux)"
###############################################################################
if systemctl is-active --quiet chrony || systemctl is-active --quiet chronyd; then
    ok "chrony déjà actif, on le garde"
    # Vérif qu'il a bien des sources
    if command -v chronyc >/dev/null; then
        chronyc -n sources 2>/dev/null | head -5 || true
    fi
    # S'assurer que timesyncd est bien éteint (règle CIS « single service »)
    run "systemctl disable --now systemd-timesyncd 2>/dev/null || true"
else
    run "apt-get install -y systemd-timesyncd || true"
    run "systemctl enable --now systemd-timesyncd"
    if ! grep -qE '^\s*NTP=' /etc/systemd/timesyncd.conf 2>/dev/null; then
        run "sed -i 's|^#NTP=.*|NTP=0.fr.pool.ntp.org 1.fr.pool.ntp.org 2.fr.pool.ntp.org|' /etc/systemd/timesyncd.conf"
        run "systemctl restart systemd-timesyncd"
    fi
fi

###############################################################################
log "sysctl : réseau + ASLR + core dumps"
###############################################################################
write_file /etc/sysctl.d/99-hardening.conf 0644 root:root "# CIS sysctl hardening
# NB: net.ipv4.ip_forward NON touché (Docker en a besoin)

# ICMP
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1

# Source routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0

# ICMP redirects (acceptés)
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0

# ICMP redirects (émis) — hôte, pas routeur
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0

# Reverse path filtering
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Log martian packets
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1

# SYN flood
net.ipv4.tcp_syncookies = 1

# Router advertisements IPv6
net.ipv6.conf.all.accept_ra = 0
net.ipv6.conf.default.accept_ra = 0

# Core dumps + ASLR + ptrace
fs.suid_dumpable = 0
kernel.randomize_va_space = 2
kernel.yama.ptrace_scope = 1
"
run "sysctl --system >/dev/null"

# Core dumps limite
if ! grep -qE '^\*\s+hard\s+core\s+0' /etc/security/limits.d/99-hardening.conf 2>/dev/null; then
    write_file /etc/security/limits.d/99-hardening.conf 0644 root:root "* hard core 0
"
fi

###############################################################################
log "AppArmor"
###############################################################################
if command -v aa-status >/dev/null; then
    if aa-status --enabled 2>/dev/null; then
        ok "AppArmor actif"
        aa-status 2>/dev/null | head -4
    else
        warn "AppArmor installé mais pas enforcing"
    fi
else
    run "apt-get install -y apparmor apparmor-utils"
fi

###############################################################################
log "Mises à jour automatiques de sécurité"
###############################################################################
run "apt-get install -y unattended-upgrades"
run "dpkg-reconfigure -f noninteractive unattended-upgrades"

###############################################################################
if [[ $DRY -eq 1 ]]; then
    log "DRY-RUN terminé — rien de modifié. Relance sans --dry-run pour appliquer."
else
    ok "Durcissement appliqué. Un reboot est conseillé pour que tout prenne."
fi
