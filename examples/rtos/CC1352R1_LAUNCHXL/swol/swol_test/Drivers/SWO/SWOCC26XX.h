/*
 * Copyright (c) 2019, Texas Instruments Incorporated
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
/** ============================================================================
 *  @file       SWOCC26XX.h
 *
 *  @brief      SWO driver for CC26XX instrumentation
 *
 *  TODO: Expand upon below documentation
 *
 *  # Protocol #
 *  The protocol uses a 32-bit header containing the op code and optional
 *  arguments. The header is sent as a single SWIT packet on the dedicated
 *  stimulus port STIM_HEADER. The meaning of the header arguments depends
 *  on the op code used and is described as part of the op code enumerator
 *  documentation.
 *
 *  If the "eventSet" bit is set in the header, the header will
 *  be extended with a third argument if needed. Argument zero will contain
 *  information on which event set the op code belongs to while the two
 *  remaining arguments contain the original operation arguments. The third
 *  argument will be sent as a separate 16-bit SWIT packet directly following
 *  the header on the same stimulus port as the header.
 *
 *  Depending on the op code received on the STIM_HEADER stimulus, additional
 *  data can be expected on the STIM_TRACE port.
 *
 *  If data has been deferred to the idle buffer, the header will be repeated
 *  again before the buffered data is sent out. The buffered data is sent
 *  on the STIM_IDLE stimulus port.
 *
 *  When returning from device standby, or opening the driver, a timer sync
 *  will be sent out on the STIM_TIME_SYNC stimulus port. The message will
 *  contain the current radio RAT timer value as well as the current RTC value.
 *  No other packets can use the STIM_TIME_SYNC port.
 *
 *  The STIM_DRIVER port is reserved for the SWO Driver and may not be used
 *  by any other part of the application. The SWO_RESV and SWO_RAW ports can
 *  be use by the application together with the SWO_sendChar(),
 *  SWO_sendShort() and SWO_sendWord() API.
 *
*/

#ifndef ti_drivers_swocc26xx__include
#define ti_drivers_swocc26xx__include

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>
#include <ti/drivers/dpl/SemaphoreP.h>

#include <ti/drivers/PIN.h>
#include <ti/drivers/Power.h>

/*!
 * @brief Maximum numbers of sets supported.
 */
#define MAX_NUMBER_OF_SETS 32

/*!
 *  @brief      SWOCC26XX Hardware attributes
 *
 *  These fields, with the exception of idleBuffer,
 *  needs to be populated. In order to use Event Records
 *  Sets and deferred calls, an idle buffer must be provided.
 */
typedef struct SWOCC26XX_HWAttrs {
    /*! Baud rate for UART */
    unsigned int     baudRate;
    /*! Buffer used for idle processing */
    unsigned char*   idleBuffer;
    /*! Size of idle buffer */
    size_t           idleBufferSize;
    /*! SWO output PIN */
    uint8_t          swoPin;
} SWOCC26XX_HWAttrs;


/*!
 *  @brief      SWOCC26XX Object
 *
 *  The application must not access any member variables of this structure!
 */
typedef struct SWOCC26XX_Object {
    uint32_t            isOpen;                                         /*!< Number of times the driver has been opened */
    uint8_t             activeWatchpoints;                              /*!< Active watchpoints */
    uint32_t            activeSets[MAX_NUMBER_OF_SETS / 32];            /*!< Bitmask containing active Event Sets */
    uint8_t             setRecords[MAX_NUMBER_OF_SETS + 1];             /*!< Number of records in an active set */
    uint32_t            fullPacketInCycles;                             /*!< Number of CPU cycles required for a full packet of 5 bytes plus 3 byte timestamp. */

    /* Idle circular buffer state */
    struct {
        uint32_t freeSpace;
        uint32_t head;
        uint32_t tail;
    } idleBuf;

    /* PIN driver state object and handle */
    PIN_Handle          swoPinHandle;
    PIN_State           swoPinState;

    /* Power driver notification object */
    Power_NotifyObj     swoPowerObj;

} SWOCC26XX_Object, *SWOCC26XX_Handle;

/* SWOCC26XX specific Functions for direct, raw, ITM data output */
void SWO_sendWord(uint8_t stimulus, uint32_t value);
void SWO_sendShort(uint8_t stimulus, uint16_t value);
void SWO_sendChar(uint8_t stimulus, uint8_t value);

#ifdef __cplusplus
}
#endif

#endif /* ti_drivers_swocc26xx__include */
