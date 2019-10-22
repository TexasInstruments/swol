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

#include <stdint.h>
#include <stdbool.h>
#include <stdarg.h>
#include <string.h>

#if defined(__IAR_SYSTEMS_ICC__)
#include <intrinsics.h>
#define __clz __CLZ
#elif defined(__GNUC__)
#define __clz __builtin_clz
#endif

#include <ti/drivers/dpl/HwiP.h>

#include <ti/drivers/SWO.h>
#include <ti/drivers/swo/SWOCC26XX.h>
#include <ti/drivers/PIN.h>
#include <ti/drivers/pin/PINCC26XX.h>
#include <ti/drivers/Power.h>
#include <ti/drivers/power/PowerCC26XX.h>


#include <ti/devices/DeviceFamily.h>
#include DeviceFamily_constructPath(inc/hw_memmap.h)
#include DeviceFamily_constructPath(inc/hw_cpu_itm.h)
#include DeviceFamily_constructPath(inc/hw_cpu_scs.h)
#include DeviceFamily_constructPath(inc/hw_cpu_tpiu.h)
#include DeviceFamily_constructPath(inc/hw_cpu_dwt.h)
#include DeviceFamily_constructPath(driverlib/ioc.h)
#include DeviceFamily_constructPath(driverlib/gpio.h)
#include DeviceFamily_constructPath(driverlib/aon_rtc.h)

/* Port macros */
#define ITM_Port32(n) (*((volatile unsigned int *)  (0xE0000000+4*n)))
#define ITM_Port16(n) (*((volatile unsigned short *)(0xE0000000+4*n)))
#define ITM_Port8(n)  (*((volatile unsigned char *) (0xE0000000+4*n)))

/* Static globals */
static SWOCC26XX_Object         swoObject;
static SWOCC26XX_Object         *object = &swoObject;
static uint8_t buffer[SWO_IDLE_BUFFER_SIZE] = {0};

const SWOCC26XX_HWAttrs swoHwAttrs = {
    .baudRate = SWO_BAUD_RATE,
    .swoPin = SWO_PIN,
    .idleBuffer = buffer,
    .idleBufferSize = SWO_IDLE_BUFFER_SIZE,
};
static SWOCC26XX_HWAttrs  const *hwAttrs = &swoHwAttrs;

/*
 *  ======== SWO_sendWord ========
 */
void SWO_sendWord(uint8_t stimulus, uint32_t value)
{
    uint32_t key;
    key = HwiP_disable();

    while ((ITM_Port32(stimulus) == 0x00000000));
    ITM_Port32(stimulus) = value;

    HwiP_restore(key);
}

/*
 *  ======== SWO_sendShort ========
 */
void SWO_sendShort(uint8_t stimulus, uint16_t value)
{
    uint32_t key;
    key = HwiP_disable();

    while ((ITM_Port16(stimulus) == 0x0000));
    ITM_Port16(stimulus) = value;

    HwiP_restore(key);
}

/*
 *  ======== SWO_sendChar ========
 */
void SWO_sendChar(uint8_t stimulus, uint8_t value)
{
    uint32_t key;
    key = HwiP_disable();

    while ((ITM_Port8(stimulus) == 0x00));
    ITM_Port8(stimulus) = value;

    HwiP_restore(key);
}

/*
 *  ======== EventSet_allocateSet ========
 *  Allocate the next free set.
 */
static SWO_EventSet EventSet_allocateSet() {
    uint8_t tmp;
    uint8_t id = 0; /* No free slot */
    uint32_t key;

    key = HwiP_disable();
    /* Find first free set */
    uint8_t i;
    for (i = 0; i < 7; i++) {
        tmp = __clz(object->activeSets[i] ^ 0xFFFFFFFF);
        if (32 != tmp) {
            break;
        }
    }

    /* If there was a free set; assign and return it */
    if (32 != tmp) {
        id = (i * 32) + (31 - tmp);
        object->activeSets[i] |= (1 << (31 - tmp));
        object->setRecords[id] = 0;
    }
    HwiP_restore(key);

    return id;
}

/*
 *  ======== EventSet_freeSet ========
 *  Frees an previous allocated set.
 */
static void EventSet_freeSet(SWO_EventSet rec) {
    uint32_t offset = rec / 32;
    if (offset > 0) {
        rec -= 32 * (offset - 1);
    }
    object->activeSets[offset] &= ~(1 << rec);
}

