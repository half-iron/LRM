/* --COPYRIGHT--,BSD
 * Copyright (c) 2017, Texas Instruments Incorporated
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * *  Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 * *  Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * *  Neither the name of Texas Instruments Incorporated nor the names of
 *    its contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
 * THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 * PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
 * CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 * EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
 * PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
 * OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
 * OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
 * EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 * --/COPYRIGHT--*/
/*******************************************************************************
 * MSP432 GPIO - Input Interrupt
 *
 * Description: This example demonstrates a very simple use case of the
 * DriverLib GPIO APIs. P1.1 (which has a switch connected to it) is configured
 * as an input with interrupts enabled and P1.0 (which has an LED connected)
 * is configured as an output. When the switch is pressed, the LED output
 * is toggled.
 *
 *                MSP432P401
 *             ------------------
 *         /|\|                  |
 *          | |                  |
 *          --|RST         P1.0  |---> P1.0 LED
 *            |                  |
 *            |            P1.1  |<--Toggle Switch
 *            |                  |
 *            |                  |
 *
 ******************************************************************************/
/* DriverLib Includes */
#include <ti/devices/msp432p4xx/driverlib/driverlib.h>

/* Standard Includes */
#include <stdint.h>
#include <stdbool.h>
#define LED_RED GPIO_PIN0 //PORT2
#define LED_GREEN GPIO_PIN1//PORT2
#define LED_BLUE GPIO_PIN2//PORT2
#define LED_RED1 GPIO_PIN0//PORT1(1.0)
#define ERROR_LED LED_RED
#define AXLE_LED  LED_RED1


//ZEITEN einstellungen
#define T_MIN_LOW 0.1 //minimum Zeit damit PASSBY_LOW transition
#define T_MIN_HIGH 0.1 //minimum Zeit damit PASSBY_HIGH transition

#define T_MAX_LOW 5
#define T_STOP 5

#define TICK_PER_mSECONDS 750 // at 12MHZ MSCLK and TIMER 16 prescaler
#define TICK_MIN_LOW (T_MIN_LOW*1000*TICK_PER_mSECONDS)
#define TICK_MIN_HIGH (T_MIN_HIGH*1000*TICK_PER_mSECONDS)

#define TICK_MAX_LOW (T_MAX_LOW*1000*TICK_PER_mSECONDS)
#define TICK_STOP (T_STOP*1000*TICK_PER_mSECONDS)

#define MSG_HEADER_NBYTE_MASK 0x0F
#define MSG_HEADER_START (1<<4)
#define MSG_HEADER_STOP (2<<4)
#define MSG_HEADER_AXLE (3<<4)
#define MSG_HEADER_ERROR (4<<4)
#define MSG_HEADER_SETUP (5<<4)
#define MSG_HEADER_STATE (6<<4)

#define FRAME_STOP 0xFE

/*
 * Messages out:
 * Start event: passbyNumber, currentTime 4 byte
 * axle_event: Axle Number, passbyNumber, axleTime: 6byte
 * Stop event: axleNumber, passbyNumber,StopTime :6 byzte
 * error: ERRnumber
 * setup info:
 * state:state
 *
 * Messages in:
 * set STOP duration
 * set MIN_LOW_DURATION
 * set MAX LOW DURATION*/

//TODO: incomingMSG
//TODO: SLEEP_MODE
//TODO: setup param
const eUSCI_UART_Config uartConfig_A2 =//9600Baud 12MHZ clk http://software-dl.ti.com/msp430/msp430_public_sw/mcu/msp430/MSP430BaudRateConverter/index.html
{
        EUSCI_A_UART_CLOCKSOURCE_SMCLK,          // SMCLK Clock Source
        78,                                      // BRDIV = 78
        2,                                       // UCxBRF = 2
        0,                                      // UCxBRS = 0
        EUSCI_A_UART_NO_PARITY,                  // No Parity
        EUSCI_A_UART_LSB_FIRST,                  // MSB First
        EUSCI_A_UART_ONE_STOP_BIT,               // One stop bit
        EUSCI_A_UART_MODE,                       // UART mode
        EUSCI_A_UART_OVERSAMPLING_BAUDRATE_GENERATION  // Oversampling
};

//transmit nCHAR bytes starting at dataPointer. LSB first
void UART_trasmitMemory(uint8_t *dataPointer, uint8_t nChar){
    uint8_t *addr;
    addr=dataPointer;
    while(nChar>0){
        MAP_UART_transmitData(EUSCI_A2_BASE, *addr);
        while (!MAP_UART_getInterruptStatus(EUSCI_A0_BASE, EUSCI_A_UART_TRANSMIT_INTERRUPT_FLAG));
        addr++;
        nChar--;
    }
}

typedef enum _state_e {STATE_IDLE_e=0,STATE_PASSBY_WHEEL_ON_e, STATE_PASSBY_WHEEL_OFF_e,STATE_ERROR_e} state_e;
volatile state_e state;

typedef enum _cell_state_e {HIGH_e,LOW_e} cell_state_e;
volatile cell_state_e cellState;

