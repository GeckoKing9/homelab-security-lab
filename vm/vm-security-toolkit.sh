#!/usr/bin/env bash
# ============================================================================
#  VM SECURITY TOOLKIT INSTALLER  —  Ubuntu 24.04
#  Curated full-spectrum kit: OSINT + CTF/HTB + Red-team + Blue-team/DFIR
#  Companion to the "cybersec-master-bookmarks" collection.
#
#  SNAPSHOT THE VM BEFORE RUNNING. Then:  bash vm-security-toolkit.sh
#  Read it top-to-bottom first — nothing here is hidden. Run whole, or by phase.
# ============================================================================
set -uo pipefail

# Toggle the big/slow installs (Metasploit, Sliver, SecLists ~2.5G, BloodHound CE).
# 0 = skip (recommended first run),  1 = install.
INSTALL_HEAVY=0

log(){ echo -e "\n\033[1;36m==> $*\033[0m"; }

# ---- tool catalog (powers --list here AND the installed `sectools` command) --
read -r -d '' CATALOG <<'CATEOF' || true
CYBERSEC VM TOOLKIT — tool reference   (usage:  sectools [name]  |  sectools = full list)

OSINT
  sherlock <user>              find a username across 400+ social networks
  maigret <user>              username -> profiles + extracted account info
  holehe <email>              which sites is this email registered on
  theHarvester -d <domain>    harvest emails/subdomains/hosts for a domain
  socialscan <email|user>     check email/username availability & registration
  phoneinfoga scan -n <num>   phone number recon (carrier, footprint)
  spiderfoot                  automated OSINT web UI (launch: cd ~/tools/spiderfoot && .venv/bin/python3 sf.py -l 127.0.0.1:5001)

RECON  (chain them: subfinder -> httpx -> nuclei)
  subfinder -d <domain>       passive subdomain enumeration
  httpx                       probe hosts: live/status/tech/title (pipe hosts in)
  nuclei -u <url>             template-based vulnerability scanner
  katana -u <url>             modern web crawler / spider
  naabu -host <target>        fast port scanner
  dnsx                        DNS toolkit (resolve/records; pipe domains in)
  ffuf -u <url>/FUZZ -w <wl>  fast web fuzzer (dirs/params/vhosts)
  amass enum -d <domain>      deep attack-surface / subdomain mapping

OFFENSIVE
  nmap -sC -sV <target>       port + service + default-script scan
  sqlmap -u "<url>" --batch   automatic SQL-injection exploitation
  hashcat -m <mode> <h> <wl>  GPU password cracking (mode 22000 = WPA2)
  john --wordlist=<wl> <hash> CPU password cracker
  hydra -l <u> -P <wl> <svc>  online login brute-forcer
  gobuster dir -u <url> -w    directory/file brute-force
  feroxbuster -u <url>        recursive content discovery
  nikto -h <url>              web server misconfig scanner
  whatweb <url>               fingerprint web technologies
  wireshark                   packet capture & analysis (GUI)
  yara <rules> <file>         pattern-match files / malware

RED-TEAM / ACTIVE DIRECTORY
  secretsdump.py / wmiexec.py SMB/Kerberos scripts (also psexec.py, GetNPUsers.py, GetUserSPNs.py ...)
  nxc <proto> <target> -u -p  NetExec: AD/network swiss-army (smb/winrm/ldap/...)
  bloodhound-python -d -u -p  collect AD data for BloodHound (-c all)
  kerbrute userenum -d <dom>  Kerberos username/password enumeration
  Responder -I <iface>        poison LLMNR/NBT-NS -> capture creds (~/tools/Responder)
  evil-winrm -i -u -p         interactive Windows remote shell

BLUE-TEAM / DFIR / MALWARE
  vol -f <mem> <plugin>       Volatility3 memory forensics (e.g. windows.pslist)
  capa <file>                 detect malware capabilities (ATT&CK-mapped)
  floss <file>                extract obfuscated/encoded strings
  suricata -r <pcap>          IDS/IPS + deep packet inspection
  clamscan -r <path>          antivirus scan
  velociraptor gui            endpoint DFIR & hunting (~/tools/velociraptor)

