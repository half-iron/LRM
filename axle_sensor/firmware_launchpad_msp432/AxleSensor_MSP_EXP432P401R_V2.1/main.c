/* DriverLib Includes */
#include <ti/devices/msp432p4xx/driverlib/driverlib.h>

/* Standard Includes */
#include <stdint.h>
#include <stdbool.h>

#define LED_RED GPIO_PIN0 //PORT2.0
#define LED_GREEN GPIO_PIN1//PORT2.1
#define LED_BLUE GPIO_PIN2//PORT2.2
#define LED_RED1 GPIO_PIN0//PORT1(1.0)
#define ERROR_LED LED_RED
#define AXLE_LED  LED_RED1

#define SYS_CLOCK 24000000//24MHZ
#define USER_TIMER_A_ISR_FREQ 2000 // Hz ISR TIMER_A frequency
#define TIMER_A_BASE_FREQ 32000 //Hz external oscillator(Q2)on Launchpad for ACLK 32 KHz
#define USER_TIMER_A_CCR (TIMER_A_BASE_FREQ/USER_TIMER_A_ISR_FREQ) //Hz external oscillator(Q2)on Launchpad for ACLK 32 KHz
#define WHEEL_COUNTER_SCALING 4 //wheel_off_counter and wheel_on_counter are scaled by this factor before sending

#define DEFAULT_THRESHOLD_ON 1
#define DEFAULT_SUM_LEN 4
#define DEFAULT_THRESHOLD_OFF 1
#define DEFAULT_THRESHOLD_ERR_S 2

//==========================================================================================
//MSG PROTOCOL
//============
//
//Messages longer than one byte (MSG from axle_sensor) are always
//stuffed using start ,stop and esc bytes
#define FRAME_START (0x7C)
#define FRAME_STOP (0x7D)
#define FRAME_ESC (0x7E)
//
//MSG from axle_sensor
//====================
//
//msg_out_axle:
//-------------
//send only in RDY state (green led on)
#define MSG_HEADER_AXLE (1)
#define MSG_HEADER_AXLE_ERROR (2)
//axle msg frame 6 byte length:
//MSG_HEADER_AXLE:uint_8t,      wheel_On_counter:uint_8t,  wheel_Off_counter:uint_32t
//
//axle error msg frame 4 byte length:
//MSG_HEADER_AXLE_ERROR:uint_8t,wheel_On_counter:uint_8t,   wheel_Off_counter:uint_32t
//
//msg_out_setup: setup response MSG
//---------------------------------
//send after a msg_in
//always 2 bytes long send only in IDLE state (green_led blinking)
//
//                                first byte                          second byte
#define MSG_HEADER_SETUP_OK (3)     // MSG_HEADER_SETUP_OK:uint_8t,     msg_in:uint_8t
#define MSG_HEADER_SETUP_ERROR (4)  // MSG_HEADER_SETUP_ERROR:uint_8t,  msg_in in:uint_8t
#define MSG_HEADER_T_ON (5)         // MSG_HEADER_T_ON:uint_8t,         threshold_ON :uint_8t
#define MSG_HEADER_T_OFF (6)        // MSG_HEADER_T_EFF:uint_8t,        threshold_OFF:uint_8t
#define MSG_HEADER_T_ERR (7)        // MSG_HEADER_T_ERR:uint_8t,        threshold_ERR:uint_8t
#define MSG_HEADER_SUM_LEN (8)      // MSG_HEADER_SUM_LEN:uint_8t,      sum_len:uint_8t
#define MSG_HEADER_ECHO (0xf1)      // MSG_HEADER_PING:uint_8t,     msg_in:uint_8t
//
//MSG to axle_sensor
//=================
//msg_in:
//-------
//Always only 1 byte long. Handle only in IDLE state (green_led blinking)
//

//Follow always response msg_out_setup
#define MSG_GET_SUM_LEN (1) //response MSG_HEADER_T_ON
#define MSG_GET_T_ON (2)    //response MSG_HEADER_T_ON
#define MSG_GET_T_OFF (3)   //response MSG_HEADER_T_OF
#define MSG_GET_T_ERR (4)   //response MSG_HEADER_T_ERR
//
//Follow always a response MSG_HEADER_SETUP_OK or MSG_HEADER_SETUP_ERROR
#define MSG_ECHO (0xf0)  //  >61
#define MSG_SET_SUM_LEN (10) // 11-20
#define MSG_SET_T_ON (20)   //  20-40
#define MSG_SET_T_OFF (40)  //  40-61
#define MSG_SET_T_ERR (60)  //  >61
//
//function prototypes and global  inherent MESG PROTOCOL
uint8_t MSG_axle(volatile uint8_t *msgdbuff, uint8_t wheel_on_counter,
                 uint32_t wheel_off_counter);