/*
 *  ======== EventSet_isActiveSet ========
 *  Checks if a set is currently active.
 */
#if defined(SWO_trace_ENABLE_ASSERT)
static bool EventSet_isActiveSet(SWO_EventSet rec) {
    uint32_t offset = rec / 32;
    if (offset > 0) {
        rec -= 32 * (offset - 1);
    }

    return (object->activeSets[offset] & (1 << rec));
}
#endif

/*
 *  ======== idleBuf_checkFreeSpace ========
 */
static bool idleBuf_checkFreeSpace(uint32_t size) {
    return (object->idleBuf.freeSpace >= size);
}

/*
 *  ======== idleBuf_isEmpty ========
 */
static bool idleBuf_isEmpty() {
    return (object->idleBuf.freeSpace == hwAttrs->idleBufferSize);
}

/*
 *  ======== idleBuf_getCount ========
 */
static uint32_t idleBuf_getCount() {
    return (hwAttrs->idleBufferSize - object->idleBuf.freeSpace);
}

/*
 *  ======== idleBuf_putData ========
 */
static void idleBuf_putData(void *data, uint32_t size) {
    uint32_t key;

    key = HwiP_disable();

    memcpy(&(hwAttrs->idleBuffer[object->idleBuf.head]), data, size);
    object->idleBuf.freeSpace -= size;
    object->idleBuf.head = (object->idleBuf.head + size) % hwAttrs->idleBufferSize;

    HwiP_restore(key);
}

/*
 *  ======== idleBuf_getData ========
 */
static int8_t idleBuf_getData(void *data, uint32_t size) {
    uint32_t key;

    key = HwiP_disable();
    if (idleBuf_getCount() < size) {
        HwiP_restore(key);
        return -1;
    }

    memcpy(data, &(hwAttrs->idleBuffer[object->idleBuf.tail]), size);
    object->idleBuf.tail = (object->idleBuf.tail + size) % hwAttrs->idleBufferSize;
    object->idleBuf.freeSpace += size;

    HwiP_restore(key);

    return (1);
}

/*
 *  ======== idleBuf_getWord ========
 */
static uint32_t idleBuf_getWord() {
    uint32_t data;

    idleBuf_getData(&data, 4);

    return (data);
}

/*
 *  ======== idleBuf_getShort ========
 */
static uint16_t idleBuf_getShort() {
    uint16_t data;

    idleBuf_getData(&data, 2);

    return (data);
}

/*
 *  ======== idleBuf_getChar ========
 */
static uint8_t idleBuf_getChar() {
    uint8_t data;

    idleBuf_getData(&data, 1);

    return (data);
}

/*
 *  ======== SWO_syncTime ========
 */
static void SWO_syncTime() {
    uint64_t currentRTCTime = AONRTCCurrent64BitValueGet();
    /* Time sync is sent over STIM_TIME_SYNC stimulus port*/
    SWO_sendWord(STIM_TIME_SYNC, (currentRTCTime >> 32));
    SWO_sendWord(STIM_TIME_SYNC, (0xFFFFFFFF & currentRTCTime));
}

/*
 *  ======== __SWO_prepareForIdle ========
 */
