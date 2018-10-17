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

//transmit nCHAR bytes starting at dataPointer. LSB first

//ZEITEN einstellungen ms
#define DELAY_HIGHtoLOW 3
#define DELAY_LOWtoHIGH 3
#define DELAY_MAX_LOW 1000
#define DELAY_STOP 3000

#define SYS_CLOCK 24000000//24MHZ

#define TICK_PER_mSECONDS (SYS_CLOCK/(16*1000)) // ACLK and TIMER 4 prescaler

#define TICK_DELAY_HIGHtoLOW  ((int)TICK_PER_mSECONDS*DELAY_HIGHtoLOW)
#define TICK_DELAY_LOWtoHIGH ((int)TICK_PER_mSECONDS*DELAY_LOWtoHIGH)
#define TICK_DELAY_MAX_LOW ((int)TICK_PER_mSECONDS*DELAY_MAX_LOW)
#define TICK_DELAY_STOP ((int)TICK_PER_mSECONDS*DELAY_STOP)
//===========
//MSG PROTOCOL
//============
//ADDRESS 1st Byte
#define DEVICE_ADDRESS  1
#define MASTER_ADDRESS  0
#define MSG_ADDRESS_TO 0x0F
#define MSG_ADDRESS_FROM 0xF0

#define MSG_TO_MASTER  (((DEVICE_ADDRESS<<4)& MSG_ADDRESS_FROM) | (MASTER_ADDRESS& MSG_ADDRESS_TO))

//HEADERS 2nd Byte

//DATA HEADERS (no RESPONSE)
#define MSG_HEADER_START (1)
#define MSG_HEADER_STOP (2)
#define MSG_HEADER_AXLE (3)

//COMMAND RESPONSe HEADER
#define MSG_HEADER_COMMAND (16)
#define MSG_HEADER_RESPONSE (17)

//DEBUG HEADER
#define MSG_HEADER_WARNING (18)
#define MSG_HEADER_ERROR (18)

#define API 1
#define TRANSPARENT 2
#define MESSAGING_PROTOCOL TRANSPARENT

/***********************************************************************
 * DATA MSG
 * =======
 *
 * -START: passbyCounter:uint_16t
 * -AXLE:  passbyCounter:uint_16t,axleCounter:uint_16t,axleTime:uint_16t
 * -STOP:  passbycounter:uint_16t,axleCounter:uint_16t,stopTime:uint_16t
 *
 * -TICKFREQ: tickfrequency:uint_16t
 *
 *
 *
 * COMMAND RESPONSE MSG:
 * ====================
 *
 * -COMMAND: command:uint8_t, command_id:uint8_t, command_data: DATA_MSG
 * -RESPONSE: command:uint8_t, command_id:uint8_t, response_data: DATA_MSG
 *
 * COMMANDTYPES
 * ------------
 *
 * - RESET: NO DATARESPONSE
 * - GET_TICK_FREQ: TICKFREQ
 *
 * DEBUG MSG:
 *
 * -ERROR:errortype:uint8_t
 *
 *
 *****************************************************************************
 */

uint8_t MSG_START(uint8_t *msg, uint16_t passbyCounter)
{
    uint8_t *p;
    p = msg;
    *p = MSG_TO_MASTER;
    *(p + 1) = MSG_HEADER_START;
    memcpy((p + 2), &passbyCounter, 2);
    return 4;
}

uint8_t MSG_AXLE(uint8_t *msg, uint16_t passbyCounter, uint16_t axleCounter,
                 uint16_t axleTime)
{
    uint8_t *p;
    p = msg;
    *p = MSG_TO_MASTER;
    *(p + 1) = MSG_HEADER_AXLE;
    memcpy((p + 2), &passbyCounter, 2);
    memcpy((p + 4), &axleCounter, 2);
    memcpy((p + 6), &axleTime, 2);
    return 8;
}
uint8_t MSG_STOP(uint8_t *msg, uint16_t passbyCounter, uint16_t axleCounter,
                 uint16_t stopTime)
{
    uint8_t *p;
    p = msg;
    *p = MSG_TO_MASTER;
    *(p + 1) = MSG_HEADER_STOP;
    memcpy((p + 2), &passbyCounter, 2);
    memcpy((p + 4), &axleCounter, 2);
    memcpy((p + 6), &stopTime, 2);
    return 8;
}

