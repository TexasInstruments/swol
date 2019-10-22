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


#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

/* Include header */
#include <ti/drivers/SWO.h>

/* TI-RTOS headers */
#include <xdc/runtime/Log.h>
#include <xdc/runtime/Diags.h>
#include <xdc/runtime/Text.h>

static uint8_t isOpen = 0;

/* SWO Driver event */
SWO_CREATE_EVENT(SWO_LogModule_KernelLog, SWOWrapper_malloc, "An memory allocation attempt occurred");
SWO_CREATE_EVENT(SWO_LogModule_KernelLog, SWOWrapper_free, "An memory deallocation attempt occurred");

/* SWO inline assembly proxy */
#if defined(__TI_COMPILER_VERSION__)
asm(" .bss    _lrprxy,4,4\n"
    " .global _lrprxy\n");
extern uint32_t _lrprxy;
#endif

/*!
 *  @brief  TI-RTOS Log Callback function.
 *
 *  This TI-RTOS LoggerCallback output function provide a layer to route
 *  kernel generated log messages using the SWO Driver interface.
 *  It will packet the Log event and use the SWO_logBuf() API as output
 *  source. The packet structure used is:
 *  uint32_t word[0]        = Log event level (INFO, WARNING, ERROR)
 *           word[1]        = Log formated text
 *           word[2-(N-1)]  = Log arguments (0 to 8)
 *
 *  NOTE: It requires the TI-RTOS kernel to be running (BIOS_started()) before
 *  being invoked the first time.
 *
 *  @param  sharedArg     Unused
 *
 *  @param  *evr          Pointer to the event record structure.
 *
 *  @params nArgs         Number of Log arguments
 *
 */
void SWO_tirtosLoggerCbOutput(uint32_t sharedArg, Log_EventRec *evr, int32_t nArgs) {
    /* The Log module support up to Log_NUMARGS number of arguments.
     * In addition to this, 1 additional arguments exist if it is
     * an INFO, ERROR or WARNING event. Add an additional argument
     * to append the Log event level.
     */
    uint32_t swoArgs[Log_NUMARGS + 2];
    uint8_t  nSwoArgs = 1;

    /* Set default Log level*/
    swoArgs[0]  = SWO_LogLevel_USER1;

    /* Get the event ID */
    Log_EventId evId    = Log_getEventId(evr->evt);

    /* If first time, make sure SWO Driver is open */
    if (isOpen) {
        SWO_Status status;
        SWO_open(NULL, &status);
        if (status == SWO_STATUS_SUCCESS) {
            isOpen = 1;
        }
    }

    /* If logging an event (evId != Log_PRINTFID), override the default log level.
     * Log level is passed as the first byte of the first word */
    if (evId == (Log_L_info >> 16))
        swoArgs[0] = SWO_LogLevel_INFO;
    if (evId == (Log_L_warning >> 16))
        swoArgs[0] = SWO_LogLevel_WARNING;
    if (evId == (Log_L_error >> 16))
        swoArgs[0] = SWO_LogLevel_ERROR;

    /* Pass along actual number of arguments as the second byte of the first word */
    swoArgs[0] |= nArgs << 8;

    /* INFO, WARNING, ERROR events have a "pre-format" strings
     * prepended, rope it in using the event id and Text module.
     */
    if ((evId != Log_PRINTFID) && Text_isLoaded) {
        swoArgs[nSwoArgs++] = (uint32_t) Text_ropeText(evId);
    }
    else
    {
        swoArgs[nSwoArgs++] = 0;
    }

    /* Copy the remaining arguments */
    memcpy(&swoArgs[nSwoArgs], (const void *)&(evr->arg[0]), nArgs * 4);
    nSwoArgs += nArgs;

    /* Send out using SWO_logbuf() (first two arguments is 1 byte only) */
    SWO_logBuf(SWO_LogModule_KernelLog, SWO_LogLevel_KERNELLOG, "SWO TI-RTOS Log event: ", (uint8_t *) swoArgs, (nSwoArgs * 4));
}

/*!
 *  @brief  Dynamic memory allocation wrappers.
 *
 *  This wrappers provide instrumented versions of "malloc".
 *  Following a allocation attempt, the LR value,
 *  pointer and size is logged using events.
 *
 *  @param  size     memory space to allocate
 *
 */
void* __real_malloc(size_t size);
void* SWO_malloc(size_t size) {
    uint32_t lr;
    /* Store  LR right away*/
#ifdef SWO_LogLevel_MASK
#if defined(__TI_COMPILER_VERSION__)
    asm(" MOVW R0, _lrprxy\n"
        " MOVT R0, _lrprxy\n"
        " STR LR, [R0]\n");
    lr = _lrprxy;
#else
    __asm volatile( "MOV %0, LR"    : "=r" (lr));
#endif
#endif
    /* Perform the malloc */
    void* tmp = __real_malloc(size);

    /* Log it */
    SWO_event(SWO_LogModule_KernelLog, SWO_LogLevel_INFO, SWOWrapper_malloc, lr, tmp, size);

    return tmp;
}

/*!
 *  @brief  Dynamic memory deallocation wrappers.
 *
 *  This wrappers provide instrumented versions of "free".
 *  Following a deallocation attempt, the LR value,
 *  and pointer is logged using events.
 *
 *  @param  ptr     memory to free
 *
 */
void __real_free(void *ptr);
void SWO_free(void* ptr) {
    uint32_t lr;
    /* Store  LR right away*/
#ifdef SWO_LogLevel_MASK
#if defined(__TI_COMPILER_VERSION__)
    asm(" MOVW R0, _lrprxy\n"
        " MOVT R0, _lrprxy\n"
        " STR LR, [R0]\n");
    lr = _lrprxy;
#else
    __asm volatile( "MOV %0, LR"    : "=r" (lr));
#endif
#endif
    /* Perform the free */
    __real_free(ptr);

    /* Log it */
    SWO_event(SWO_LogModule_KernelLog, SWO_LogLevel_INFO, SWOWrapper_free, lr, ptr);
}
