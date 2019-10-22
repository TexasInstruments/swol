/*
 * Copyright (c) 2015-2017, Texas Instruments Incorporated
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
 */

/*
 *  ======== empty.c ========
 */

/* For usleep() */
#include <unistd.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>

/* TI-RTOS Logging */
#include <xdc/runtime/Log.h>
#include <xdc/runtime/Diags.h>

/* Driver Header files */
#include <ti/drivers/GPIO.h>
#include <ti/drivers/Power.h>
#include <ti/drivers/power/PowerCC26XX.h>
#include <ti/drivers/SWO.h>
#include <ti/drivers/swo/SWOCC26XX.h>
#include <ti/drivers/UART.h>

/* Board Header file */
#include "Board.h"

SWO_CREATE_EVENT(SWO_LogModule_BLEStack, EV0, "Event 0");
SWO_CREATE_EVENT(SWO_LogModule_User, EV1, "Event 1");
SWO_CREATE_EVENT(SWO_LogModule_User, EV2, "Event 2");

#define SWO_LogLevel_DISABLE_ERROR

/*
 * TODO(s):
 *
 * - Add re-entrancy / nesting tests (send from SWI's)
 * - Add in RTOS module
 * - Add in driver module
 */

/*
 *  ======== mainThread ========
 */
void *mainThread(void *arg0)
{
    SWO_Status status;
    SWO_open(0, &status);

    /******************************************************************************
     * Test RTOS log routing
     */

    /* Test Power driver logging */
    Power_setConstraint(PowerCC26XX_DISALLOW_IDLE);
    Power_setConstraint(PowerCC26XX_DISALLOW_STANDBY);
    Power_setConstraint(PowerCC26XX_DISALLOW_SHUTDOWN);
    Power_setConstraint(PowerCC26XX_NEED_FLASH_IN_IDLE);
    Power_setConstraint(PowerCC26XX_DISALLOW_IDLE);
    Power_setConstraint(PowerCC26XX_DISALLOW_STANDBY);
    Power_setConstraint(PowerCC26XX_DISALLOW_SHUTDOWN);
    Power_setConstraint(PowerCC26XX_NEED_FLASH_IN_IDLE);
    Power_setConstraint(PowerCC26XX_DISALLOW_IDLE);

    Power_releaseConstraint(PowerCC26XX_DISALLOW_IDLE);
    Power_releaseConstraint(PowerCC26XX_DISALLOW_STANDBY);
    Power_releaseConstraint(PowerCC26XX_DISALLOW_SHUTDOWN);
    Power_releaseConstraint(PowerCC26XX_NEED_FLASH_IN_IDLE);

    Power_setConstraint(PowerCC26XX_DISALLOW_STANDBY);
    Power_setConstraint(PowerCC26XX_DISALLOW_SHUTDOWN);
    Power_setConstraint(PowerCC26XX_NEED_FLASH_IN_IDLE);

    Power_releaseConstraint(PowerCC26XX_DISALLOW_IDLE);
    Power_releaseConstraint(PowerCC26XX_DISALLOW_STANDBY);
    Power_releaseConstraint(PowerCC26XX_DISALLOW_SHUTDOWN);
    Power_releaseConstraint(PowerCC26XX_NEED_FLASH_IN_IDLE);

    Power_releaseConstraint(PowerCC26XX_DISALLOW_IDLE);
    Power_releaseConstraint(PowerCC26XX_DISALLOW_STANDBY);
    Power_releaseConstraint(PowerCC26XX_DISALLOW_SHUTDOWN);
    Power_releaseConstraint(PowerCC26XX_NEED_FLASH_IN_IDLE);

    /* Try to trigger warnings in the logger */
    Power_releaseConstraint(PowerCC26XX_DISALLOW_IDLE);
    Power_releaseConstraint(PowerCC26XX_DISALLOW_STANDBY);
    Power_releaseConstraint(PowerCC26XX_DISALLOW_SHUTDOWN);
    Power_releaseConstraint(PowerCC26XX_NEED_FLASH_IN_IDLE);

    /*************************************************************************
     * Test driver module
     */

    /* And a UART write (as part of Power driver logger test) */
    char        writeDummy[] = "Cheese, ost, flöte";
    UART_Handle uart;
    UART_Params uartParams;
    // Initialize the UART driver.
    UART_init();
    // Create a UART with data processing off.
    UART_Params_init(&uartParams);
    uartParams.writeDataMode = UART_DATA_BINARY;
    uartParams.readDataMode = UART_DATA_BINARY;
    uartParams.readReturnMode = UART_RETURN_FULL;
    uartParams.readEcho = UART_ECHO_OFF;
    uartParams.baudRate = 115200;

    // Open an instance of the UART drivers
    uart = UART_open(Board_UART0, &uartParams);

    if (uart == NULL) {
        // UART_open() failed
        while (1);
    }

    UART_write(uart, writeDummy, sizeof(writeDummy));

    /* Test kernel log glue layer*/
    Log_info0("Hello world via Log_info0");
    Log_error0("Out of cheese error!");
    Log_error1("Out of cheese error! %d %x %s", 1);
    Log_info2("Cheesewiz: %d", 1, 2);
    Log_warning1("Out of cheese warning! %d", 1);
    Log_warning5("Out of cheese warning! %d", 1, 2, 3, 4, 5);
    Log_info3("Cheesewiz:", 1, 2, 3);

    /*********************************************************************
     * Exercise all SWO driver functionality
     */

    /* 1 second delay */
    uint32_t time0;
    uint32_t time1;
    uint32_t time2;
    uint32_t time3;
    uint8_t testBuf[6] = {0, 1, 2, 3, 4, 5};

    /* Do normal event work as they should? */
    SWO_event(SWO_LogModule_BLEStack, SWO_LogLevel_INFO,    EV0);
    SWO_event(SWO_LogModule_User, SWO_LogLevel_INFO,    EV1, 1);
    /* Do some sleep tests */
    sleep(1);
    SWO_event(SWO_LogModule_User, SWO_LogLevel_INFO, EV2, 1, 2);
    SWO_event(SWO_LogModule_User, SWO_LogLevel_WARNING, EV2, 1, 2, 3);
    SWO_event(SWO_LogModule_User, SWO_LogLevel_ERROR, EV2, 1, 2, 3, 4);

    /* Do printf works as expected */
    SWO_printf(SWO_LogModule_User, SWO_LogLevel_INFO, "String without arguments");
    SWO_printf(SWO_LogModule_User, SWO_LogLevel_INFO, "String with one argument %d", 1);
    sleep(1);
    SWO_printf(SWO_LogModule_User, SWO_LogLevel_INFO, "String with two argument %d %d", 1, 2);

    /* Do logBuf works? */
    SWO_logBuf(SWO_LogModule_User, SWO_LogLevel_INFO, "This is a test buffer: ", testBuf, 6);

    /* Do event set works? */
    SWO_EventSet eventSetHandle;
    SWO_EventSet_init(SWO_LogModule_User, SWO_LogLevel_INFO, &eventSetHandle, EV1);
    SWO_EventSet_printf(SWO_LogModule_User, SWO_LogLevel_INFO, eventSetHandle, "Test printf record %d %d %d", 1, 2, 3);
    SWO_EventSet_logBuf(SWO_LogModule_User, SWO_LogLevel_INFO, eventSetHandle, "Test logBuf record: ", testBuf, 6);

    /* Do deferred calls work? */
    SWO_printf_deferred(SWO_LogModule_User, SWO_LogLevel_INFO, "Deferred printf %d", 1);
    SWO_logBuf_deferred(SWO_LogModule_User, SWO_LogLevel_INFO, "Deferred test buffer ", testBuf, 6);
    SWO_EventSet_printf_deferred(SWO_LogModule_User, SWO_LogLevel_INFO, eventSetHandle, "Deferred test printf record %d %d %d", 1, 2, 3);
    SWO_EventSet_logBuf_deferred(SWO_LogModule_User, SWO_LogLevel_INFO, eventSetHandle, "Deferred test logBuf record ", testBuf, 6);

    /*
     * Flush it!
     *
     * Note!!! In a real application, this would likely be called from the idle task. The .cfg used to build the RTOS
     * would need to updated to accomplish this. See the documention in SWO.h for more information.
     */
    SWO_idleFlush();

    /* Can we close the set? */
    SWO_EventSet_close(SWO_LogModule_User, eventSetHandle);

    /* Can we enable watchpoints? */
    SWO_enableWatchpoint(SWO_LogModule_User, "Watchpoint 0 Text", SWO_Watchpoint0, SWO_SampleDataOnWrite, (uintptr_t) &time0);
    sleep(1);
    time0 = 0xAABBCCDD;
    sleep(1);

    SWO_enableWatchpoint(SWO_LogModule_User, "Watchpoint 1 Text", SWO_Watchpoint1, SWO_SampleDataOnWrite, (uintptr_t) &time1);
    sleep(1);
    time1 = 0xAABBCCDD;
    sleep(1);

    SWO_enableWatchpoint(SWO_LogModule_User, "Watchpoint 2 Text", SWO_Watchpoint2, SWO_SampleDataOnWrite, (uintptr_t) &time2);
    sleep(1);
    time2 = 0xAABBCCDD;
    sleep(1);

    SWO_enableWatchpoint(SWO_LogModule_User, "Watchpoint 3 Text", SWO_Watchpoint3, SWO_SampleDataOnWrite, (uintptr_t) &time3);
    sleep(1);
    time3 = 0xAABBCCDD;
    sleep(1);

    /* Test idle buffer overflow event */
    SWO_logBuf_deferred(SWO_LogModule_User, SWO_LogLevel_INFO, "Deferred test buffer ", testBuf, 0xFFFFFFF0);
    SWO_printf(SWO_LogModule_User, SWO_LogLevel_INFO, "There should have been a buffer overflow before this message.");

    /* Can we disable watchpoints? */
    SWO_sendWord(STIM_RESV3, 0xBBBBBB1A);
    SWO_disableWatchpoint(SWO_Watchpoint0);
    SWO_disableWatchpoint(SWO_Watchpoint1);
    SWO_disableWatchpoint(SWO_Watchpoint2);
    SWO_disableWatchpoint(SWO_Watchpoint3);

    /* Did it "work"? */
    SWO_sendWord(STIM_RESV3, 0xBBBBBB1B);
    time3++;

    /*
     * Send a raw event
     *
     * While this won't be parsed, it should at least not break the remainder of the test
     */
    SWO_sendWord(STIM_RESV3, 0xBBBBBB1C);
    SWO_printf(SWO_LogModule_User, SWO_LogLevel_USER2, "THIS SHOULD NOT BE SENT!!!!");

    // Test sync times
    uint8_t i = 0;
    for(i = 0; i < 5; i++)
    {
        sleep(1);
        SWO_event(SWO_LogModule_BLEStack, SWO_LogLevel_INFO, EV0);
    }

    // All done
    SWO_printf(SWO_LogModule_User, SWO_LogLevel_INFO, "Test complete!! Good job :)");

    return 0;
}