uint8_t MSG_ERROR(uint8_t *msg)
{
    uint8_t *p;
    p = msg;
    *p = MSG_TO_MASTER;
    *(p + 1) = MSG_HEADER_ERROR;
    return 2;
}

//FRAME bytes
#define FRAME_START (0x7C) // char "\r\r\r\n"
#define FRAME_STOP (0x7D)
#define FRAME_ESC (0x7E)
//TODO: incomingMSG
//TODO: SLEEP_MODE
//TODO: setup param
const eUSCI_UART_Config uartConfig_A2 =
//UART clocking
//http://software-dl.ti.com/msp430/msp430_public_sw/mcu/msp430/MSP430BaudRateConverter/index.html
//http://www.samlewis.me/2015/05/using-msp432-eUSCI/
// SYSCLC   BAUD    BRDIV   UCxBRF  UCBRS
// 24       115200  13      0       37
// 24       9600    156     4       0
//  24      57600   26      0       111
// 12       9600    78      2       0
// 12       115200  6       8       32
        {
        EUSCI_A_UART_CLOCKSOURCE_SMCLK,          // SMCLK Clock Source
          26,                                      // BRDIV = 78 6
          0,                                       // UCxBRF = 2 8
          111,                                      // UCxBRS = 0 32
          EUSCI_A_UART_NO_PARITY,                  // No Parity
          EUSCI_A_UART_LSB_FIRST,                  // MSB First
          EUSCI_A_UART_ONE_STOP_BIT,               // One stop bit
          EUSCI_A_UART_MODE,                       // UART mode
          EUSCI_A_UART_OVERSAMPLING_BAUDRATE_GENERATION  // Oversampling
        };

//transmit nCHAR bytes starting at dataPointer. LSB first
#if MESSAGING_PROTOCOL == API
void UART_trasmitFrame(uint8_t *dataPointer, uint8_t nChar)
{
    uint8_t b;
    uint8_t i;
    //transmit Data
    for (i = 0; i < nChar; i++)
    {
        b = *(dataPointer + i);
        while (!MAP_UART_getInterruptStatus(
                        EUSCI_A0_BASE, EUSCI_A_UART_TRANSMIT_INTERRUPT_FLAG))
        ;
        MAP_UART_transmitData(EUSCI_A2_BASE, b);
    }

}
#else
void UART_trasmitFrame(uint8_t *dataPointer, uint8_t nChar)
{
    uint8_t b;
    uint8_t i;
    //Transmit START
    while (!MAP_UART_getInterruptStatus(EUSCI_A0_BASE,
    EUSCI_A_UART_TRANSMIT_INTERRUPT_FLAG))
        ;
    MAP_UART_transmitData(EUSCI_A2_BASE, FRAME_START);
    //transmit Data
    for (i = 0; i < nChar; i++)
    {
        b = *(dataPointer + i);
        if ((b == FRAME_ESC) | (b == FRAME_START) | (b == FRAME_STOP))
        {
            while (!MAP_UART_getInterruptStatus(
                    EUSCI_A0_BASE, EUSCI_A_UART_TRANSMIT_INTERRUPT_FLAG))
                ;
            MAP_UART_transmitData(EUSCI_A2_BASE, FRAME_ESC);
        }
        while (!MAP_UART_getInterruptStatus(
                EUSCI_A0_BASE, EUSCI_A_UART_TRANSMIT_INTERRUPT_FLAG))
            ;
        MAP_UART_transmitData(EUSCI_A2_BASE, b);
    }
    //Transmit STOP
    while (!MAP_UART_getInterruptStatus(EUSCI_A0_BASE,
    EUSCI_A_UART_TRANSMIT_INTERRUPT_FLAG))
        ;
    MAP_UART_transmitData(EUSCI_A2_BASE, FRAME_STOP);
}
#endif

