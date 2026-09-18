#!/usr/bin/env python3
"""MASTER cybersecurity bookmark tree v2 — OSINT / Red / Blue / Learn.
Existing tools + researched additions, deduped, ranked by real usefulness,
each titled with a plain-English description. Emits Netscape HTML (Firefox
one-click import) + a flat urls.txt for liveness checking."""
import html, io, re

def clean(name):
    # strip leading emoji/symbols/whitespace from folder names
    return re.sub(r'^[^\w(]+', '', name).strip()

# top -> subfolder -> [(title_with_description, url), ...]  (ranked: best first)
TREE = {
"\U0001F50D OSINT": {
  "⭐ Start Here (all-in-one)": [
    ("Max Intel — 100+ free lookup tools, no signup (email/user/phone/domain)", "https://maxintel.org/"),
    ("OSINT Industries — email/phone/username → connected accounts", "https://osint.industries/"),
    ("Epieos — email/phone reverse lookup → linked accounts + Google data", "https://epieos.com/"),
    ("SpiderFoot — automate OSINT across 200+ data sources", "https://github.com/smicallef/spiderfoot"),
    ("Maltego (Community) — visual link-analysis graphs", "https://www.maltego.com/"),
  ],
  "People & Identity": [
    ("IDCrawl — best free people-search aggregator (US)", "https://www.idcrawl.com/"),
    ("TruePeopleSearch — free US name/phone/address", "https://www.truepeoplesearch.com/"),
    ("FastPeopleSearch — free US people search, strong coverage", "https://www.fastpeoplesearch.com/"),
    ("ThatsThem — free reverse phone/email/address", "https://thatsthem.com/"),
    ("Spokeo — people search (freemium)", "https://www.spokeo.com/"),
    ("WebMii — name → web presence & profiles", "https://webmii.com/"),
  ],
  "Username enumeration": [
    ("WhatsMyName — check a username across 600+ sites (web)", "https://whatsmyname.app/"),
    ("Sherlock — hunt a username across social networks (tool)", "https://github.com/sherlock-project/sherlock"),
    ("Maigret — username → profiles + extracted info (tool)", "https://github.com/soxoj/maigret"),
    ("Blackbird — fast username/email search (tool)", "https://github.com/p1ngul1n0/blackbird"),
    ("Namechk — username/domain availability across platforms", "https://namechk.com/"),
  ],
  "Email & breach lookup": [
    ("Have I Been Pwned — is this email in a known breach?", "https://haveibeenpwned.com/"),
    ("Hudson Rock (Cavalier) — is this email/domain in infostealer logs? (free)", "https://cavalier.hudsonrock.com/"),
    ("DeHashed — breach search engine (freemium)", "https://dehashed.com/"),
    ("Intelligence X — leaks/pastes/darkweb selector search", "https://intelx.io/"),
    ("CheckLeaked — breach check showing the source (free searches)", "https://checkleaked.cc/"),
    ("Scattered Secrets — see cracked plaintext for domains you own (free)", "https://scatteredsecrets.com/"),
    ("Holehe — which sites an email is registered on (tool)", "https://github.com/megadose/holehe"),
    ("EmailRep — email reputation & risk profile", "https://emailrep.io/"),
  ],
  "Phone": [
    ("PhoneInfoga — best phone OSINT: carrier, footprint (tool)", "https://github.com/sundowndev/phoneinfoga"),
    ("NumLookup — free reverse phone lookup", "https://www.numlookup.com/"),
    ("Truecaller — caller ID / name lookup", "https://www.truecaller.com/"),
    ("whocalld — quick caller info", "https://whocalld.com/"),
  ],
  "Face & reverse image": [
    ("PimEyes — face search across the web (freemium, powerful)", "https://pimeyes.com/"),
    ("FaceCheck.ID — face search (free tier)", "https://facecheck.id/"),
    ("Yandex Images — best reverse-image for faces & places", "https://yandex.com/images/"),
    ("Google Lens — reverse image / identify objects", "https://lens.google.com/"),
    ("TinEye — reverse image, finds oldest/exact match", "https://tineye.com/"),
  ],
  "Geolocation (photo → place)": [
    ("GeoSpy — AI predicts location from a photo", "https://geospy.ai/"),
    ("Picarta — AI photo geolocation vs global database", "https://picarta.ai/"),
    ("Overpass Turbo — query OpenStreetMap features to pin a spot", "https://overpass-turbo.eu/"),
    ("SunCalc — shadows/sun → time & orientation (chronolocation)", "https://www.suncalc.org/"),
    ("Google Earth (web) — imagery + historical timeline", "https://earth.google.com/web/"),
    ("Mapillary — crowd street-level imagery (beyond Google)", "https://www.mapillary.com/app/"),
  ],
  "Infrastructure & domain": [
    ("crt.sh — certificate transparency → find subdomains", "https://crt.sh/"),
    ("Netlas.io — internet asset search, big free tier", "https://netlas.io/"),
    ("Censys Search — hosts, certs & services", "https://search.censys.io/"),
    ("Shodan — search internet-connected devices", "https://www.shodan.io/"),
    ("urlscan.io — scan & screenshot any URL, see what it loads", "https://urlscan.io/"),
    ("LeakIX — find exposed/misconfigured services (open DBs, git, env)", "https://leakix.net/"),
    ("SecurityTrails — historical DNS & subdomains", "https://securitytrails.com/"),
    ("DNSDumpster — free domain recon map", "https://dnsdumpster.com/"),
    ("ViewDNS.info — 30+ DNS/whois tools in one page", "https://viewdns.info/"),
    ("BuiltWith — what tech a website runs on", "https://builtwith.com/"),
    ("Wappalyzer — tech-stack profiler (free)", "https://www.wappalyzer.com/"),
    ("web-check.xyz — all-in-one site OSINT dashboard", "https://web-check.xyz/"),
  ],
  "IP, network & ASN": [
    ("bgp.he.net — ASN/BGP/IP relationships", "https://bgp.he.net/"),
    ("GreyNoise — is this IP mass-scanning the internet? (context)", "https://viz.greynoise.io/"),
    ("IPinfo.io — IP geolocation & ASN", "https://ipinfo.io/"),
    ("AbuseIPDB — IP abuse reputation", "https://www.abuseipdb.com/"),
    ("Spur.us — detect VPN/proxy/residential IPs", "https://spur.us/"),
    ("WiGLE — wardriving / global WiFi network map", "https://wigle.net/"),
  ],
  "Social media": [
    ("Social-Media-OSINT Collection — curated per-platform tools (list)", "https://github.com/osintambition/Social-Media-OSINT-Tools-Collection"),
    ("X / Twitter Advanced Search", "https://twitter.com/search-advanced"),
    ("TGStat — Telegram channel analytics & search", "https://tgstat.com/"),
    ("Telegago — Google search across public Telegram", "https://cse.google.com/cse?cx=006368593537057042503:efxu7xprihg"),
    ("Imginn — view public Instagram anonymously", "https://imginn.com/"),
    ("Osintgram — pull metadata/followers from public IG (tool)", "https://github.com/Datalux/Osintgram"),
    ("Social Searcher — real-time social mention search", "https://www.social-searcher.com/"),
  ],
  "Business, entity & records": [
    ("OpenCorporates — largest open company database", "https://opencorporates.com/"),
    ("OCCRP Aleph — investigative-journalism data trove", "https://aleph.occrp.org/"),
    ("OpenSanctions — sanctions / PEP / watchlists", "https://www.opensanctions.org/"),
    ("ICIJ Offshore Leaks — Panama/Paradise Papers", "https://offshoreleaks.icij.org/"),
    ("SEC EDGAR — US public company filings", "https://www.sec.gov/cgi-bin/browse-edgar"),
  ],
  "Transport (flights & ships)": [
    ("ADS-B Exchange — unfiltered live flight tracking", "https://globe.adsbexchange.com/"),
    ("Flightradar24 — flight tracking", "https://www.flightradar24.com/"),
    ("MarineTraffic — live ship tracking", "https://www.marinetraffic.com/"),
    ("VesselFinder — ship tracking", "https://www.vesselfinder.com/"),
  ],
  "Capture & workflow": [
    ("Hunchly — auto-capture every page in an investigation (evidence)", "https://www.hunch.ly/"),
    ("SingleFile — save a full web page as one HTML file (extension)", "https://github.com/gildas-lormeau/SingleFile"),
    ("Mitaka — right-click any selector → OSINT lookups (extension)", "https://github.com/ninoseki/mitaka"),
    ("archive.today — snapshot pages the Wayback Machine won't", "https://archive.ph/"),
    ("Wayback Machine — historical page archive", "https://web.archive.org/"),
  ],
  "Meta-hubs & directories": [
    ("Bellingcat Toolkit — gold-standard investigator resource list", "https://bellingcat.gitbook.io/toolkit"),
    ("IntelTechniques Tools — Bazzell's custom search tools", "https://inteltechniques.com/tools/"),
    ("Technisette (start.me) — huge maintained OSINT collection", "https://start.me/p/rxRbpo/osint"),
    ("Awesome OSINT — the classic GitHub list", "https://github.com/jivoi/awesome-osint"),
    ("Awesome Hacker Search Engines — Shodan-style search engines", "https://github.com/edoardottt/awesome-hacker-search-engines"),
    ("OSINT Framework — categorized directory (a bit dated)", "https://osintframework.com/"),
    ("GitHub Code Search — hunt leaked secrets & code", "https://cs.github.com/"),
  ],
},
"⚔️ Red Team": {
  "⭐ Start Here (bible & frameworks)": [
    ("HackTricks — the pentester's methodology bible (everything)", "https://book.hacktricks.xyz/"),
    ("PayloadsAllTheThings — payloads & bypasses for every vuln", "https://github.com/swisskyrepo/PayloadsAllTheThings"),
    ("MITRE ATT&CK — the adversary tactics & techniques matrix", "https://attack.mitre.org/"),
    ("Metasploit Framework — the classic exploitation framework", "https://www.metasploit.com/"),
    ("Red-Teaming-Toolkit — huge curated offensive-tool list", "https://github.com/infosecn1nja/Red-Teaming-Toolkit"),
    ("RedTeam-Tools — techniques + tools by kill-chain phase", "https://github.com/A-poc/RedTeam-Tools"),
  ],
  "Recon & enumeration": [
    ("Subfinder — fast passive subdomain discovery (tool)", "https://github.com/projectdiscovery/subfinder"),
    ("httpx — probe hosts for status/tech/title (tool)", "https://github.com/projectdiscovery/httpx"),
    ("Nuclei — template-based vulnerability scanner (huge) (tool)", "https://github.com/projectdiscovery/nuclei"),
    ("Katana — next-gen web crawler/spider (tool)", "https://github.com/projectdiscovery/katana"),
    ("Amass — deep attack-surface mapping (tool)", "https://github.com/owasp-amass/amass"),
    ("ffuf — fast web fuzzer: dirs/params/vhosts (tool)", "https://github.com/ffuf/ffuf"),
    ("Aquatone — screenshot hosts at scale for triage (tool)", "https://github.com/michenriksen/aquatone"),
    ("Nmap — the port & service scanner", "https://nmap.org/"),
  ],
  "Web app hacking": [
    ("Burp Suite — the web pentest proxy (Community free)", "https://portswigger.net/burp"),
    ("HackTricks — web-vulnerability methodology", "https://book.hacktricks.xyz/pentesting-web/web-vulnerabilities-methodology"),
    ("sqlmap — automatic SQL-injection exploitation (tool)", "https://github.com/sqlmapproject/sqlmap"),
    ("feroxbuster — fast content/directory brute-force (tool)", "https://github.com/epi052/feroxbuster"),
    ("XSStrike — advanced XSS discovery (tool)", "https://github.com/s0md3v/XSStrike"),
    ("revshells.com — reverse-shell command generator", "https://www.revshells.com/"),
    ("GTFOBins — abuse Unix binaries for privesc/bypass", "https://gtfobins.github.io/"),
    ("LOLBAS — abuse built-in Windows binaries", "https://lolbas-project.github.io/"),
  ],
  "Active Directory & network": [
    ("BloodHound — map Active Directory attack paths (essential)", "https://github.com/SpecterOps/BloodHound"),
    ("NetExec (nxc) — swiss-army AD/network tool (ex-CrackMapExec)", "https://github.com/Pennyw0rth/NetExec"),
    ("Impacket — SMB/Kerberos/MSRPC protocol toolkit", "https://github.com/fortra/impacket"),
    ("Responder — LLMNR/NBT-NS poisoning → capture creds", "https://github.com/lgandx/Responder"),
    ("Certipy — Active Directory Certificate Services abuse", "https://github.com/ly4k/Certipy"),
    ("Evil-WinRM — Windows remote-shell for pentesters", "https://github.com/Hackplayers/evil-winrm"),
    ("Kerbrute — Kerberos username/password enumeration", "https://github.com/ropnop/kerbrute"),
  ],
  "C2 frameworks": [
    ("Sliver — modern open-source C2 (BishopFox)", "https://github.com/BishopFox/sliver"),
    ("Havoc — polished modern C2 with strong UX", "https://github.com/HavocFramework/Havoc"),
    ("Mythic — modular multi-platform C2", "https://github.com/its-a-feature/Mythic"),
    ("Villain — lightweight multi-session shell handler", "https://github.com/t3l3machus/Villain"),
  ],
  "Passwords & cracking": [
    ("Hashcat — GPU password cracking (the standard)", "https://hashcat.net/hashcat/"),
    ("John the Ripper — versatile password cracker", "https://www.openwall.com/john/"),
    ("hashes.com — identify & look up hashes", "https://hashes.com/en/decrypt/hash"),
    ("CrackStation — free wordlist hash lookup", "https://crackstation.net/"),
    ("Hydra — online login brute-forcer", "https://github.com/vanhauser-thc/thc-hydra"),
    ("SecLists — the essential wordlist collection", "https://github.com/danielmiessler/SecLists"),
  ],
  "Privilege escalation & post-ex": [
    ("PEASS-ng (winPEAS/linPEAS) — privesc enumeration scripts", "https://github.com/peass-ng/PEASS-ng"),
    ("Mimikatz — extract Windows credentials from memory", "https://github.com/gentilkiwi/mimikatz"),
    ("pspy — watch processes/cron without root", "https://github.com/DominicBreuker/pspy"),
    ("GTFOBins — Unix binary privesc reference", "https://gtfobins.github.io/"),
  ],
  "Active recon & tracking": [
    ("Canarytokens — planted tokens that alert (with IP) on access", "https://canarytokens.org/"),
    ("Grabify — IP logger via disguised link", "https://grabify.org/"),
    ("Webhook.site — capture click/request metadata", "https://webhook.site/"),
  ],
  "Mobile / Android": [
    ("MobSF — mobile app security framework (static+dynamic)", "https://github.com/MobSF/Mobile-Security-Framework-MobSF"),
    ("jadx — Android DEX → Java decompiler", "https://github.com/skylot/jadx"),
    ("apktool — decompile & rebuild APKs", "https://github.com/iBotPeaches/Apktool"),
    ("APKPure — download APK files", "https://apkpure.com/"),
    ("ManifestEditor — edit APK AndroidManifest", "https://github.com/WindySha/ManifestEditor"),
  ],
  "CTF toolkit": [
    ("CyberChef — the cyber swiss-army knife (encode/decode/crypto)", "https://gchq.github.io/CyberChef/"),
    ("dcode.fr — cipher & encoding solver", "https://www.dcode.fr/en"),
    ("Aperi'Solve — layered steganography analysis", "https://www.aperisolve.com/"),
    ("StegOnline — image steganography toolkit", "https://georgeom.net/StegOnline/upload"),
    ("hexed.it — online hex editor", "https://hexed.it/"),
    ("Boxentriq — code-breaking & cipher identifier", "https://www.boxentriq.com/code-breaking"),
    ("IEEE-754 Float Converter", "https://www.h-schmidt.net/FloatConverter/IEEE754.html"),
  ],
},
"\U0001F6E1️ Blue Team": {
  "⭐ Start Here (hubs)": [
    ("Awesome Cybersecurity Blue Team — the master defender list", "https://github.com/fabacab/awesome-cybersecurity-blueteam"),
    ("Awesome Threat Detection & Hunting — curated detection resources", "https://github.com/0x4d31/awesome-threat-detection"),
    ("MITRE ATT&CK — adversary TTP reference", "https://attack.mitre.org/"),
    ("MITRE D3FEND — defensive countermeasures matrix", "https://d3fend.mitre.org/"),
  ],
  "Malware analysis & sandboxes": [
    ("VirusTotal — multi-engine file/URL/hash analysis", "https://www.virustotal.com/gui/home/upload"),
    ("ANY.RUN — interactive online malware sandbox", "https://any.run/"),
    ("Hybrid Analysis — free automated malware sandbox", "https://www.hybrid-analysis.com/"),
    ("Triage (tria.ge) — fast malware sandbox", "https://tria.ge/"),
    ("Joe Sandbox — deep malware sandbox", "https://www.joesandbox.com/"),
    ("Process Monitor — live process/file/registry activity (Sysinternals)", "https://learn.microsoft.com/en-us/sysinternals/downloads/procmon"),
  ],
  "Threat intel & IOC lookup": [
    ("MISP — threat-intelligence sharing platform", "https://github.com/MISP/MISP"),
    ("OpenCTI — structured threat-intel knowledge base", "https://github.com/OpenCTI-Platform/opencti"),
    ("Pulsedive — free IOC enrichment + risk score", "https://pulsedive.com/"),
    ("AlienVault OTX — community IOC exchange", "https://otx.alienvault.com/"),
    ("abuse.ch (ThreatFox/URLhaus/MalwareBazaar) — free feeds & samples", "https://abuse.ch/"),
    ("GreyNoise — internet scan-noise context", "https://viz.greynoise.io/"),
  ],
  "SIEM, detection & logs": [
    ("Wazuh — open-source SIEM / XDR (OSSEC successor)", "https://github.com/wazuh/wazuh"),
    ("Security Onion — network & log monitoring distro", "https://github.com/Security-Onion-Solutions/securityonion"),
    ("Sigma — vendor-agnostic detection rules", "https://github.com/SigmaHQ/sigma"),
    ("Hayabusa — fast Windows event-log threat hunting", "https://github.com/Yamato-Security/hayabusa"),
    ("Chainsaw — hunt through Windows event logs", "https://github.com/WithSecureLabs/chainsaw"),
  ],
  "DFIR (forensics & IR)": [
    ("Velociraptor — endpoint DFIR & hunting at scale", "https://github.com/Velocidex/velociraptor"),
    ("TheHive — incident-response case management", "https://github.com/TheHive-Project/TheHive"),
    ("Volatility 3 — memory forensics framework", "https://github.com/volatilityfoundation/volatility3"),
    ("Autopsy — disk forensics GUI (Sleuth Kit)", "https://www.autopsy.com/"),
    ("Eric Zimmerman Tools — Windows forensic suite", "https://ericzimmerman.github.io/"),
    ("CyberChef — decode/analyze data for analysts", "https://gchq.github.io/CyberChef/"),
    ("Email header analyzer — phishing triage", "https://mha.azurewebsites.net/"),
    ("Image metadata / forensics (29a.ch) — detect manipulated images", "https://29a.ch/photo-forensics/#forensic-magnifier"),
  ],
  "Network defense": [
    ("Wireshark — packet capture & analysis (the standard)", "https://www.wireshark.org/"),
    ("Zeek — network security monitor", "https://zeek.org/"),
    ("Suricata — IDS/IPS with deep packet inspection", "https://suricata.io/"),
    ("Arkime — full-packet capture & search", "https://arkime.com/"),
  ],
  "Purple team & detection eng.": [
    ("Atomic Red Team — ATT&CK-mapped detection tests", "https://github.com/redcanaryco/atomic-red-team"),
    ("MITRE Caldera — automated adversary emulation", "https://github.com/mitre/caldera"),
    ("YARA — pattern-match malware & files", "https://github.com/VirusTotal/yara"),
    ("LOLDrivers — known vulnerable/malicious drivers", "https://www.loldrivers.io/"),
  ],
  "Hardening & vuln mgmt": [
    ("CIS Benchmarks — secure configuration baselines", "https://www.cisecurity.org/cis-benchmarks"),
    ("OpenVAS / Greenbone — open-source vulnerability scanner", "https://www.openvas.org/"),
    ("Snyk Vulnerability DB — dependency/library vulns", "https://security.snyk.io/"),
    ("tarnish — Chrome extension security analyzer", "https://thehackerblog.com/tarnish/"),
  ],
},
"\U0001F4DA Learn & Reference": {
  "Hands-on labs (offensive)": [
    ("Hack The Box — realistic pentest machines", "https://www.hackthebox.com/"),
    ("TryHackMe — beginner-friendly guided rooms", "https://tryhackme.com/"),
    ("PortSwigger Web Security Academy — free web-hacking labs", "https://portswigger.net/web-security"),
    ("PentesterLab — web & pentest exercises", "https://pentesterlab.com/"),
    ("pwn.college — binary exploitation & deep fundamentals", "https://pwn.college/"),
    ("OverTheWire — classic wargames (start with Bandit)", "https://overthewire.org/wargames/"),
    ("VulnHub — downloadable vulnerable VMs", "https://www.vulnhub.com/"),
    ("OWASP Juice Shop — deliberately vulnerable web app", "https://owasp.org/www-project-juice-shop/"),
  ],
  "Hands-on labs (defensive/DFIR)": [
    ("CyberDefenders — blue-team & DFIR challenges", "https://cyberdefenders.org/"),
    ("BlueTeamLabs Online — SIEM/hunt/malware labs", "https://blueteamlabs.online/"),
    ("LetsDefend — SOC analyst simulation", "https://letsdefend.io/"),
  ],
  "CTF platforms & tracking": [
    ("CTFtime — track every CTF event & team ranking", "https://ctftime.org/"),
    ("picoCTF — beginner-friendly CTF (Carnegie Mellon)", "https://picoctf.org/"),
    ("Root-Me — 500+ hacking challenges", "https://www.root-me.org/"),
    ("CTFlearn — practice CTF challenges", "https://ctflearn.com/"),
  ],
  "Reference & cheat sheets": [
    ("HackTricks — pentest methodology bible", "https://book.hacktricks.xyz/"),
    ("PayloadsAllTheThings — payload reference", "https://github.com/swisskyrepo/PayloadsAllTheThings"),
    ("GTFOBins — Unix binary abuse", "https://gtfobins.github.io/"),
    ("LOLBAS — Windows binary abuse", "https://lolbas-project.github.io/"),
    ("MITRE ATT&CK — TTP matrix", "https://attack.mitre.org/"),
    ("OWASP Top 10 — web risk reference", "https://owasp.org/www-project-top-ten/"),
    ("Exploit-DB — public exploit archive", "https://www.exploit-db.com/"),
  ],
  "Blogs & news": [
    ("The Hacker News — daily security news", "https://thehackernews.com/"),
    ("BleepingComputer — breaches & malware news", "https://www.bleepingcomputer.com/"),
    ("Krebs on Security — investigative security journalism", "https://krebsonsecurity.com/"),
    ("Bellingcat — open-source investigations", "https://www.bellingcat.com/"),
    ("tl;dr sec — weekly appsec newsletter", "https://tldrsec.com/"),
    ("Darknet Diaries — security stories podcast", "https://darknetdiaries.com/"),
    ("Hackers-Arise — offensive-security tutorials", "https://www.hackers-arise.com/"),
    ("MalwareTech — malware analysis blog", "https://www.malwaretech.com/"),
    ("OSINTCurio.us — OSINT tips & techniques", "https://osintcurio.us/"),
  ],
  "My accounts & notes": [
    ("HackerOne — bug bounty programs", "https://hackerone.com/opportunities/all"),
    ("TCM Security Academy", "https://academy.tcm-sec.com/"),
    ("Antisyphon Training", "https://www.antisyphontraining.com/pay-what-you-can/"),
    ("Udemy — my courses", "https://www.udemy.com/"),
    ("David Bombal — courses", "https://courses.davidbombal.com/"),
    ("Notion — my notes", "https://www.notion.so/"),
  ],
},
}