void __SWO_prepareForIdle(uint32_t reason) {
    /* Only if currently used ... */
    if (object->isOpen != 0) {
#ifdef SWO_PcSampling_ENABLE
        /* Disable PCSAMPLING, otherwise the FIFO will continue to fill up. */
        HWREG(CPU_DWT_BASE + CPU_DWT_O_CTRL) &= ~((1 << 12) | (1 << 16));
#endif

        /* Wait for the FIFO to be empty */
        while ((ITM_Port32(0) == 0x00000000));

        /* Write dummy value to "flush" the FIFO */
        uint32_t dummy = 0xAAAAAA00 | reason;
        SWO_sendWord(STIM_DRIVER, dummy);


        /* Wait until the ITM events has drained */
        while (HWREG(CPU_ITM_BASE + CPU_ITM_O_TCR) & (1 << 23));

        /* The ITM line need to remain high for at least 1
         * full 32-bit packet, or a half "timestamp interval",
         * which ever is larger. This to be sure the ITM FIFO it is empty
         * and idle.
         *
         * As this function is only to be invoked just before entering
         * standby, there should be no auto generated sync packets
         * this close in time. */
        uint32_t ticksNow = HWREG(CPU_DWT_BASE + CPU_DWT_O_CYCCNT);
        int32_t numTicks = 0;
        do {
            if (GPIO_readDio(hwAttrs->swoPin)) {
                int32_t tmp = ticksNow - HWREG(CPU_DWT_BASE + CPU_DWT_O_CYCCNT);
                if (tmp < 0) {
                    tmp += 0xFFFFFF;
                }
                numTicks += tmp;
                ticksNow = HWREG(CPU_DWT_BASE + CPU_DWT_O_CYCCNT);
            }
            else {
                numTicks = 0;
            }
        } while ((numTicks < object->fullPacketInCycles));

        /* Ensure SWO IO will stay high when in idle */
        PIN_setOutputEnable(object->swoPinHandle, hwAttrs->swoPin, 1);
        PIN_setOutputValue(object->swoPinHandle, hwAttrs->swoPin, 1);
        /* Release the SWO pin from the ITM */
        PINCC26XX_setMux(object->swoPinHandle, hwAttrs->swoPin, IOC_PORT_GPIO);
        /* Disable ITM */
        HWREG(CPU_ITM_BASE + CPU_ITM_O_TCR) &= ~0x1;
    }
}

/*
 *  ======== __SWO_prepareForIdle ========
 */
void __SWO_returnFromIdle() {
    /* Only if currently used ... */
    if (object->isOpen != 0) {
        /* Enable ITM */
        HWREG(CPU_ITM_BASE + CPU_ITM_O_TCR) |= 0x1;
        /* Return SWO pin to the ITM hardware*/
        PINCC26XX_setMux(object->swoPinHandle, hwAttrs->swoPin, IOC_PORT_MCU_SWV);
        /* Send time sync */
        SWO_syncTime();
#ifdef SWO_PcSampling_ENABLE
        /* Enable PCSAMPLING */
        HWREG(CPU_DWT_BASE + CPU_DWT_O_CTRL) |= (1 << 12) | (1 << 16);
#endif
    }
}

/*
 *  ======== swoPostNotify ========
 */
static int swoPowerNotify(unsigned int eventType, uintptr_t eventArg, uintptr_t clientArg)
{
    /* Reconfigure the hardware if returning from sleep */
    if (eventType == PowerCC26XX_AWAKE_STANDBY_LATE) {
        __SWO_returnFromIdle();
    }
    else if (eventType == PowerCC26XX_ENTERING_STANDBY) {
        __SWO_prepareForIdle(PowerCC26XX_ENTERING_STANDBY);
    }
    return Power_NOTIFYDONE;
}

/*
 *  ======== __SWO_init ========
 */
void __SWO_init() {
    // Empty ...
}

/*
 *  ======== __SWO_open ========
 */
