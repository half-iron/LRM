
Remote zugriff auf Messtation
=============================
28.9.2018
---------

Den BBG stellt ein ssh tunnl zu einen server (benannt: remote server) mit öffentliches ip her und leitet dort seine eigen ssh port (22) auf einer zu definierende port (zb: 2210) weiter. 

Dann kann man vom remote server auf den BBG via ssh zugegriffen werden mit:

```
ssh debian@localhost -p 2210
```

# SSH tunnel einrichten

Folgende Schritte werden auf den BBG durchgeführt um den tünnel herzustellen.

## ssh tunnel von BBG zu remotes server testen

parameter:
ip, user and pw  der remote server sind Geheim

```
ssh user@ip
```

## ssh-key generieren
```
ssh-keygen -f ~/.ssh/BBG-messstation -t rsa
```

## ssh-key copieren
```
ssh-copy-id -i .ssh/BBG-messstation.pub user@ip
```

## ssh Profil für remote server (remoteSBB) erstellen

folgende zeilen zur file `~.ssh/config` hinzufügen

Host remoteSBB
	HostName ip # ip zu ändern
	User user  # user zu ändern
	Port 22
	PubkeyAuthentication Yes
	IdentityFile ~/.ssh/BBG-messstation
	ServerAliveInterval 10

profil testen mit:

```
ssh remoteSBB
```

## automatiesiert tunnel herstellen

file ssh-tunnel.service file in  `/etc/systemd/system/ssh-tunnel.service` copieren und dann service starten mit:

```
sudo systemctl enable ssh-tunnel.service
sudo systemctl restart ssh-tunnel.service
```
##Check to see if it started:
sudo systemctl status -l ssh-tunnel.service

falls alles in ordnung ist den tunnel hergestellt.