typedef enum _transition_e {NONE_e,HIGHtoLOW_e,LOWtoHIGH_e} transition_e;
volatile transition_e lastCellTransition;


volatile uint8_t HIGHtoLOW_transitionFlag,LOWtoHIGH_transitionFlag,newAxle_Flag;
volatile uint32_t lastHIGHtoLOW_time, lastLOWtoHIGH_time,HIGHtoLOW_time, LOWtoHIGH_time ;
volatile uint32_t LOW_duration, HIGH_duration;

uint32_t  currentTime, axleTime, timeOffset;
float currentTime_f;
const float timeScaling = (1.0/(1000*TICK_PER_mSECONDS));

uint16_t axleCounter,passbyCounter;
uint8_t msg_out[20];
uint8_t transmitNBytes;


int main(void)
             {
    /* Halting the Watchdog */
    SystemInit();
    SystemCoreClockUpdate();

    MAP_WDT_A_holdTimer();

    /* Configuring LED as output*/
    MAP_GPIO_setAsOutputPin(GPIO_PORT_P1, LED_RED1);
    MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P1, LED_RED1);
    MAP_GPIO_setAsOutputPin(GPIO_PORT_P2, LED_RED);
    MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P2,LED_RED);
    MAP_GPIO_setAsOutputPin(GPIO_PORT_P2, LED_GREEN);
    MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P2,LED_GREEN);
    MAP_GPIO_setAsOutputPin(GPIO_PORT_P2, LED_BLUE);
    MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P2, LED_BLUE);


    /* Configuring P2.5 as an input and enab delta_LOWling interrupts */
    MAP_GPIO_setAsInputPinWithPullUpResistor(GPIO_PORT_P2, GPIO_PIN5);
    MAP_GPIO_clearInterruptFlag(GPIO_PORT_P2, GPIO_PIN5);
    MAP_GPIO_enableInterrupt(GPIO_PORT_P2, GPIO_PIN5);
    MAP_GPIO_interruptEdgeSelect(GPIO_PORT_P2, GPIO_PIN5, GPIO_LOW_TO_HIGH_TRANSITION);
    MAP_Interrupt_enableInterrupt(INT_PORT2);

    /* Configuring P2.7 as an input and enabling interrupts */
    MAP_GPIO_setAsInputPinWithPullUpResistor(GPIO_PORT_P2, GPIO_PIN7);
    MAP_GPIO_clearInterruptFlag(GPIO_PORT_P2, GPIO_PIN7);
    MAP_GPIO_enableInterrupt(GPIO_PORT_P2, GPIO_PIN7);
    MAP_GPIO_interruptEdgeSelect(GPIO_PORT_P2, GPIO_PIN7, GPIO_HIGH_TO_LOW_TRANSITION);
    MAP_Interrupt_enableInterrupt(INT_PORT2);

    /* Configuring Timer32 to 128000 (1s) of MCLK in periodic mode */
    MAP_Timer32_initModule(TIMER32_0_BASE, TIMER32_PRESCALER_16, TIMER32_32BIT, TIMER32_FREE_RUN_MODE);
    MAP_Timer32_startTimer(TIMER32_0_BASE,0);

    /* UART  P3.2 and P3.3 in UART A2*/
    MAP_GPIO_setAsPeripheralModuleFunctionInputPin(GPIO_PORT_P3,GPIO_PIN2 | GPIO_PIN3, GPIO_PRIMARY_MODULE_FUNCTION);
    CS_setDCOCenteredFrequency(CS_DCO_FREQUENCY_12);
    MAP_UART_initModule(EUSCI_A2_BASE, &uartConfig_A2);
    MAP_UART_enableModule(EUSCI_A2_BASE);

    /* Enabling SRAM Bank Retention */
    MAP_SysCtl_enableSRAMBankRetention(SYSCTL_SRAM_BANK1);
    
    /* Enabling MASTER interrupts */
    MAP_Interrupt_enableMaster();

    state=STATE_IDLE_e;
    cellState=HIGH_e;
    lastCellTransition=NONE_e;

    lastHIGHtoLOW_time=0;
    lastLOWtoHIGH_time=0;
    HIGHtoLOW_transitionFlag=0;
    LOWtoHIGH_transitionFlag=0;
    newAxle_Flag=0;
    LOW_duration=0;
    HIGH_duration=0;
    axleCounter=0;
    passbyCounter=0;
    transmitNBytes=0;


    while (1)
    {
        MAP_Interrupt_disableMaster();
        currentTime = MAP_Timer32_getValue(TIMER32_0_BASE);
        if((cellState==LOW_e)){
            if((lastHIGHtoLOW_time-currentTime) > TICK_MIN_LOW ){
                HIGHtoLOW_time=lastHIGHtoLOW_time;
                state=STATE_PASSBY_WHEEL_ON_e;
            }
        }else{//cell == HIGH
            if((lastLOWtoHIGH_time-currentTime) > TICK_MIN_HIGH){
                LOWtoHIGH_time=lastHIGHtoLOW_time;
                state=STATE_PASSBY_WHEEL_OFF_e;
                newAxle_Flag=1;
            }
        }
        MAP_Interrupt_enableMaster();

        //
        if (state == STATE_PASSBY_WHEEL_ON_e){
            //get current Time
            currentTime = MAP_Timer32_getValue(TIMER32_0_BASE);
            // check errors or end condition
            if((lastHIGHtoLOW_time-currentTime)> TICK_MAX_LOW){//
                //timeout ERROR
                state=STATE_ERROR_e;
                //send error event type 1
                msg_out[0]=MSG_HEADER_ERROR;
                msg_out[1]=0;
                msg_out[2]=FRAME_STOP;
                transmitNBytes=3;
            }
        }else if(state==STATE_PASSBY_WHEEL_OFF_e){
            //get current Time
            currentTime = MAP_Timer32_getValue(TIMER32_0_BASE);
            //handle interrupt flags
            if(newAxle_Flag){
                newAxle_Flag=0;
                axleCounter+=1;
                if(axleCounter==1){
                    //start passby
                    axleTime=0;
                    timeOffset = lastHIGHtoLOW_time + LOW_duration/2;
                    passbyCounter+=1;
                    //send startEvent
                    msg_out[0]=MSG_HEADER_START;
                    memcpy(&(msg_out[1]),&passbyCounter,2);
                    memcpy(&(msg_out[3]),&currentTime,4);
                    msg_out[7]=FRAME_STOP;
                    transmitNBytes=8;
                }else{
                    axleTime = lastHIGHtoLOW_time + LOW_duration/2 - timeOffset;
                }

                //send axle event
                msg_out[0]=MSG_HEADER_AXLE;
                memcpy(&(msg_out[1]),&passbyCounter,2);
                memcpy(&(msg_out[3]),&axleCounter,2);
                memcpy(&(msg_out[5]),&axleTime,4);
                msg_out[9]=FRAME_STOP;
                transmitNBytes=10;
            }
            //check STOP condition
            if((lastLOWtoHIGH_time-currentTime)> TICK_STOP_DURATION){
                //stop measurement
                state = STATE_IDLE_e;
                //send stop event
                msg_out[0]=MSG_HEADER_STOP;
                memcpy(&(msg_out[1]),&passbyCounter,2);
                memcpy(&(msg_out[3]),&axleCounter,2);
                memcpy(&(msg_out[5]),&currentTime,4);
                msg_out[9]=FRAME_STOP;
                transmitNBytes=10;
                //
                axleCounter=0;
            }
        }else if (state==STATE_ERROR_e){

            //get current Time
            currentTime = MAP_Timer32_getValue(TIMER32_0_BASE);
            if(LOWtoHIGH_transitionFlag){
                LOWtoHIGH_transitionFlag=0;
                axleCounter+=1;
            }
        }else if (state==STATE_IDLE_e){
            //MAP_Timer32_haltTimer(TIMER32_0_BASE);
            currentTime = MAP_Timer32_getValue(TIMER32_0_BASE);

        }
        currentTime_f= timeScaling*currentTime;
        //transmit message if necessary
        if (transmitNBytes>0) {
            UART_trasmitMemory((uint8_t *)(msg_out), transmitNBytes);
            transmitNBytes=0;
        }

    }
}