void __SWO_open(SWO_Params *params, SWO_Status *status) {
    PIN_Config               swoPinTable[2];

    if (status != NULL) {
        *status = SWO_STATUS_SUCCESS;
    }

    /* If first time, initialize the ITM module */
    if (object->isOpen == 0) {
        /* Try to allocate the swo pin */
        swoPinTable[0] = hwAttrs->swoPin | PIN_INPUT_EN | PIN_GPIO_OUTPUT_EN | PIN_GPIO_HIGH;
        swoPinTable[1] = PIN_TERMINATE;
        object->swoPinHandle = PIN_open(&object->swoPinState, swoPinTable);

        /* Are the pin already allocated */
        if ((NULL == object->swoPinHandle) && (status != NULL)) {
            *status = SWO_STATUS_PIN_UNAVAILABLE;
        }
        else {
            /* Enable ITM module */
            HWREG(CPU_SCS_BASE + CPU_SCS_O_DEMCR) |= (1 << 24);

            /* Give Access Control */
            HWREG(CPU_ITM_BASE + CPU_ITM_O_LAR) = 0xC5ACCE55;

            /* Control Register: Enable all stimulus ports */
            HWREG(CPU_ITM_BASE + CPU_ITM_O_TER) = 0xFFFFFFFF;

            /* Control register: enable ITM, differential timestamp, sync packet Tx, Trace bus Id */
            HWREG(CPU_ITM_BASE + CPU_ITM_O_TCR) |= 0x1000F;

            /* Apply Trace Bus ID */
            HWREG(CPU_ITM_BASE + CPU_ITM_O_TPR) |= 0xF;

            /* Set formatter and flush control */
            HWREG(CPU_TPIU_BASE + CPU_TPIU_O_FFCR) &= ~(1 << 1);
            HWREG(CPU_TPIU_BASE + CPU_TPIU_O_FFCR) |= (1 << 8);

            /* USE UART protocol */
            HWREG(CPU_TPIU_BASE + CPU_TPIU_O_SPPR) &= ~(0x3);
            HWREG(CPU_TPIU_BASE + CPU_TPIU_O_SPPR) |= (0x2);

            /* Set bus speed */
            HWREG(CPU_TPIU_BASE + CPU_TPIU_O_ACPR) &= ~(0x1FFF);
            HWREG(CPU_TPIU_BASE + CPU_TPIU_O_ACPR) |= ((48000000 / (hwAttrs->baudRate) - 1));

            /* Enable CYCCNT */
            HWREG(CPU_DWT_BASE + CPU_DWT_O_CTRL) |= 1;

            /* Configure pin for SWO trace */
            PINCC26XX_setMux(object->swoPinHandle, hwAttrs->swoPin, IOC_PORT_MCU_SWV);

            /* Init the circular buffer if an idle buffer is defined */
            if (NULL != hwAttrs->idleBuffer) {
                object->idleBuf.head = 0;
                object->idleBuf.tail = 0;
                object->idleBuf.freeSpace = hwAttrs->idleBufferSize;
            }
            else {
                object->idleBuf.freeSpace = 0;
            }

            /* Reserve record 0, used as a special value */

            object->setRecords[0] = 1;

            /* Calculate number of cycles needed for sending out 4.
             * If the number is larger then half of a full time stamp
             * interval, use that instead*/
            object->fullPacketInCycles = (32 * (48000000 / hwAttrs->baudRate));
            if (object->fullPacketInCycles > 900000) {
                object->fullPacketInCycles = 900000;
            }

            /* Register notification function */
            Power_registerNotify(&object->swoPowerObj, PowerCC26XX_AWAKE_STANDBY_LATE | PowerCC26XX_ENTERING_STANDBY, (Power_NotifyFxn)swoPowerNotify, (uint32_t)0);

            /* Send magic reset sequence */
            SWO_sendWord(STIM_DRIVER, 0xBBBBBBBB);

            /* Send RTC time sync messages */
            SWO_syncTime();

#ifdef SWO_PcSampling_ENABLE
            /* Enable PCSAMPLING every 512th cycle and interrupt event tracing*/
            HWREG(CPU_DWT_BASE + CPU_DWT_O_CTRL) |= (1 << 12) | (1 << 9) | (1 << 16);
#endif // SWO_PcSampling_ENABLE
        }
    }

    /* Increment is open counter to allow multiple open calls */
    object->isOpen++;
}

/*
 *  ======== __SWO_close ========
 */
void __SWO_close() {
    /* Decrement is open counter */
    object->isOpen--;

    /* If this is the last close call, clean up */
    if (object->isOpen == 0) {
        /* Release swo pin */
        PIN_close(object->swoPinHandle);
        object->swoPinHandle = NULL;

        /* Disable ITM */
        HWREG(CPU_SCS_BASE + CPU_SCS_O_DEMCR) &= ~(1 << 24);
        HWREG(CPU_DWT_BASE + CPU_DWT_O_CTRL) &= ~(1 << 12) | (1 << 16);

        /* Unregister power notification objects */
        Power_unregisterNotify(&object->swoPowerObj);
    }
}

/*
 *  ======== __SWO_Idleflush ========
 */
void __SWO_idleFlush() {
    uint32_t size;

    /* If there is data in the buffer */
    while (!idleBuf_isEmpty()) {
        /* Read out size */
        size = idleBuf_getWord();

        /* Send data */
        uint32_t i;
        for (i = 0; i < size; ) {
            uint32_t data = 0;
            /* Read out the data from the buffer */
            uint32_t readNBytes = (((size - i) > 3) ? 4 : (size - i));

            /* 3-4 bytes is sent as words, 2 bytes as shorts and 1 byte as char */
            if (readNBytes > 3) {
                data = idleBuf_getWord();
                SWO_sendWord(STIM_IDLE, data);
                i += 4;
            } else if (readNBytes > 1) {
                data = idleBuf_getShort();
                SWO_sendShort(STIM_IDLE, (uint16_t) data);
                i += 2;
            } else {
                data = idleBuf_getChar();
                SWO_sendChar(STIM_IDLE, (uint8_t) data);
                i += 1;
            }
        }
    }
}

