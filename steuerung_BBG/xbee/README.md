# LRMessanlage Xbee

In LRMesanlage kommuniziert die *steuerungBBG* und die *axle_sensor* mithilfe von [digi Xbee radio module](https://www.digi.com/xbee). Xbee Radiomodule sind an den *steuerungBBG* und die *axle_sensor* via serielle Schnittstelle (UART) verbunden. Mithilfe einen [UAR2USB Adapter](https://www.sparkfun.com/products/11812) lassen sich auch die Xbee module an PC verbinden.

- Den Xbee der *steuerungBBG* dient als *coordinator* und arbeitet in API mode.
- Die *axle_sensor* xbee sind *router* und arbeiten im *trasparent mode*.

## Xbee configurieren und testen

Am einfachsten werden xbee mithilfe des digi configurations program [XCTU](https://www.digi.com/products/xbee-rf-solutions/xctu-software/xctu) am PC configuriert und getestet. 
Das Erfolgt grundsätzlich in drei Schritte

1. Xbee auf UAR2USB einstecken und an PC verbinden
2. XCTU und xbee modul hinzufügen/finden 
3. xbee configurieren

Die [XCTU user guide](https://www.digi.com/resources/documentation/digidocs/90001458-13/) kann dafür hilfreich sein.


**Configurationsfile** für steuerungBBG (coordinator) und  axle_sensor sind in`LRMessanlage/steuerung_BBG/xbee` bzw. `LRMessanlage/axle_sensor/xbee` zu finden.

In diesem [link](https://alselectro.wordpress.com/2017/01/23/zigbee-xbee-s2c-how-to-configure-as-coordinator-router-end-device/) wird Schritt für Schritt den coordinator configuriert.

## Serielle Schnittstelle parameter

Die Configurationsfiles configurieren die Serielle Schnittstelle mit folgende parameter:

**steuerungBBG:**  57600/8/N/1/N - API 1; MAC: 0013A200414F9054

**axle_sensor:** 57600/8/N/1/N - AT; MAC: 0013A20041863136, 0013A200414F906D

## Xbee und python3

Digi hat einen python3 modul für die communication und setuop von xbee Modulen. [Documentation](https://xbplib.readthedocs.io/en/stable/) 
 


