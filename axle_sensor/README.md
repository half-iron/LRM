
## Grundlage
Ein Achssensor besteht grundsätzlich aus 3 bestandteile:
- Lichtschranke (LS). Die LS hat einen  Analoge output:
    - 10V => logical 1, wenn abgedekt (Rad steht im Sicht)
    - 0V => logical 0, wenn frei (freie Sicht)
- Mikrocontroller msp432 (MCU)
- XEee Radio Modul (XBee)

### Software idee 
Den Achzähler ist als State Maschine modelliert. 

**Zustände:**
1. IDLE: Setup und stromsparmodus. Die Transition  zu diesem Zustand erfolgt 
anhand einen Xbee pin Status.
2. AXLE_ON
3. AXLE_OFF
4. AXLE_ERR

**Intergrund 2kHz ISR, Low pass filter**   

    Der MCU tastet den LS Output, deren Wert `x_i` entweder 0 oder 1  ist, mit 2kHz ab. 
    Aus diesen Werte wird eine Summe aus die letzten  `sum_len` gelesen Werte gebildet `sum = Summe x_i`.
    Dazu wird in jeden Zustand ein counter `cnt` incrementiert mit 2kHZ takt.
     
**Transitions und actions**
- wenn `sum>(sum_len-threshold_ON)`: AXLE_OFF->AXLE_ON. Dann set `axle_off_time=cnt` dann set `cnt=0`
- wenn `sum<threshold_OFF`: AXLE_ON->AXLE_OFF. Dann  send msg AXLE mit`axle_off_time` und `axle_on_time=cnt` dann set `cnt=0`
- wenn `cnt>threshold_ERR`: AXLE_ON->AXLE_ERR. Dann  send msg AXLE_ERR mit`axle_off_time` 
- wenn `sum<threshold_OFF`: AXLE_ERR->AXLE_OFF. Dann set  `cnt=0`


Mehr Informationen im Code

    
### Einstellungen

Die State Maschine kann mit 4 parameter beeinflusst werden: `threshold_ERR,threshold_ON,threshold_OFF,sum_len`

##PrintedCircuitBoard (PCB)
Alle pcb sowohl für den axle_sensor wie für den BBG  wurden mirt KiCad hersetllt.