uint8_t MSG_axle_error(volatile uint8_t *msgdbuf, uint32_t wheel_off_counter);
void UART_trasmitFrame(volatile uint8_t *dataPointer, uint8_t nChar);
volatile uint8_t msg_out_dbuf[6];
uint8_t msg_in;
volatile uint8_t transmitNBytes;
// UART setup
const eUSCI_UART_Config uartConfig_A2 =\
//http://software-dl.ti.com/msp430/msp430_public_sw/mcu/msp430/MSP430BaudRateConverter/index.html
//http://www.samlewis.me/2015/05/using-msp432-eUSCI/
// SYSCLC   BAUD    BRDIV   UCxBRF  UCBRS
// 24       115200  13      0       37
// 24       9600    156     4       0
//  24      57600   26      0       111
        {
        EUSCI_A_UART_CLOCKSOURCE_SMCLK,          // SMCLK Clock Source
          26,          // BRDIV = 78 6
          0,          // UCxBRF = 2 8
          111,          // UCxBRS = 0 32
          EUSCI_A_UART_NO_PARITY,          // No Parity
          EUSCI_A_UART_LSB_FIRST,          // MSB First
          EUSCI_A_UART_ONE_STOP_BIT,          // One stop bit
          EUSCI_A_UART_MODE,          // UART mode
          EUSCI_A_UART_OVERSAMPLING_BAUDRATE_GENERATION         // Oversampling
        };

//end MSG PROTOCOL
//==========================================================================================

//================================================================
//STATE MASCINE
typedef enum _state_e
{
    STATE_IDLE_e = 0, STATE_RDY_e,
} state_e;

typedef enum _wheel_state_e
{
    WHEEL_OFF_e = 0, WHEEL_ON_e, WHEEL_ON_ERROR_e,
} wheel_state_e;

volatile state_e state;
volatile wheel_state_e wheelState;

volatile uint16_t threshold_ON, threshold_OFF, threshold_ERROR;
uint16_t threshold_ERROR_s, sum_len;
//end  STATE MASCHINE
//================================================================

//================================================================
// MOVING SUM
//
#define M_SUM_MAX_LEN 32       // Size of data arrays
typedef struct _MOVING_SUM_Obj_
{
    uint16_t sum_len;
    uint16_t sum;
    uint16_t index_0;       // points to field with oldest content
    volatile uint16_t *dbuffer_ptr;

} M_SUM_Obj;

void M_SUM_init(volatile M_SUM_Obj *moving_sum_obj,
                volatile uint16_t *dbuffer_ptr);
void M_SUM_setup(volatile M_SUM_Obj *moving_sum_obj, uint16_t sum_len);
void M_SUM_run(volatile M_SUM_Obj *moving_sum_obj, uint16_t x_new);
volatile M_SUM_Obj m_sum;
volatile uint16_t m_sum_dbuff[M_SUM_MAX_LEN];
//end  MOVING SUM
//================================================================
const Timer_A_UpModeConfig upModeConfig =\
 {
TIMER_A_CLOCKSOURCE_ACLK, // ACLK Clock Source
        TIMER_A_CLOCKSOURCE_DIVIDER_1, // ACLK/1 = 48MHz
        (USER_TIMER_A_CCR-1), // sR = 2048
        TIMER_A_TAIE_INTERRUPT_DISABLE, // Disable Timer ISR
        TIMER_A_CCIE_CCR0_INTERRUPT_ENABLE, // Disable CCR0
        TIMER_A_DO_CLEAR // Clear Counter
        };