/* GPIO ISR */
void PORT2_IRQHandler(void)
{
    uint32_t IntState;
    uint32_t timerCounter;

    if(state == STATE_IDLE_e){
        MAP_Timer32_setCount(TIMER32_0_BASE,0xFFFFFFFF);
    }

    timerCounter=MAP_Timer32_getValue(TIMER32_0_BASE);
    //get Interrupt state reg
    IntState = MAP_GPIO_getEnabledInterruptStatus(GPIO_PORT_P2);

    if(IntState & GPIO_PIN7){ //HIGH to LOW
            MAP_GPIO_setOutputHighOnPin(GPIO_PORT_P1, AXLE_LED);
            cellState=LOW_e;
            lastHIGHtoLOW_time= timerCounter;
            //HIGH_duration= timerCounter-lastLOWtoHIGH_time ;
            //state=STATE_IDLE_LOW_e;
            //
            HIGHtoLOW_transitionFlag=1;
        }
    else if(IntState & GPIO_PIN5){//LOW to HIGH
            MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P1, AXLE_LED);
            cellState=HIGH_e;
            lastLOWtoHIGH_time= timerCounter;
            //LOW_duration= ( timerCounter- lastHIGHtoLOW_time );
            //if((LOW_duration > TICK_MIN_LOW_DURATION ) & (state==STATE_PASSBY_LOW_e)){
            //    newAxle_Flag=1;
            //    state=STATE_PASSBY_HIGH_e;
            //}
            //
            LOWtoHIGH_transitionFlag=1;
        }
   //clear interrupt Flag
   MAP_GPIO_clearInterruptFlag(GPIO_PORT_P2, IntState);

}


