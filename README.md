

### Vorbereitungen

### Messung 

1. Stelle sicher dass den XL2 korrekt funktioniert und im serial modus ist. Benutze dafür  `xl2_device.py`
2. Starte die Messung mit  

    ```buildoutcfg
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

## Daten Bereinigen und zuordnen


1. dauer testen 

2. 

3. zuordnen

4. neue ordnerstructur


### Logs Anschauen
     