uint32_t led_count, led_on_count;
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
    /* Configuring P2.7 as an input  */
    MAP_GPIO_setAsInputPinWithPullUpResistor(GPIO_PORT_P2, GPIO_PIN7);

    //idle input GPIO
    /* Configuring P4.1 as an input  */
    MAP_GPIO_setAsInputPinWithPullDownResistor(GPIO_PORT_P4, GPIO_PIN0);

    /* Starting and enabling ACLK (32kHz) */
    MAP_CS_setReferenceOscillatorFrequency(CS_REFO_128KHZ);
    MAP_CS_initClockSignal(CS_ACLK, CS_REFOCLK_SELECT, CS_CLOCK_DIVIDER_4);

    /* Configuring TA0 UpMode */
    MAP_Timer_A_configureUpMode(TIMER_A0_BASE, &upModeConfig);
    MAP_Interrupt_enableInterrupt(INT_TA0_0);

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

    //state = STATE_IDLE_e;
    wheelState = WHEEL_OFF_e;
    state = STATE_IDLE_e;
    threshold_ERROR_s = DEFAULT_THRESHOLD_ERR_S;
    threshold_ERROR = threshold_ERROR_s * USER_TIMER_A_ISR_FREQ;
    threshold_OFF = DEFAULT_THRESHOLD_OFF;
    threshold_ON = DEFAULT_THRESHOLD_ON;
    sum_len = DEFAULT_SUM_LEN;
    transmitNBytes = 0;
    led_count = 0;

    M_SUM_init(&m_sum, m_sum_dbuff);

    while (1)
    {
        //
        if (state == STATE_IDLE_e)
        {
            if (led_count > 0xA000)
            {
                led_count = 0;
                MAP_GPIO_toggleOutputOnPin(GPIO_PORT_P2, LED_GREEN);
            }
            else
            {
                led_count++;
            }
            //handle incoming frame
            if (MAP_UART_getInterruptStatus(EUSCI_A2_BASE,
            EUSCI_A_UART_RECEIVE_INTERRUPT_FLAG))
            {
                msg_in = MAP_UART_receiveData(EUSCI_A2_BASE);
                //

                if (msg_in >= MSG_ECHO)
                {
                    msg_out_dbuf[0] = MSG_HEADER_ECHO;
                    msg_out_dbuf[1] = msg_in;

                }

                else if (msg_in > MSG_SET_T_ERR)
                {
                    if ((msg_in - MSG_SET_T_ERR) < 5)
                    {
                        threshold_ERROR_s = msg_in - MSG_SET_T_ERR;
                        threshold_ERROR =
                                threshold_ERROR_s * USER_TIMER_A_ISR_FREQ;
                        msg_out_dbuf[0] = MSG_HEADER_SETUP_OK;
                        msg_out_dbuf[1] = msg_in;
                    }
                    else
                    {
                        msg_out_dbuf[0] = MSG_HEADER_SETUP_ERROR;
                        msg_out_dbuf[1] = msg_in;
                    }
                }
                else if (msg_in >= MSG_SET_T_OFF)
                {
                    if ((msg_in - MSG_SET_T_OFF) < (sum_len) / 2)
                    {
                        threshold_OFF = msg_in - MSG_SET_T_OFF;
                        msg_out_dbuf[0] = MSG_HEADER_SETUP_OK;
                        msg_out_dbuf[1] = msg_in;
                    }
                    else
                    {
                        msg_out_dbuf[0] = MSG_HEADER_SETUP_ERROR;
                        msg_out_dbuf[1] = msg_in;
                    }
                }
                else if (msg_in >= MSG_SET_T_ON)
                {
                    if ((msg_in - MSG_SET_T_ON) < (sum_len) / 2)
                    {
                        threshold_ON = msg_in - MSG_SET_T_ON;
                        msg_out_dbuf[0] = MSG_HEADER_SETUP_OK;
                        msg_out_dbuf[1] = msg_in;
                    }
                    else
                    {
                        msg_out_dbuf[0] = MSG_HEADER_SETUP_ERROR;
                        msg_out_dbuf[1] = msg_in;
                    }
                }
                else if (msg_in > MSG_SET_SUM_LEN)
                {
                    if ((msg_in - MSG_SET_SUM_LEN) <= 5)
                    {
                        sum_len = 1 << (msg_in - MSG_SET_SUM_LEN); //sum len =2**x, x in [1:5], max 32
                        msg_out_dbuf[0] = MSG_HEADER_SETUP_OK;
                        msg_out_dbuf[1] = msg_in;
                    }
                    else
                    {
                        msg_out_dbuf[0] = MSG_HEADER_SETUP_ERROR;
                        msg_out_dbuf[1] = msg_in;
                    }
                }
                else if (msg_in == MSG_GET_SUM_LEN)
                {
                    msg_out_dbuf[0] = MSG_HEADER_SUM_LEN;
                    msg_out_dbuf[1] = (uint8_t) sum_len;
                }
                else if (msg_in == MSG_GET_T_ON)
                {
                    msg_out_dbuf[0] = MSG_HEADER_T_ON;
                    msg_out_dbuf[1] = (uint8_t) threshold_ON;
                }
                else if (msg_in == MSG_GET_T_OFF)
                {
                    msg_out_dbuf[0] = MSG_HEADER_T_OFF;
                    msg_out_dbuf[1] = (uint8_t) threshold_OFF;
                }
                else if (msg_in == MSG_GET_T_ERR)
                {
                    msg_out_dbuf[0] = MSG_HEADER_T_ERR;
                    msg_out_dbuf[1] = (uint8_t) threshold_ERROR_s;
                }
                else
                {
                    msg_out_dbuf[0] = MSG_HEADER_SETUP_ERROR;
                    msg_out_dbuf[1] = msg_in;
                }
                UART_trasmitFrame((uint8_t *) (msg_out_dbuf), 2);
            }

            //transition
            if (MAP_GPIO_getInputPinValue(GPIO_PORT_P4, GPIO_PIN0))   //pin high
            {
                M_SUM_setup(&m_sum, sum_len);
                state = STATE_RDY_e;
                MAP_Timer_A_clearTimer(TIMER_A0_BASE);
                MAP_Timer_A_startCounter(TIMER_A0_BASE, TIMER_A_UP_MODE);
                MAP_GPIO_setOutputHighOnPin(GPIO_PORT_P2, LED_GREEN);
            }

        }
        else if (state == STATE_RDY_e)
        {
            //send axle data if necessary
            if (transmitNBytes > 0)
            {
                UART_trasmitFrame((uint8_t *) (msg_out_dbuf), transmitNBytes);
                transmitNBytes = 0;
            }
            //change state if sleep rdy
            if ( MAP_GPIO_getInputPinValue(GPIO_PORT_P4, GPIO_PIN0) == 0)
            {
                MAP_Timer_A_stopTimer(TIMER_A0_BASE);
                transmitNBytes = 0;
                state = STATE_IDLE_e;
            } //pin high
        }
//transmit message if necessary

    }
}