typedef enum _state_e
{
    STATE_RDY_e = 0,
    STATE_PASSBY_WHEEL_OFF_e,
    STATE_PASSBY_WHEEL_ON_e,
    STATE_ERROR_e,
    STATE_IDLE_e,
    STATE_SLEEP_e,
} state_e;

typedef enum _wheel_state_e
{
    WHEEL_OFF_e = 0,
    WHEEL_PRE_OFF_e,
    WHEEL_PRE_ON_e,
    WHEEL_ON_e,
    WHEEL_ON_ERROR_e,
} wheel_state_e;

volatile state_e state;
volatile wheel_state_e wheelState;
volatile uint8_t stopFlag, errorFlag;
volatile uint32_t achsStart_ms, achsStop_ms;
volatile uint16_t axleCounter, passbyCounter, errorCounter;

uint32_t currentTime_ms, axleTime_ms;

uint8_t msg_out[16];
uint8_t msg_in[16];
uint8_t transmitNBytes;
uint32_t led_count,led_on_count;

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
    MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P2, LED_RED);
    MAP_GPIO_setAsOutputPin(GPIO_PORT_P2, LED_GREEN);
    MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P2, LED_GREEN);
    MAP_GPIO_setAsOutputPin(GPIO_PORT_P2, LED_BLUE);
    MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P2, LED_BLUE);

    //cell input GPIO
    /* Configuring P2.6 as an input and enab delta_LOWling interrupts */
    MAP_GPIO_setAsInputPinWithPullUpResistor(GPIO_PORT_P2, GPIO_PIN4);
    MAP_GPIO_enableInterrupt(GPIO_PORT_P2, GPIO_PIN4);
    MAP_GPIO_interruptEdgeSelect(GPIO_PORT_P2, GPIO_PIN4,
    GPIO_LOW_TO_HIGH_TRANSITION);
    /* Configuring P2.7 as an input and enabling interrupts */
    MAP_GPIO_setAsInputPinWithPullUpResistor(GPIO_PORT_P2, GPIO_PIN7);
    MAP_GPIO_enableInterrupt(GPIO_PORT_P2, GPIO_PIN7);
    MAP_GPIO_interruptEdgeSelect(GPIO_PORT_P2, GPIO_PIN7,
    GPIO_HIGH_TO_LOW_TRANSITION);

    //status input GPIO
    /* Configuring P4.1 as an input  */
    MAP_GPIO_setAsInputPinWithPullDownResistor(GPIO_PORT_P4, GPIO_PIN1);

    /* Configuring P4.3 as an input  */
    MAP_GPIO_setAsInputPinWithPullDownResistor(GPIO_PORT_P4, GPIO_PIN3);

    /* Configuring P6.0 as an input  */
    MAP_GPIO_setAsInputPinWithPullDownResistor(GPIO_PORT_P6, GPIO_PIN0);

    // turn cell off GPIO
    /* Configuring P3.0 as an output  */
    MAP_GPIO_setAsOutputPin(GPIO_PORT_P3, GPIO_PIN0);
    MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P3, GPIO_PIN0);

    // Configuring Timer_32_0 for delay
    MAP_Timer32_initModule(TIMER32_0_BASE, TIMER32_PRESCALER_16, TIMER32_32BIT,
    TIMER32_FREE_RUN_MODE);
    //MAP_Timer32_enableInterrupt(TIMER32_0_BASE);

    // Configuring Timer_32_0 as time
    MAP_Timer32_initModule(TIMER32_1_BASE, TIMER32_PRESCALER_16, TIMER32_32BIT,
    TIMER32_FREE_RUN_MODE);
    MAP_Timer32_startTimer(TIMER32_1_BASE, false);

    /* UART  P3.2 and P3.3 in UART A2*/
    MAP_GPIO_setAsPeripheralModuleFunctionInputPin(
            GPIO_PORT_P3, GPIO_PIN2 | GPIO_PIN3, GPIO_PRIMARY_MODULE_FUNCTION);
    CS_setDCOCenteredFrequency(CS_DCO_FREQUENCY_24);
    MAP_UART_initModule(EUSCI_A2_BASE, &uartConfig_A2);
    MAP_UART_enableModule(EUSCI_A2_BASE);

    /* Enabling SRAM Bank Retention */
    MAP_SysCtl_enableSRAMBankRetention(SYSCTL_SRAM_BANK1);

    /* Enabling MASTER interrupts */
    MAP_Interrupt_enableMaster();

    state = STATE_IDLE_e;
    wheelState = WHEEL_OFF_e;

    axleCounter = 0;
    passbyCounter = 0;
    errorCounter = 0;
    transmitNBytes = 0;
    stopFlag = 0;
    errorFlag = 0;
    led_count=0;
    led_on_count=0;


    while (1)
    {
        //get current Time
        currentTime_ms = (0xffffffff - MAP_Timer32_getValue(TIMER32_1_BASE))
                / TICK_PER_mSECONDS;
        //
        if (state == STATE_SLEEP_e)
        {
            if(led_count>0x80000){
                MAP_GPIO_setOutputHighOnPin(GPIO_PORT_P2, LED_GREEN);
                led_count=0;
                while(led_count< 0x1000){
                    led_on_count=led_count/8;
                    led_count++;
                }
                led_count=0;
                MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P2, LED_GREEN);
            }else{
                led_count++;
            }
            if (MAP_GPIO_getInputPinValue(GPIO_PORT_P4, GPIO_PIN3)| MAP_GPIO_getInputPinValue(GPIO_PORT_P6, GPIO_PIN0))//pin high
            {
                state = STATE_IDLE_e;
            }


        }
        else if (state == STATE_IDLE_e)
        {
            //LED toggle
            if(led_count>0x8000){
                led_count=0;
                MAP_GPIO_toggleOutputOnPin(GPIO_PORT_P2, LED_GREEN);
            }else{
                led_count++;
            }
            //process incoming msg
            /*
            while (MAP_UART_getInterruptStatus(EUSCI_A0_BASE,
            EUSCI_A_UART_RECEIVE_INTERRUPT_FLAG))
            {
                msg_in[0] = MAP_UART_receiveData(EUSCI_A0_BASE);
            }
            */
            //change state if sleep rdy
            if (MAP_GPIO_getInputPinValue(GPIO_PORT_P4, GPIO_PIN1)|MAP_GPIO_getInputPinValue(GPIO_PORT_P6, GPIO_PIN0))// & MAP_GPIO_getInputPinValue(GPIO_PORT_P2, GPIO_PIN7)) //pin high and cell HIGH
            {
                //go to rdy state
                state = STATE_RDY_e;
                //enable Cell
                MAP_GPIO_setOutputHighOnPin(GPIO_PORT_P3, GPIO_PIN0);
                //clear interrupts
                MAP_GPIO_clearInterruptFlag(GPIO_PORT_P2, GPIO_PIN7);
                MAP_GPIO_clearInterruptFlag(GPIO_PORT_P2, GPIO_PIN4);
                MAP_Timer32_clearInterruptFlag(TIMER32_0_BASE);
                //
                MAP_Interrupt_enableInterrupt(INT_PORT2);
                MAP_Interrupt_enableInterrupt(INT_T32_INT1); //todo:
            }
            else if ((MAP_GPIO_getInputPinValue(GPIO_PORT_P4, GPIO_PIN3) == 0)&(MAP_GPIO_getInputPinValue(GPIO_PORT_P6, GPIO_PIN0)==0))
            {
                state = STATE_SLEEP_e;
            } //pin high
              //delay

        }
        else if (state == STATE_RDY_e)
        {
            MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P2, LED_BLUE);
            MAP_GPIO_setOutputHighOnPin(GPIO_PORT_P2, LED_GREEN);
            MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P2, LED_RED);
            if (wheelState == WHEEL_ON_e)
            {
                state = STATE_PASSBY_WHEEL_ON_e;
            }
            else if (wheelState==WHEEL_PRE_ON_e)
            {
                ;;
            }
            else if ((MAP_GPIO_getInputPinValue(GPIO_PORT_P4, GPIO_PIN1) == 0)&(MAP_GPIO_getInputPinValue(GPIO_PORT_P6, GPIO_PIN0)==0)) //pin4.1 high and cell HIGH(nothing is )
            {
                MAP_Interrupt_disableInterrupt(INT_PORT2);
                MAP_Interrupt_disableInterrupt(INT_T32_INT1);
                state = STATE_IDLE_e;
                //turn cell off
                MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P3, GPIO_PIN0);
            }
        }
        else if (state == STATE_PASSBY_WHEEL_ON_e)
        {
            MAP_GPIO_setOutputHighOnPin(GPIO_PORT_P2, LED_BLUE);
            MAP_GPIO_setOutputHighOnPin(GPIO_PORT_P2, LED_GREEN);
            MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P2, LED_RED);
            // check errors or end condition
            if (wheelState == WHEEL_OFF_e)
            {
                if (axleCounter == 0)
                {
                    passbyCounter++;
                    axleCounter++;
                    //START
                    transmitNBytes = MSG_START(msg_out, passbyCounter);
                    state = STATE_PASSBY_WHEEL_OFF_e;
                }
                else
                {
                    axleCounter++;
                    axleTime_ms = (achsStart_ms + achsStop_ms) / 2;
                    //AXLE
                    transmitNBytes = MSG_AXLE(msg_out, passbyCounter,
                                              axleCounter, axleTime_ms);
                    state = STATE_PASSBY_WHEEL_OFF_e;
                }
            }
            else if (wheelState == WHEEL_ON_ERROR_e)
            {
                state = STATE_ERROR_e;
                transmitNBytes = MSG_ERROR(msg_out);
            }

        }
        else if (state == STATE_PASSBY_WHEEL_OFF_e)
        {
            MAP_GPIO_setOutputHighOnPin(GPIO_PORT_P2, LED_BLUE);
            MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P2, LED_GREEN);
            MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P2, LED_RED);
            //handle interrupt flags
            if (wheelState == WHEEL_ON_e)
            {
                state = STATE_PASSBY_WHEEL_ON_e;
            }
            else if (stopFlag)
            {
                stopFlag = 0;
                //Stop passby
                transmitNBytes = MSG_STOP(msg_out, passbyCounter, axleCounter,
                                          currentTime_ms);
                //
                state = STATE_RDY_e;
                axleCounter = 0;
            }
        }
        else if (state == STATE_ERROR_e)
        {
            MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P2, LED_BLUE);
            MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P2, LED_GREEN);
            MAP_GPIO_setOutputHighOnPin(GPIO_PORT_P2, LED_RED);
            if (wheelState == WHEEL_OFF_e)
            {
                state = STATE_RDY_e;
                axleCounter = 0;
            }
        }
        //transmit message if necessary
        if (transmitNBytes > 0)
        {
            UART_trasmitFrame((uint8_t *) (msg_out), transmitNBytes);
            transmitNBytes = 0;
        }
    }
}

