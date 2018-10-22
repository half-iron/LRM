#Schritte um das bertiebssystem auf BBG zu kopieren

#stand 24.9.2018:
BBG it mit der image bone-debian-9.5-iot-armhf-2018-08-30-4gb.img aufgerüstet.


1.Download BBG image falls eine neuere version nötig ist. https://beagleboard.org/latest-images.
ich wervende meistens iot image. 
Teste sha256 checksum: 
'sha256sum bone-debian-9.5-iot-armhf-2018-08-30-4gb.img.xz'

2.Entpacke image:
'xz -d bone-debian-9.5-iot-armhf-2018-08-30-4gb.img.xz>bone-debian-9.5-iot-armhf-2018-08-30-4gb.img'

3.Brenne image auf sd-karte:
finde sd karte: 
sudo dd bs=4M if=bone-debian-9.5-iot-armhf-2018-08-30-4gb.img of=karte_name status=progress conv=fsync


4. brenne image  auf eMMC (speicher) on BBG, dann lauft das BBG ohne sd-Karte:
https://elinux.org/Beagleboard:BeagleBoneBlack_Debian#Flashing_eMMC
To turn these images into eMMC flasher images, edit the /boot/uEnv.txt file on the Linux partition on the microSD card and remove the '#' on the line with 'cmdline=init=/opt/scripts/tools/eMMC/init-eMMC-flasher-v3.sh'. Enabling this will cause booting the microSD card to flash the eMMC. 
Es braucht gut 5 minuten. Blaue LED beim USB leuchten hin und her. Wenn sie aufhéren zum leuchten ist den BBG bereit zum einschelten.