//******************************************************************************
//
//This is the TIMERA interrupt vector service routine.
//
//******************************************************************************
// messages are send at the end of wheel on or at the begininnig of wheel_err

void TA0_0_IRQHandler(void)
{
    static uint32_t wheel_on_count;
    static uint32_t wheel_off_count;
    MAP_GPIO_setOutputHighOnPin(GPIO_PORT_P2, LED_BLUE);
    MAP_Timer_A_clearCaptureCompareInterrupt(TIMER_A0_BASE,
    TIMER_A_CAPTURECOMPARE_REGISTER_0); //moving average
    M_SUM_run(&m_sum, 1 - MAP_GPIO_getInputPinValue(GPIO_PORT_P2, GPIO_PIN7));

    if (wheelState == WHEEL_OFF_e)
    {
        wheel_off_count++;
        if (m_sum.sum > (m_sum.sum_len - threshold_ON))
        {
            wheelState = WHEEL_ON_e;
            MAP_GPIO_setOutputHighOnPin(GPIO_PORT_P1, AXLE_LED);
            wheel_on_count = 0;
        }

    }
    else if (wheelState == WHEEL_ON_e)
    {
        wheel_on_count++;
        if (m_sum.sum < threshold_OFF)
        {
            wheelState = WHEEL_OFF_e;
            MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P1, AXLE_LED);
            //send message time wheel on  and time inbetween
            transmitNBytes = MSG_axle(msg_out_dbuf,
                                      (uint8_t) (wheel_on_count/WHEEL_COUNTER_SCALING),
                                      (wheel_off_count/WHEEL_COUNTER_SCALING )); //time in ms
            wheel_off_count = 0;

        }
        else if (wheel_on_count > threshold_ERROR)
        {
            wheelState = WHEEL_ON_ERROR_e;
            MAP_GPIO_setOutputHighOnPin(GPIO_PORT_P2, ERROR_LED);
            transmitNBytes = MSG_axle_error(msg_out_dbuf,
                                            (wheel_off_count / WHEEL_COUNTER_SCALING)); //time in ms
            wheel_off_count = 0;
        }

    }
    else if (wheelState == WHEEL_ON_ERROR_e)
    {   //
        wheel_on_count++;
        if (m_sum.sum == 0)
        {
            MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P1, AXLE_LED);
            MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P2, ERROR_LED);
            wheelState = WHEEL_OFF_e;

        }
    }
    MAP_GPIO_setOutputLowOnPin(GPIO_PORT_P2, LED_BLUE);

}