/*
 *  ======== __SWO_printf ========
 */
void __SWO_printf(uint8_t isDeferred, uint8_t isEventSet, uint32_t hdr, uint32_t nArgs, SWO_EventSet eventSet, ...)
{
    va_list argptr;
    va_start(argptr, eventSet);

    /* Send header */
    SWO_sendWord(STIM_HEADER, hdr);

    /* If event set, send record data before the payload */
    if (isEventSet) {
        /* Protect record struct */
        uint32_t key = HwiP_disable();
        uint8_t tmp = object->setRecords[eventSet]++;
        HwiP_restore(key);
        SWO_sendShort(STIM_TRACE, (eventSet << 8) | (0xFF & tmp));
    }

    /* Is the data deferred or not? */
    if (isDeferred) {
            uint32_t bufferSize = ((nArgs) * 4);
        if ((bufferSize > 0) && idleBuf_checkFreeSpace(bufferSize + 8)) {
            /* Store count to idle buffer before the arguments*/
            idleBuf_putData(&bufferSize, 4);

            uint32_t i;
            for (i = 0; i < nArgs; i++) {
                uintptr_t arg = va_arg(argptr, uint32_t);
                idleBuf_putData(&arg, 4);
            }
        }
        else {
            /* Idle buffer was full, notify tracer */
            SWO_sendWord(STIM_DRIVER, 0xCCCCCCCC);
        }
    }
    else {
        uint32_t i;
        for(i = 0; i < nArgs; ++i)
        {
            uintptr_t arg = va_arg(argptr, uintptr_t);
            SWO_sendWord(STIM_TRACE, arg);
        }
    }

    va_end (argptr);
}

/*
 *  ======== __SWO_event0 ========
 */
void __SWO_event0(uint32_t hdr, uint32_t dummy)
{
    /* Send header */
    SWO_sendWord(STIM_HEADER, hdr);
}

/*
 *  ======== __SWO_event1 ========
 */
void __SWO_event1(uint32_t hdr, uint32_t dummy, uint32_t arg0)
{
    /* Send header */
    SWO_sendWord(STIM_HEADER, hdr);

    /* Send argument */
    SWO_sendWord(STIM_TRACE, arg0);
}

/*
 *  ======== __SWO_event2 ========
 */
void __SWO_event2(uint32_t hdr, uint32_t dummy, uint32_t arg0, uint32_t arg1)
{
    /* Send header */
    SWO_sendWord(STIM_HEADER, hdr);

    /* Send argument */
    SWO_sendWord(STIM_TRACE, arg0);
    SWO_sendWord(STIM_TRACE, arg1);
}

/*
 *  ======== __SWO_event3 ========
 */
void __SWO_event3(uint32_t hdr, uint32_t dummy, uint32_t arg0, uint32_t arg1, uint32_t arg2)
{
    /* Send header */
    SWO_sendWord(STIM_HEADER, hdr);

    /* Send arguments */
    SWO_sendWord(STIM_TRACE, arg0);
    SWO_sendWord(STIM_TRACE, arg1);
    SWO_sendWord(STIM_TRACE, arg2);
}

/*
 *  ======== __SWO_event4 ========
 */
void __SWO_event4(uint32_t hdr, uint32_t dummy, uint32_t arg0, uint32_t arg1, uint32_t arg2, uint32_t arg3)
{
    /* Send header */
    SWO_sendWord(STIM_HEADER, hdr);

    /* Send arguments */
    SWO_sendWord(STIM_TRACE, arg0);
    SWO_sendWord(STIM_TRACE, arg1);
    SWO_sendWord(STIM_TRACE, arg2);
    SWO_sendWord(STIM_TRACE, arg3);
}

/*
 *  ======== __SWO_EventSet_init ========
 */