HEAVY (only if INSTALL_HEAVY=1)
  msfconsole                  Metasploit exploitation framework
  sliver-server               Sliver C2 framework
  /usr/share/seclists         the SecLists wordlist collection
CATEOF

USAGE="VM Security Toolkit installer — Ubuntu 24.04
  bash vm-security-toolkit.sh            install the curated kit (edit INSTALL_HEAVY at top for the big stuff)
  bash vm-security-toolkit.sh --list     print the full annotated tool list (no install)
  bash vm-security-toolkit.sh --help     this help + the tool list
After installing, the same reference is available anytime as:  sectools  (or  sectools <name>)"

case "${1:-}" in
  -h|--help)        echo "$USAGE"; echo; echo "$CATALOG"; exit 0 ;;
  --list|--catalog) echo "$CATALOG"; exit 0 ;;
esac

# --- PHASE 0: base + package managers --------------------------------------
log "Phase 0: base packages"
sudo apt-get update
sudo apt-get install -y build-essential git curl wget jq unzip ruby-dev \
     python3-pip python3-venv python3-dev libssl-dev libffi-dev \
     pipx golang-go docker.io docker-compose-v2 cargo rustc pkg-config
pipx ensurepath
# put Go binaries + pipx on PATH for this session and future shells
export PATH="$PATH:$HOME/go/bin:$HOME/.local/bin"
grep -q 'go/bin' ~/.bashrc || echo 'export PATH="$PATH:$HOME/go/bin:$HOME/.local/bin"' >> ~/.bashrc
sudo usermod -aG docker "$USER" || true   # log out/in later for rootless docker

# install the `sectools` reference command (sectools = full list, sectools <name> = one tool)
echo "$CATALOG" | sudo tee /usr/local/share/sectools-catalog.txt >/dev/null
sudo tee /usr/local/bin/sectools >/dev/null <<'SH'
#!/usr/bin/env bash
F=/usr/local/share/sectools-catalog.txt
if [ -n "${1:-}" ]; then grep -i --color=auto -- "$1" "$F"; else less -R "$F" 2>/dev/null || cat "$F"; fi
SH
sudo chmod +x /usr/local/bin/sectools

# install the `newtool` helper: in any freshly-cloned Python tool dir, run `newtool`
# to auto-create .venv + install requirements (avoids the PEP 668 externally-managed wall)
grep -q 'newtool()' ~/.bashrc || cat >> ~/.bashrc <<'NT'

# newtool — cd into a cloned Python tool, run `newtool`, get a ready+active venv
newtool() {
  local d="${1:-.}"; cd "$d" || return 1
  [ -d .venv ] || { echo "[newtool] creating venv..."; python3 -m venv .venv || return 1; }
  source .venv/bin/activate
  python -m pip install -q --upgrade pip
  if   [ -f requirements.txt ]; then echo "[newtool] installing requirements.txt..."; pip install -r requirements.txt
  elif [ -f pyproject.toml ] || [ -f setup.py ]; then echo "[newtool] installing package..."; pip install -e .
  else echo "[newtool] no requirements found — empty venv is ready."; fi
  echo "[newtool] venv ACTIVE — run the tool (e.g. python main.py ...), then type 'deactivate'."
}
NT

# --- PHASE 1: OSINT CLIs (pipx = isolated, updatable) ----------------------
log "Phase 1: OSINT tools"
for p in sherlock-project maigret holehe theHarvester socialscan; do
  pipx install "$p" || pipx upgrade "$p" || true
done
# phoneinfoga (Go binary via official installer)
curl -fsSL https://raw.githubusercontent.com/sundowndev/phoneinfoga/master/support/scripts/install | bash || true
sudo mv ./phoneinfoga /usr/local/bin/ 2>/dev/null || true
# SpiderFoot (git + venv, it's a web app you launch with: python3 sf.py -l 127.0.0.1:5001)
[ -d ~/tools/spiderfoot ] || git clone https://github.com/smicallef/spiderfoot ~/tools/spiderfoot
python3 -m venv ~/tools/spiderfoot/.venv && ~/tools/spiderfoot/.venv/bin/pip install -r ~/tools/spiderfoot/requirements.txt || true

