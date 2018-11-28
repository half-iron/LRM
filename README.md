# LRM übersicht

### Ordner

- `axle_sensors` achsensoren info und firmware
- `NTiXL2` entält die python implementierung der serielle schnittstelle zur XL2 messgerät. Diesem Modul  
- `pyLRM` entält den python code notwendig für die scripts.

### Scripts

Die scripts dienen zur Bedienung der Messanlage. Die Scripts implementieren eine rehie von 
funktionen. Den Befehl `python3 scriptname.py -h` gibt Hinweise über die funktionalität und
 Anwendug der Scripts. 
 
Ein übersicht der implementierten funktionalitäten sind: 
- **xl2_device.py**: 
    - XL2 cycle power (strom aus und wieder ein)
    - XL2 test serial
    - XL2 mass <-> serial mode wechseln
    - XL2 mass mount und umount
    
- **messung.py** durchführt die Messung. Messdaten werden sowohl im XL2 wie im BBG generiert.

- **assign_tools.py**. Nach einer Messung müssen die XL2 und BBG Messdaten miteinander zugeordnet werden.

- **test_mail_logger.py** sendet einen testmail
    
- **test_axle_sensors.py** um axle sensor zu testen. ähnlich zur `messung.py` aber ohne XL2.



## Durchführung einer Messung
### Vorbereitungen

1. `pyLRM/config.py` file modifizieren falls nötig.

2. `pyLRM/passby.py` file modifizieren. Diesem File enthält die logik um die passby zu generieren. In zukunft diese änderung 
sollten in `pyLRM/config.py` durchgeführt werden durch subclassen von `passby.Passby` und neuschreiben der methode `run`

3. `pyLRM`, `NTiXL2`, Scripts und secret file auf BBG hochladen. 

### Messen

1. Stelle sicher dass den XL2 korrekt funktioniert und im serial modus ist. Benutze dafür 
den `xl2_device.py` script. z.B. mit:
    ```
    python3 xl2_device.py -test_serial
    ```
2. Starte die Messung mit  

    ```
       python3 messung.py TestMessung
    ```
    
    Den ordner `~\TestMessung` wird erstellt. Messdaten und logs sind dorthin gespeichert.
      
    Damit die messung auch nach den ssh logout weiterläuft muss den befehl in einen [screen](https://linuxize.com/post/how-to-use-linux-screen/) 
    Session  durchgeführt werden.
      
    ```bash
       screen
    ```
    Um den screen Session zu verlassen ctr-a d (detach).  
    Um den screen Session wieder zu öffnen `screen -r`
    Um den screen Session zu schliessen ctr-a k (kill).  
 

3. Stoppe die Messung  mit ctrl-c.
4. XL2 in mass modus bringen and mounten
    ```bash
        python3 xl2_device.py -to_mass -mount 
    ```
    
5. Daten runterladen
    - die XL2 daten befinden sich in `~\storagXL2`  
    - die messdaten (passby) befinden sich in `~\TestMessung`

6. XL2 wieder in serial modus bringen mit 
    ```bash
        python3 xl2_device.py -umount -eject
    ```

## Daten bereinigen und zuordnen

Zu diesem Zeitpunkt sind die passby daten und die XL2 daten in zwei ordner auf den PC. 

Als letzte Schritt nach einer Messung  müssen XL2 Daten und passby daten miteinander zugeordnet werden. 

Das Erfolgt nach diesem Schritten:

1. dauer von passby und XL2 aufnahmen prüfen 

2. zeit syncronisations zwischen passby und XL2 prüfen

3. XL2 aufnahmen und passby zuordnen

4. Neue ordnerstruktur herstellen 

Schritt 1 und 2 sind notwendig um Daten von oft auftretende Fehler zu Bereinigen. 
Diese Schritte werden mithilfe des `assign_tools.py` Script durchgeführt.

### Logs und passby daten analysieren 

Den notebook `visualize_axle_sensor_logs.ipynb` ist einen hilfmittel/Beispiel wie log Daten analysiert werden können.  
Den notebook `untersuche_assignement.ipynb` ist einen hilfmittel/Beispiel wie die Zuordnung untersucht werden kann.
  
## Ideen zur Verbesserungen

- Viele Probleme entstehen bei der Schnittstellen zum XL2 Gerät. Eine mögliche Verbesserung wäre
 die Messung nur einmal zu starten und entsprechend nur einmal stoppen. Damit wird nur ein XL2 filesatz generiert. Audiofiles werden aber dann gross
(XL2 gerät erstellt neue Files nach einer bestimmte grösse). Nur im postprocessing (assign) verden dann für die geloggte Vorbeifahrten (passby)  XL2 log und audiofiles ausgeschnitten.
**Wichtig**:
    - sync zeit Zwischen XL2 und passby(BBG) für jeden passby abfragen!
    - Messung trotzem jeden Tag neustarten damit log nicht zu gross werden un um fehler zu vermeiden.
    - Die Messung muss nicht den ganzen Tag laufen. In Zeiten ohne Verkehr (Nacht) sollte die Messung nicht laufen. 
        Zu dieser Zeiten XL2 ausschalten (mit relay), damit spart man Akku und den XL2 gerät wird resettet (Trägt zur stabilität der Messung zu). 
        Dazu können auch daten abgeholt werden. 
    - Aufpassen, kritische punkt im XL2 setum ist immer die Wahl des Messprofil.


- Alggemeine Programmierungs Verbesserungen:
    - NTiXL2 schnittstelle
    - passby module und passby class verbessern
    - Scripts verbessern. Vor allem das Argument parsing mit argparsing und die dazugehörige Dokumentation verbessern (wie im assign.py script)

- BBG: 
    - erstellen eines device tree overlay für den Relay.
    - Akku Spannung messen. Den PCB wäre dafür vorgesehn. Wobei dass problem ist dass den ADC nicht korrekt geschütz wurde. 
    Vielleicht eine bessere Lösung ist einen externen ADC (über I2C) zu wervenden. 
    Groove Module implementieren das schon und sind sehr einfach zu integrieren.  
    - Temperatur und feuchtigkeit messen. Wieder mit einen GrooveModul über I2C.

- Batterien für achszäler: Bohrmaschinen Batterien, eine genauere Messung des stromverbrauch ist zu machen.

- Mechanisches:
    - Dichtigkeit und betriebstemperaturen der Kisten prüfen 
    - Laser Lichtsensor alignement prüfen. Marke auf lichtsensor zeichen damit man sicher stellt dass den laser aligned ist.
    - Akkuverbindungsbox und Akkukabeln verbessern (Dichtigkehit und Srösse)
    -