SWO_EventSet __SWO_EventSet_init(uint32_t hdr, SWO_Event event) {
    /* Try to allocate a free set */
    SWO_EventSet eventSet = EventSet_allocateSet();

    /* Send header right away, marks start of set */
    if ((SWO_EventSet) 0x00 != eventSet) {
        /* Send header */
        SWO_sendWord(STIM_HEADER, hdr);
        SWO_sendChar(STIM_TRACE, eventSet);
    }
    else {
        /* If there were no sets available, send the header without setting the "eventSet" bit*/
        //TODO. I don't know how to handle this in parser. Just return error here?
        //SWO_sendWord(STIM_HEADER, SWO_HEADER(0, SWO_OPCODE_EVENT_SET_START, 0, loc));
    }

    return eventSet;
}

/*
 *  ======== __SWO_EventSet_close ========
 */
void __SWO_EventSet_close(uint32_t hdr, SWO_EventSet eventSet) {
    /* Send closing header */
    SWO_sendWord(STIM_HEADER, hdr);
    SWO_sendChar(STIM_TRACE, eventSet);
    /* Free the record */
    EventSet_freeSet(eventSet);
}

/*
 *  ======== __SWO_logBuf ========
 */
void __SWO_logBuf(uint8_t isDeferred, uint8_t isEventSet, uint32_t hdr, SWO_EventSet eventSet, uint8_t *data, size_t size) {
    /* Send header */
    SWO_sendWord(STIM_HEADER, hdr);

    /* If event set, send record data before the payload */
    if (isEventSet) {
        /* Protect record struct */
        uint32_t key = HwiP_disable();
        uint8_t tmp = object->setRecords[eventSet]++;
        HwiP_restore(key);

        SWO_sendShort(STIM_TRACE, (eventSet << 8) | (0xFF & tmp));
    }

    /* We also always send the size of the expected buffer */
    SWO_sendWord(STIM_TRACE, size);

    /* Is the data deferred or not? */
    if (isDeferred) {
       /* Is there room in the idle buffer? */
        if (idleBuf_checkFreeSpace(size + 4)) {
            /* Store size to idle buffer before the data*/
            idleBuf_putData(&size, 4);

            /* Copy into buffer */
            idleBuf_putData(data, size);
        }
        else {
            /* Idle buffer was full, notify tracer */
            SWO_sendWord(STIM_DRIVER, 0xCCCCCCCC);
        }
    }
    else {
        /* Send data from buffer*/
        uint32_t i;
        for (i = 0; i < size; ) {
            /* 3-4 bytes is sent as words, 2 bytes as shorts and 1 byte as char */
            if ((size - i) > 2) {
                SWO_sendWord(STIM_TRACE, *((uint32_t *)(&data[i])));
                i += 4;
            } else if ((size - i) > 1) {
                SWO_sendShort(STIM_TRACE, *((uint16_t *)(&data[i])));
                i += 2;
            } else {
                SWO_sendChar(STIM_TRACE, *((uint8_t *)(&data[i])));
                i += 1;
            }
        }
    }
}

/*
 *  ======== __SWO_enableWatchpoint ========
 */
void __SWO_enableWatchpoint(uint32_t hdr, SWO_Watchpoint watchpoint, SWO_WatchpointFunction
                            function, uintptr_t address) {
   /* Is the watchpoint available */
   if (!(object->activeWatchpoints & watchpoint)) {
       uint32_t offset = 16 * watchpoint;
       HWREG(CPU_DWT_BASE + CPU_DWT_O_COMP0 + offset) = address;
       HWREG(CPU_DWT_BASE + CPU_DWT_O_MASK0 + offset) = 0;
       HWREG(CPU_DWT_BASE + CPU_DWT_O_FUNCTION0 + offset) = function;

       /* Notify tracer about the watchpoint */
       SWO_sendWord(STIM_HEADER, hdr);
   }
}

/*
 *  ======== __SWO_disableWatchpoint ========
 */
void __SWO_disableWatchpoint(SWO_Watchpoint watchpoint) {
    /* Disable by setting comparator to zero */
    uint32_t offset = 16 * watchpoint;
    HWREG(CPU_DWT_BASE + CPU_DWT_O_COMP0 + offset) = 0;

    /* Remove from active wp mask */
    object->activeWatchpoints &= ~watchpoint;
}