def esc(s): return html.escape(s or "", quote=True)

def emit(d, out, indent):
    pad = "    " * indent
    for name, val in d.items():
        out.write(f'{pad}<DT><H3>{esc(clean(name))}</H3>\n{pad}<DL><p>\n')
        if isinstance(val, dict):
            emit(val, out, indent + 1)
        else:
            ip = "    " * (indent + 1)
            for title, url in val:
                out.write(f'{ip}<DT><A HREF="{esc(url)}">{esc(title)}</A>\n')
        out.write(f'{pad}</DL><p>\n')

out = io.StringIO()
out.write('<!DOCTYPE NETSCAPE-Bookmark-file-1>\n')
out.write('<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">\n')
out.write('<TITLE>Bookmarks</TITLE>\n<H1>Bookmarks</H1>\n<DL><p>\n')
emit(TREE, out, 1)
out.write('</DL><p>\n')
text = out.getvalue()

SCR = "./out"
open(f"{SCR}/cybersec-master-bookmarks.html", "w", encoding="utf-8").write(text)
# flat url list for liveness check
urls = [u for top in TREE.values() for sub in top.values() for _, u in sub]
open(f"{SCR}/urls.txt", "w").write("\n".join(urls))

total = len(urls)
print("top folders:", len(TREE))
for top, subs in TREE.items():
    n = sum(len(v) for v in subs.values())
    print(f"  {top}: {n} tools, {len(subs)} subfolders")
print("TOTAL tools:", total, "| unique:", len(set(urls)))