/* GPIO ISR */
void PORT2_IRQHandler(void)
{
    uint32_t IntState;
    //halt timeout
    MAP_Timer32_disableInterrupt(TIMER32_0_BASE);
    MAP_Timer32_haltTimer(TIMER32_0_BASE);
    MAP_Timer32_clearInterruptFlag(TIMER32_0_BASE);
    //clear interrupt Flag
    IntState = MAP_GPIO_getEnabledInterruptStatus(GPIO_PORT_P2);
    MAP_GPIO_clearInterruptFlag(GPIO_PORT_P2, IntState);
    //get Interrupt state reg
    if (IntState & GPIO_PIN7)
    { //HIGH to LOW
        MAP_GPIO_setOutputHighOnPin(GPIO_PORT_P1, AXLE_LED);
        if (wheelState == WHEEL_OFF_e)
        {
            wheelState = WHEEL_PRE_ON_e;
            MAP_Timer32_setCount(TIMER32_0_BASE, TICK_DELAY_HIGHtoLOW);
            MAP_Timer32_enableInterrupt(TIMER32_0_BASE);
            MAP_Timer32_startTimer(TIMER32_0_BASE, true);
            if (state == STATE_RDY_e)
            {
                MAP_Timer32_setCount(TIMER32_1_BASE, 0xffffffff);
            }
            achsStart_ms = (0xffffffff - MAP_Timer32_getValue(TIMER32_1_BASE))
                    / TICK_PER_mSECONDS;

        }
        else if (wheelState == WHEEL_PRE_OFF_e)
        {
            wheelState = WHEEL_ON_e;
        }
    }
    else if (IntState & GPIO_PIN4)
    { //LOW to HIGH
      //stop Timer A
        if (wheelState == WHEEL_PRE_ON_e)
        {
            wheelState = WHEEL_OFF_e;
        }
        else if (wheelState == WHEEL_ON_e)
        {
            wheelState = WHEEL_PRE_OFF_e;
            MAP_Timer32_setCount(TIMER32_0_BASE, TICK_DELAY_LOWtoHIGH);
            MAP_Timer32_enableInterrupt(TIMER32_0_BASE);
            MAP_Timer32_startTimer(TIMER32_0_BASE, true);
            achsStop_ms = (0xffffffff - MAP_Timer32_getValue(TIMER32_1_BASE))
                    / TICK_PER_mSECONDS;
        }
        else if (wheelState == WHEEL_ON_ERROR_e)
        {
            wheelState = WHEEL_OFF_e;
        }
        MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P1, AXLE_LED);
    }

}

