
Remote Zugriff auf LRM
=============================
22.10.2018
---------

Den BBG stellt ein ssh tunnl zu einen server (benannt: remote server) mit öffentliches ip her und leitet dort seine eigen ssh port (22) auf einer zu definierende port (zb: 2210) weiter. 

Dann kann man vom remote server auf den BBG via ssh zugegriffen werden mit:

```bash
ssh debian@localhost -p 2211
```

# SSH tunnel einrichten

Folgende Schritte werden auf den BBG durchgeführt um den   Tunnel herzustellen.

## ssh tunnel von BBG zu remotes server testen



**Parameter:** **ip**, **user** and **pw**  der remote server sind Geheim und deswegen zu ändern.

```bash
ssh user@ip # ip, user zu ändern
```

## ssh-key generieren
```bash
ssh-keygen -f ~/.ssh/LRM_BBG -t rsa
```

## ssh-key copieren
```bash
ssh-copy-id -i .ssh/LRM_BBG.pub user@ip
```

## ssh Profil für remote server (remoteSBB) erstellen

Folgende Zeilen zur File `~.ssh/config` hinzufügen.
```bash
Host remoteSBB
	HostName ip # ip zu ändern
	User user  
	Port 22
	PubkeyAuthentication Yes
	IdentityFile ~/.ssh/LRM_BBG
	ServerAliveInterval 10
	
```
Weitere ports können, falls nötig, auf remoteSBB weiterleitet werden mit Hinzufügen von: 
```
Host remoteSBB
        ...
	RemoteForward remotePort localhost:localPort
```

Profil testen mit:
```bash
ssh remoteSBB
```

## Automatiesiert tunnel herstellen

Installiere autossh. `sudo apt install autossh`

File *ssh-tunnel.service* file in  `/etc/systemd/system/ssh-tunnel.service` kopieren und dann Service starten mit:

```bash
sudo systemctl enable ssh-tunnel.service
sudo systemctl restart ssh-tunnel.service
```

Kontrollieren fals service  korrekt gestartet
```bash
sudo systemctl status -l ssh-tunnel.service
```

falls alles in ordnung ist den tunnel hergestellt.

## Create a SOCKS proxy with SSH

Den gesamte browsing über LRM umzuleiten. Z.B um Router zu konfigurieren.

Die client ssh Verbindung  an LRM mit option `-D` durchführen:

```bash

ssh -D 1080 LRM
```

Oder im `.ssh/config` file option:
```
	DynamicForward 1080
```
Web browser muss  auf SOCK proxy mit port 1080 konfiguriert werden.

Mehreer details auf diesem [Link](https://ma.ttias.be/socks-proxy-linux-ssh-bypass-content-filters/).