# --- PHASE 2: recon / ProjectDiscovery stack -------------------------------
log "Phase 2: recon stack (subfinder, httpx, nuclei, katana, naabu, dnsx...)"
go install -v github.com/projectdiscovery/pdtm/cmd/pdtm@latest
"$HOME/go/bin/pdtm" -install-all || true
go install github.com/ffuf/ffuf/v2@latest || true
sudo snap install amass 2>/dev/null || go install -v github.com/owasp-amass/amass/v4/...@master || true
"$HOME/go/bin/nuclei" -update-templates 2>/dev/null || true

# --- PHASE 3: offensive classics (apt) -------------------------------------
log "Phase 3: offensive classics"
sudo apt-get install -y nmap tcpdump wireshark netcat-traditional hydra john \
     hashcat sqlmap gobuster nikto whatweb dnsutils yara
# feroxbuster (not in Ubuntu repos — official install script)
curl -sL https://raw.githubusercontent.com/epi052/feroxbuster/main/install-nix.sh | bash 2>/dev/null && sudo mv ./feroxbuster /usr/local/bin/ 2>/dev/null || true

# --- PHASE 4: red-team / AD ------------------------------------------------
log "Phase 4: red-team / Active Directory"
pipx install git+https://github.com/fortra/impacket.git || true
pipx install git+https://github.com/Pennyw0rth/NetExec || true   # nxc (ex-CrackMapExec)
pipx install bloodhound || true       # bloodhound-python collector
go install github.com/ropnop/kerbrute@latest || true
[ -d ~/tools/Responder ] || git clone https://github.com/lgandx/Responder ~/tools/Responder
sudo gem install evil-winrm || true

# --- PHASE 5: blue-team / DFIR / malware -----------------------------------
log "Phase 5: blue-team / DFIR"
pipx install volatility3 || true      # memory forensics
pipx install flare-capa || true       # capability detection
pipx install flare-floss || true      # string deobfuscation
sudo apt-get install -y suricata clamav
# Velociraptor (single static binary)
VR=$(curl -s https://api.github.com/repos/Velocidex/velociraptor/releases/latest | grep -o 'https.*linux-amd64' | head -1)
[ -n "$VR" ] && wget -qO ~/tools/velociraptor "$VR" && chmod +x ~/tools/velociraptor || true

# --- HEAVY / OPTIONAL (set INSTALL_HEAVY=1 above) --------------------------
if [ "$INSTALL_HEAVY" = "1" ]; then
  log "HEAVY: Metasploit"
  # Download to a private mktemp dir, not a fixed /tmp path: a predictable name in
  # world-writable /tmp lets a local user pre-plant or symlink the file between download
  # and the `sudo` that runs it. The dir is 0700 and cleaned up after.
  msfdir="$(mktemp -d)" && msfinstall="$msfdir/msfinstall"
  if curl -fsSL https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb -o "$msfinstall"; then
    chmod +x "$msfinstall" && sudo "$msfinstall" || true
  fi
  rm -rf "$msfdir"

  log "HEAVY: Sliver C2"
  curl https://sliver.sh/install | sudo bash || true

  log "HEAVY: SecLists wordlists (~2.5G)"
  sudo git clone --depth 1 https://github.com/danielmiessler/SecLists /usr/share/seclists || true

  log "HEAVY: BloodHound CE (Docker) — start with: cd ~/tools/bhce && docker compose up -d"
  mkdir -p ~/tools/bhce && curl -sL https://raw.githubusercontent.com/SpecterOps/BloodHound/main/examples/docker-compose/docker-compose.yml -o ~/tools/bhce/docker-compose.yml || true
fi

# --- PHASE 6: verify -------------------------------------------------------
log "Phase 6: verify (versions)"
for t in nmap sqlmap hashcat john nuclei subfinder httpx ffuf amass \
         sherlock maigret holehe nxc secretsdump.py vol yara suricata; do
  printf "  %-22s " "$t"
  if command -v "$t" >/dev/null; then
    ver=$("$t" --version 2>/dev/null | head -1); [ -z "$ver" ] && ver=$("$t" -version 2>/dev/null | head -1)
    echo "${ver:-ok}"
  else echo "MISSING"; fi
done
log "Done. Open a new shell (or 'source ~/.bashrc') so PATH picks up new tools."
echo "Blue-team platforms (MISP/OpenCTI) are Docker stacks — say the word and I'll add compose files."