//handles  timeout
void T32_INT1_IRQHandler(void)
{
    //
    MAP_Timer32_haltTimer(TIMER32_0_BASE);
    MAP_Timer32_disableInterrupt(TIMER32_0_BASE);
    MAP_Timer32_clearInterruptFlag(TIMER32_BASE);

    if (wheelState == WHEEL_OFF_e)
    { //stop
        stopFlag = 1; //state = STATE_IDLE_e;
    }
    else if (wheelState == WHEEL_PRE_OFF_e)
    {   //
        wheelState = WHEEL_OFF_e;
        //state = STATE_PASSBY_WHEEL_OFF_e;
        MAP_Timer32_setCount(TIMER32_0_BASE, TICK_DELAY_STOP);
        MAP_Timer32_enableInterrupt(TIMER32_0_BASE);
        MAP_Timer32_startTimer(TIMER32_0_BASE, true);
    }
    else if (wheelState == WHEEL_ON_e)
    {
        wheelState = WHEEL_ON_ERROR_e;
        //errorFlag=1;//state = STATE_ERROR_e;
    }
    else if (wheelState == WHEEL_PRE_ON_e)
    {
        wheelState = WHEEL_ON_e;
        //state = STATE_PASSBY_WHEEL_ON_e;
        MAP_Timer32_setCount(TIMER32_0_BASE, TICK_DELAY_MAX_LOW);
        MAP_Timer32_enableInterrupt(TIMER32_0_BASE);
        MAP_Timer32_startTimer(TIMER32_0_BASE, true);
    }
}