void M_SUM_init(volatile M_SUM_Obj *moving_sum_obj,
                volatile uint16_t *dbuffer_ptr)
{
    moving_sum_obj->dbuffer_ptr = dbuffer_ptr;
}
void M_SUM_setup(volatile M_SUM_Obj *moving_sum_obj, uint16_t sum_len)
{
    uint16_t i;
    moving_sum_obj->index_0 = 0;
    moving_sum_obj->sum_len = sum_len;
    moving_sum_obj->sum = 0;
    for (i = 0; i < M_SUM_MAX_LEN; ++i)
    {
        moving_sum_obj->dbuffer_ptr[i] = 0;
    }
}

void M_SUM_run(volatile M_SUM_Obj *moving_sum_obj, uint16_t x_new)
{
    uint16_t x_oldest;
    if ((++moving_sum_obj->index_0) == moving_sum_obj->sum_len)
    {
        moving_sum_obj->index_0 = 0;
    }
    //retrive x_old from data buffer
    x_oldest = moving_sum_obj->dbuffer_ptr[moving_sum_obj->index_0];
    //calculate the moving average of <x>=sum(x_i)/N by adding (x_old/N - x_old/N)
    moving_sum_obj->sum += x_new - x_oldest;
    moving_sum_obj->dbuffer_ptr[moving_sum_obj->index_0] = x_new;
}

uint8_t MSG_axle(volatile uint8_t *msgdbuff, uint8_t wheel_on_counter,
                 uint32_t wheel_off_counter)
{
    volatile uint8_t *p;
    p = msgdbuff;
    *(p) = MSG_HEADER_AXLE;
    *(p + 1) = wheel_on_counter;
    *(p + 2)= (uint8_t)(wheel_off_counter);
    *(p + 3)= (uint8_t)(wheel_off_counter>>8);
    *(p + 4)= (uint8_t)(wheel_off_counter>>16);
    *(p + 5)= (uint8_t)(wheel_off_counter>>24);
    return 6;
}

uint8_t MSG_axle_error(volatile uint8_t *msgdbuf, uint32_t wheel_off_counter)
{
    volatile uint8_t *p;
    p = msgdbuf;
    *(p) = MSG_HEADER_AXLE_ERROR;
    *(p + 1)= (uint8_t)(wheel_off_counter);
    *(p + 2)= (uint8_t)(wheel_off_counter>>8);
    *(p + 3)= (uint8_t)(wheel_off_counter>>16);
    *(p + 4)= (uint8_t)(wheel_off_counter>>24);
    return 5;
}

void UART_trasmitFrame(volatile uint8_t *dataPointer, uint8_t nChar)
{
    uint8_t b;
    uint8_t i;
    //Transmit START
    while (!MAP_UART_getInterruptStatus(EUSCI_A2_BASE,
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
                    EUSCI_A2_BASE,
                    EUSCI_A_UART_TRANSMIT_INTERRUPT_FLAG))
                ;
            MAP_UART_transmitData(EUSCI_A2_BASE, FRAME_ESC);
        }
        while (!MAP_UART_getInterruptStatus(
                EUSCI_A2_BASE,
                EUSCI_A_UART_TRANSMIT_INTERRUPT_FLAG))
            ;
        MAP_UART_transmitData(EUSCI_A2_BASE, b);
    }
    //Transmit STOP
    while (!MAP_UART_getInterruptStatus(EUSCI_A2_BASE,
    EUSCI_A_UART_TRANSMIT_INTERRUPT_FLAG))
        ;
    MAP_UART_transmitData(EUSCI_A2_BASE, FRAME_STOP);
}
