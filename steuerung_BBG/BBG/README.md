#Schritte um das BBG zu einrichten  

Stand 22.10.2018  

[Allgemeine BBG info](http://wiki.seeedstudio.com/BeagleBone_Green/)



1. sd karte vorbereiten  

    - BBG ist mit der image **image_name** *bone-debian-9.5-iot-armhf-2018-10-07-4gb* aufgerüstet.  [Download BBG image](https://beagleboard.org/latest-images).  
    Ich wervende immer iot image. 
    Teste sha256 checksum mit `sha256sum image_name.img.xz`.

    - Entpacke image:
    
        `xz -d image_name.img.xz > image_name.img`

    - Finde Sd-Karte name und brenne image auf Sd-Karte mit **karte_name**:
        ```bash
          sudo dd bs=4M if=image_name.img of=karte_name status=progress conv=fsync 
         ```
2. Allgemeines:  
    - Password wechseln
        ```bash
        passwd 
        ```
    - Update and upgrade
    - Grow sd card partition.  
    Die sd Karte hat nach dem brennen eine Partition grösse von ca 4GB. Um die Partition auf die 
    ganze sd-Karte grösse zu strecken diesem script durchführen.
         ```
          sudo /opt/scripts/tools/grow_partition.sh
         ```
        dann reboot. [Vertiefung](https://elinux.org/Beagleboard:Expanding_File_System_Partition_On_A_microSD)

3. Setup static ip.  
    Debian verwendet `connman`als network manager. Für weitere info sich an den manual wenden.
    Grundsätzlich funktioniert das einrichten des statische ip  wie folgt:  
    - Finde de service Name **ser_name** des ethernet network service.  
    
         ```
         sudo connmanctl services  
         
         ```  
         z.B: in meinem fall ist ser_name  **ethernet_84eb189c0c9e_cable**  
     
    - dann diesem Befehl eingeben
        ```
        connmanctl config ethernet_84eb189c0c9e_cable --ipv4 manual 192.168.5.5 255.255.255.0 192.168.5.1 --nameservers 8.8.8.8
        ```


4. ssh Tunnel einrichten. (im unterordner erklärt) 

9. Einrichten des UART für den Xbee. damit die UART Nummer 4 Schnittstelle aktiviert wird muss den korrekten device tree overlay geladen werden.  
Da erfolgt durch das modifizieren des uEnv.txt file an den Punkt `###Custom Cape`
    ```
    ###Custom Cape
    dtb_overlay=/lib/firmware/BB-UART4-00A0.dtbo
    ###
    ```
    Als Referenz benütze den abgelegte uEnv.txt File.

10. XL2 udev rules einrichten und fstab Zeile einfügen.  

    Den Abgelegte file `50-usb-XL2slm.rules` im `/etc/udev/rules.d/` copieren.
    Udev restarten mit `sudo udevadm control --reload-rules && udevadm trigger`.
      
    Zum fstab file `/etc/fstab` füge Zeile hinzu (prüfe UUID! mit `blkid`)   
    `UUID=9016-4EF8  /home/debian/storageXL2  vfat defaults,nofail,user,noauto  0  0`  
    
    Nach die udev Einstellungen sollte den XL2:  
     - wenn in serial modus, mit device name `/dev/XL2serial` erkennt werden. 
     - wenn in mass storage modus, sollte ein Disk auftauchen mit name `/dev/XL2storage` 
    
    Dank fstab das mounten sollte mit `mount storageXL2` erscheinen.   
    Umounten sollte mit `umount storageXL2` erscheinen. 
    Eject mit `eject /dev/XL2storage`
    





