/*
 * Copyright (c) 2018-2019, Texas Instruments Incorporated
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * *  Redistributions of source code must retain the above copyright
 *   notice, this list of conditions and the following disclaimer.
 *
 * *  Redistributions in binary form must reproduce the above copyright
 *   notice, this list of conditions and the following disclaimer in the
 *   documentation and/or other materials provided with the distribution.
 *
 * *  Neither the name of Texas Instruments Incorporated nor the names of
 *   its contributors may be used to endorse or promote products derived
 *   from this software without specific prior written permission.
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
/*!*****************************************************************************
 *  @file       SWO.h
 *      SWO driver interface
 *
 *  This driver implements APIs to perform generic instrumentation and logging
 *  using the ARM ITM module.
 *
 * # Table of Contents
 *  - [Overview](#overview)
 *  - [Usage](#usage)
 *    - [Common Setup](#setup)
 *    - [Opening SWO](#opening)
 *    - [Compile-time Module / Level Enabling](#enabling)
 *    - Functionality
 *      - [Printf](#print)
 *      - [LogBuf](#logbuf)
 *      - [Events](#events)
 *      - [Event Sets](#eventsets)
 *      - [Deferred Data](#deferred)
 *    - [Linker File Modifications](#linker)
 *    - [Power Management](#power)
 *  - <a href="./_s_w_o_8h.html#func-members">API's</a>
 *  - <a href="./_s_w_o_8h.html#define-members">Macros</a>
 *  - <a href="./_s_w_o_8h.html#enum-members">Enums</a>
 *  - <a href="./_s_w_o_8h.html#typdef-members">Typedefs</a>
 *
 *  # Overview <a name="overview"></a>
 *
 *  @note This documentation will explain the SWO Driver API's and how to use them.
 *  For full SWOL system documentation including how to setup the parser,
 *  Wireshark dissector, etc, see the <a href="../../Users_Guide.html">User's Guide</a>
 *
 *  @warning This documentation assumes that the SWOL environment is set up correctly.
 *  This is described in the <a href="../../Users_Guide.html">User's Guide</a>. It is
 *  highly recommended to first perform the Demo from the User's Guide to verify
 *  this before adding SWOL to a separate project.
 *
 *  The ARM ITM module is used to implement instrumentation and logging using a
 *  low-overhead protocol based on SWIT packets. See the
 *  <a href="https://developer.arm.com/docs/ddi0403/e/armv7-m-architecture-reference-manual">ARM Documentation</a>
 *  for more information regarding the ITM Protocol.
 *  This driver adds another level of parsing (the SWO protocol) above ITM
 *  and abstracts the functionality through the API's documented here.
 *
 *  The driver also uses sections to place strings symbols in virtual
 *  off-chip memory regions. This reduces the amount of data that needs to be
 *  sent over the physical interface to a (32-bit) pointer pointing to the
 *  symbol in virtual memory. The output ELF file is then parsed to resolve
 *  the symbol based on the received pointer.
 *
 *  A TI provided tool (Logger) is available for parsing of the ITM data, providing
 *  structured and readable outputs
 *
 *  # Usage <a name="usage"></a>
 *
 *  The following includes a section detailing the minimum steps required to add
 *  SWO logging to an embedded project. These common steps will always be required.
 *  After this, examples of each SWO functionality are provided.
 *
 *  ## Common Setup <a name="setup"></a>
 *
 *  -# Include the SWO header files:
 *     @code
 *     #include <ti/drivers/SWO.h>
 *     #include <ti/drivers/swo/SWOCC26XX.h>
 *     @endcode
 *
 *  -# Add the following source files to the project:
 *     - $SWO_PLUGIN_INSTALL$/source/ti/drivers/SWO.c
 *     - $SWO_PLUGIN_INSTALL$/source/ti/drivers/SWO.h
 *     - $SWO_PLUGIN_INSTALL$/source/ti/drivers/swo/SWOCC26XX.c
 *     - $SWO_PLUGIN_INSTALL$/source/ti/drivers/swo/SWOCC26XX.h
 *     - $SWO_PLUGIN_INSTALL$/source/ti/drivers/swo/SWOUtils.h
 *     - $SWO_PLUGIN_INSTALL$/source/ti/boards/CCxxxx_LAUNCHXL/PowerCCXXX_tirtos.c
 *  -# IDE-Specific:
 *     - In CCS, add the SWOL product in Project Properties->General->Project:
 *       @image html add_ccs_product.png
 *     - In IAR, add $SWO_INSTALL_DIR$/source to the Preprocessor Include Directories
 *       in Project->Options->C/C++ Compiler->Preprocessor:
 *       @image html iar_include.png
 *  -# The following steps are optional:
 *     - Configure the pin to be used by the SWO driver by setting the @ref SWO_PIN
 *     preprocessor define. If not defined, this will default to the SWO pin on
 *     the  launchpad (IOID_18). Ensure that this pin is not used by other hardware.
 *     - Configure the idle buffer size by setting the @ref SWO_IDLE_BUFFER_SIZE
 *     preprocessor define. See [Deferred Data](#deferred) for more information.
 *     If not defined, this will  default to 512.
 *     - Configure the SWO baud rate by setting the @ref SWO_BAUD_RATE preprocessor
 *     define. If not defined, this will default to 12000000.
 *  -# Configure SWO_idleFlush() to be an RTOS Idle task. This is done by adding the
 *     following to the Idle task configuration section of the RTOS configuration
 *     file (xxx.cfg):
 *     @code
 *     Idle.addFunc('&__SWO_idleFlush');
 *     @endcode
 *  -# Update the linker file for the chosen IDE as specified in
 *     [Linker File Modifications](#linker)
 *  -# Open the SWO Driver. See [Opening SWO](#opening)
 *     @code
 *     SWO_Status status;
 *     SWO_open(NULL, &status);
 *     @endcode
 *  -# Enable some logging at compile-time by setting module / level preprocessor defines.
 *     Start by setting ```SWO_LogModule_ENABLE_ALL``` and ```SWO_LogLevel_ENABLE_ALL```. See
 *     [Compile-time Module / Level Enabling](#enabling)
 *
 *  ## Opening SWO<a name="opening"></a>
 *
 *  Before logging, the SWO Driver needs to be enabled by a call to SWO_open().
 *  Multiple calls to SWO_open() are supported as only the first call will
 *  configure the ITM module. If multiple successful calls to SWO_open() are
 *  performed, an equal number of calls to SWO_close() need to be performed
 *  before the driver disables logging (stops sending all ITM data). Following
 *  SWO_open(), the user can use the provided logging APIs for instrumentation
 *  of the software, see the following sub sections covering the available
 *  logging APIs and how to use them.
 *
 *   ## Compile-time Module / Level Enabling<a name="enabling"></a>
 *
 *  For each API, a @ref SWO_LogLevel and @ref SWO_LogModule need to be provided
 *  as initial arguments. The configuration of modules and levels at
 *  compile-time dictates which SWO API's are compiled into the code. Thus, it is
 *  easy to completely remove all SWO flash consumption by not setting any
 *  SWO_XXX_ENABLE_XXX define's.
 *
 *  Per default, all log modules and levels are disabled. The user can choose
 *  to enable all of them by defining ```SWO_LogModule_ENABLE_ALL```
 *  and ```SWO_LogLevel_ENABLE_ALL``` in the global project settings. Individual
 *  modules and levels can be enabled by substituting "ALL" with the relevant
 *  module or level. For more information, see the individual module documentation
 *  in @ref SWO_LogModule. For example, a list of defines to enable a subset of
 *  modules and levels could be:
 *
 *  * ```SWO_LogModule_ENABLE_USER```
 *  * ```SWO_LogModule_ENABLE_DRIVERS```
 *  * ```SWO_LogLevel_ENABLE_ERROR```
 *  * ```SWO_LogLevel_ENABLE_WARNING```
 *
 *  ## Printf <a name="printf"></a>
 *  Printf-like logging is supported using SWO_printf(). Note that
 *  only 32-bit arguments are supported. SWO_printf_deferred() supports deferring
 *  the arguments (see [Deferred Data](#deferred))
 *
 *  Here is a sample of various printf calls:
 *
 *  @code
 *   // Open SWO Driver with default parameters
 *   SWO_Status status;
 *   SWO_open(NULL, &status);
 *
 *   // Do blocking printf
 *   SWO_printf(SWO_LogModule_User, SWO_LogLevel_INFO, "String without arguments");
 *   SWO_printf(SWO_LogModule_User, SWO_LogLevel_INFO, "String with two argument %d %d", 1, 2);
 *
 *   // Do deferred printf
 *   SWO_printf_deferred(SWO_LogModule_User, SWO_LogLevel_INFO, "String without arguments");
 *   SWO_printf_deferred(SWO_LogModule_User, SWO_LogLevel_ERROR, "String with one argument %d", 'A');
 *  @endcode
 *
 *  Here is a sample of what the second printf output above would look like in Wireshark:
 *
 *  @image html swo_printf.png
 *
 *  ## LogBuf <a name="logbuf"></a>
 *  SWO_logBuf() can be used to log a raw data buffer of known-size.
 *  The buffer is logged together with a user provided description of
 *  the content. SWO_logBuf_deferred() can be used to defer data (see [Deferred Data](#deferred)).
 *
 *  Here is a sample of various logBuf calls:
 *
 *  @code
 *  uint8_t testBuf[6] = {0, 1, 2, 3, 4, 5};
 *
 *  // Open SWO Driver with default parameters
 *  SWO_Status status;
 *  SWO_open(NULL, &status);
 *
 *  // Do blocking logBuf
 *  SWO_logBuf(SWO_LogModule_User, SWO_LogLevel_INFO, "This is a test buffer: ", testBuf, 6);
 *
 *  // Do deferred logBuf
 *  SWO_logBuf_deferred(SWO_LogModule_User, SWO_LogLevel_INFO, "Deferred test buffer ", testBuf, 6);
 *  @endcode
 *
 *  Here is a sample of what the first log buffer output from above would look like in Wireshark:
 *
 *  @image html swo_logbuf.png
 *
 *  ## Events <a name="events"></a>
 *  SWO_event() provides functionality to log a pre-defined event from multiple
 *  places in the code. While printf and logbuf provide
 *  flexibility in the amount of data that can be logged, this comes at the tradeoff of
 *  relatively higher code and processing time overhead. In situations where absolute
 *  minimal invasiveness is desired, SWO_event() should be used.
 *
 *  @warning An event must be declared prior to using SWO_event() with @ref SWO_CREATE_EVENT
 *
 *  Here are some samples of various event calls:
 *
 *  @code
 *  SWO_CREATE_EVENT(SWO_LogModule_User, EV2, "Event 2");
 *
 *  SWO_event(SWO_LogModule_BLEStack, SWO_LogLevel_INFO,    EV0);
 *  SWO_event(SWO_LogModule_User, SWO_LogLevel_INFO,    EV1, 1);
 *  SWO_event(SWO_LogModule_User, SWO_LogLevel_INFO, EV2, 1, 2);
 *  SWO_event(SWO_LogModule_User, SWO_LogLevel_WARNING, EV2, 1, 2, 3);
 *  SWO_event(SWO_LogModule_User, SWO_LogLevel_ERROR, EV2, 1, 2, 3, 4);
 *  @endcode
 *
 *  Here is what the output from the third event call above would look like in Wireshark:
 *
 *  @image html swo_event.png
 *
 *  ## Event sets <a name="eventsets"></a>
 *  Event sets can be used to gather multiple logging instructions under one
 *  single event.  This can be used by the receiver to easily parse multiple types
 *  of SWO messages.  An event set is started by calling SWO_EventSet_init() for a
 *  pre-defined event, which will return a non-zero event set ID if successful.
 *  Records can then be added to the set using  SWO_EventSet_printf() and
 *  SWO_EventSet_logBuf(). As in the case for the original printf and
 *  logBuf APIs, there are deferred versions available of each. The event set
 *  must eventually be closed by calling SWO_EventSet_close(). Event sets provide the
 *  highest flexibility in usage at the tradeoff of higher code size and processing
 *  time.
 *
 *  Here is an example of creating an event set with various records:
 *
 *  @code
 *  SWO_CREATE_EVENT(SWO_LogModule_User, EV1, "Event 1");
 *
 *  SWO_EventSet eventSetHandle;
 *  SWO_EventSet_init(SWO_LogModule_User, SWO_LogLevel_INFO, &eventSetHandle, EV1);
 *  SWO_EventSet_printf(SWO_LogModule_User, SWO_LogLevel_INFO, eventSetHandle, "Test printf record %d %d %d", 1, 2, 3);
 *  SWO_EventSet_logBuf(SWO_LogModule_User, SWO_LogLevel_INFO, eventSetHandle, "Test logBuf record: ", testBuf, 6);
 *  SWO_EventSet_printf_deferred(SWO_LogModule_User, SWO_LogLevel_INFO, eventSetHandle, "Deferred test printf record %d %d %d", 1, 2, 3);
 *  SWO_EventSet_logBuf_deferred(SWO_LogModule_User, SWO_LogLevel_INFO, eventSetHandle, "Deferred test logBuf record ", testBuf, 6);
 *  SWO_EventSet_close(SWO_LogModule_User, eventSetHandle);
 *  @endcode
 *
 *  @image html swo_eventset.png
 *
 *  ## Deferred Data <a name="deferred"></a>
 *
 *  Any of the deferred calls above will store the payload data to the idle buffer, the size of which
 *  was configured via @ref SWO_IDLE_BUFFER_SIZE.
 *
 *  Data will only be transmitted from the idle buffer when SWO_idleFlush() is called. Normally, this
 *  occurs during the Idle task if the RTOS has been configured as stated in [Setup](#setup).
 *
 *  If at any point a SWO API can not place its payload data in the idle buffer because there is not
 *  enough room, a Buffer Overflow Packet will be sent to the logger. It will appear in the
 *  Wireshark output as such:
 *
 *  @image html swo_overflow.png
 *
 *  # Linker File Modifications <a name="linker"></a>
 *  In order to use the SWO Driver, a new ".swo_trace" section needs to be setup in the linker
 *  file. This section is used to store information in the .elf file in order to avoid consuming
 *  flash.  The python logger will then pares the .elf file to extract this information.
 *
 *  The .swo_trace section must be placed in a memory region range that does not overlap
 *  with the RAM or FLASH regions.  The section must be placed as "COPY" to ensure the
 *  symbols are available in the ELF output file.
 *
 *  @warning It is important to ensure that the section is exactly called .swo_trace as this
 *  section name is used by the logger python tool when parsing the .elf file.
 *
 *  Example CSS linker file modifications:
 *  @code
 *  // System memory map
 *  MEMORY
 *  {
 *  ...
 *      SWO_TRACE (R) : origin = 0x60000000, length = 0xFFFFFFFF
 *  }
 *
 *  // Section allocation in memory
 *  SECTIONS
 *  {
 *  ...
 *      .swo_trace        :   > SWO_TRACE, type = COPY
 *  ...
 *  }
 *  @endcode
 *
 *  Example IAR linker file modifications:
 *  @code
 *  define region TRACES_AREA      = mem:[from 0x60000000 to 0x6FFFFFFF];
 *
 *  ".swo_trace":
 *  place noload in TRACES_AREA { readonly section .swo_trace };
 *  @endcode
 *
 *  # Power Management <a name="power"></a>

 *  There are several modifications required to the power driver to use SWO with
 *  power management. This is accomplished by compiling the relevant
 *  PowerCCxxxx_tirtos.c file into the project to overwrite the library implemenation
 *  (see [Setup](#setup)).  If desired, continue reading this section for more
 *  information on why this is the case.
 *
 *  The ITM hardware is disabled during CPU low-power modes. To handle this,
 *  SWO_prepareForIdle() needs to be called prior to putting the CPU into low-
 *  power modes. On returning from a low-power mode, SWO_returnFromIdle() need
 *  to be called to re-configure the ITM port and provide time synchronization
 *  with external logger tools. When going into standby, this is handled via the
 *  Power driver notification system. For any other power state such as "idle",
 *  this need to be handled  by the code responsible for this mode as no Power
 *  notifications is  provided.
 *
 * @cond NODOC
 * ## Tracking Dynamic Memory Allocation ##
 * Wrapper functions is available to log usage of dynamic memory inside the
 * application. These wrapper functions replaces the original malloc() and
 * free() calls with instrumented versions. To use these wrappers, the linker
 * file need to be contain symbol mapping in accordance with the toolchain used:
 *
 * ### TI ARM toolchain linker file ###
 * @code
 * --symbol_map=__real_free=free
 * --symbol_map=malloc=SWO_malloc
 * --symbol_map=__real_malloc=malloc
 * --symbol_map=free=SWO_free
 * @endcode
 *
 * ### IAR toolchain ###
 * TODO
 * @endcond //NODOC
 */

#ifndef ti_drivers_SWO__include
#define ti_drivers_SWO__include

#ifdef __cplusplus
extern "C" {
#endif

#include <xdc/std.h>
#include <stddef.h>
#include <stdint.h>

/* Include SWO helper macros */
#include <ti/drivers/swo/SWOUtils.h>

#ifndef SWO_LogLevel_MASK
#ifndef SWO_LogLevel_ENABLE_ALL
/* Is User logs enabled? */
#ifdef SWO_LogLevel_ENABLE_KERNELLOG
/*!
 * SWO log level mask for the kernel module
 */
#define SWO_LogLevel_MASK_KERNELLOG SWO_LogLevel_KERNELLOG
#else
#define SWO_LogLevel_MASK_KERNELLOG 0
#endif

/* Is User logs enabled? */
#ifdef SWO_LogLevel_ENABLE_USER2
/*!
 * SWO log level mask for the User 2 module
 */
#define SWO_LogLevel_MASK_USER2 SWO_LogLevel_USER2
#else
#define SWO_LogLevel_MASK_USER2 0
#endif

/* Is User logs enabled? */
#ifdef SWO_LogLevel_ENABLE_USER1
/*!
 * SWO log level mask for the User 1 module
 */
#define SWO_LogLevel_MASK_USER1 SWO_LogLevel_USER1
#else
#define SWO_LogLevel_MASK_USER1 0
#endif

/* Is Error logs enabled? */
#ifdef SWO_LogLevel_ENABLE_ERROR
/*!
 * SWO log level mask for the error level
 */
#define SWO_LogLevel_MASK_ERROR SWO_LogLevel_ERROR
#else
#define SWO_LogLevel_MASK_ERROR 0
#endif

/* Is Warning logs enabled? */
#ifdef SWO_LogLevel_ENABLE_WARNING
/*!
 * SWO log level mask for the warning level
 */
#define SWO_LogLevel_MASK_WARNING SWO_LogLevel_WARNING
#else
#define SWO_LogLevel_MASK_WARNING 0
#endif

/* Is Info logs enabled? */
#ifdef SWO_LogLevel_ENABLE_INFO
/*!
 * SWO log level mask for the info level
 */
#define SWO_LogLevel_MASK_INFO SWO_LogLevel_INFO
#else
#define SWO_LogLevel_MASK_INFO 0
#endif

/*!
 * Mask of currently enabled log levels.
 *
 * Is a bitwise OR of the enabled log levels (i.e. @ref SWO_LogLevel_MASK_KERNELLOG)
 *
 * @note If SWO_LogLevel_ENABLE_ALL is defined, this is set to 0xFFFFFFFF
 */
#define SWO_LogLevel_MASK (SWO_LogLevel_MASK_KERNELLOG  | SWO_LogLevel_MASK_USER1 |  \
                           SWO_LogLevel_MASK_USER2      | SWO_LogLevel_MASK_ERROR |      \
                           SWO_LogLevel_MASK_WARNING    | SWO_LogLevel_MASK_INFO)
#else
#define SWO_LogLevel_MASK 0xFFFFFFFF
#endif
#endif

#ifndef SWO_LogModule_MASK
#ifndef SWO_LogModule_ENABLE_ALL
/* Is BLEStack log module enabled? */
#ifdef SWO_LogModule_ENABLE_BLE
#define SWO_LogModule_MASK_BLE SWO_LogModule_BLEStack
#else
#define SWO_LogModule_MASK_BLE 0
#endif

/* Is Driver log module enabled? */
#ifdef SWO_LogModule_ENABLE_DRIVERS
#define SWO_LogModule_MASK_DRIVERS SWO_LogModule_Driver
#else
#define SWO_LogModule_MASK_DRIVERS 0
#endif

/* Is User log module enabled? */
#ifdef SWO_LogModule_ENABLE_USER
#define SWO_LogModule_MASK_USER SWO_LogModule_User
#else
#define SWO_LogModule_MASK_USER 0
#endif

/* Is KernelLog log module enabled? */
#ifdef SWO_LogModule_ENABLE_KERNELLOG
#define SWO_LogModule_MASK_KERNELLOG SWO_LogModule_KernelLog
#else
#define SWO_LogModule_MASK_KERNELLOG 0
#endif

/* Is RTSL log module enabled? */
#ifdef SWO_LogModule_ENABLE_RTLS
#define SWO_LogModule_MASK_RTLS SWO_LogModule_RTLS
#else
#define SWO_LogModule_MASK_RTLS 0
#endif

/* Is DMM log module enabled? */
#ifdef SWO_LogModule_ENABLE_DMM
#define SWO_LogModule_MASK_DMM SWO_LogModule_DMM
#else
#define SWO_LogModule_MASK_DMM 0
#endif

/* Is RF Driver log module enabled? */
#ifdef SWO_LogModule_ENABLE_RF
#define SWO_LogModule_MASK_RF SWO_LogModule_RF
#else
#define SWO_LogModule_MASK_RF 0
#endif

/* Create combined mask */
#define SWO_LogModule_MASK ( \
                SWO_LogModule_MASK_BLE  | SWO_LogModule_MASK_DRIVERS    | \
                SWO_LogModule_MASK_USER | SWO_LogModule_MASK_KERNELLOG  | \
                SWO_LogModule_MASK_RTLS | SWO_LogModule_MASK_DMM        | \
                SWO_LogModule_MASK_RF)
#else
/* All log modules are enabled */
#define SWO_LogModule_MASK 0xFFFFFFFF
#endif
#endif

#ifndef SWO_IDLE_BUFFER_SIZE
/// Buffer size used for payload of deferred data
#define SWO_IDLE_BUFFER_SIZE        512
#endif

#ifndef SWO_PIN
/// Pin used to send ITM data from SWO driver
#define SWO_PIN                     IOID_18
#endif

#ifndef SWO_BAUD_RATE
/// Baud rate of serial ITM data from SWO driver
#define SWO_BAUD_RATE               12000000
#endif

/// @cond NODOC
#if (SWO_LogModule_MASK == 0x00000000)
#define SWO_MACRO(x)
#else
#define SWO_MACRO(x) do{ x }while(0)
#endif

#if defined(__IAR_SYSTEMS_ICC__)

/* Place a string in trace format section */
#define SWO_PLACE_FORMAT_IN_SECTOR(opcode, isDeferred, isEventSet, logLevel, logModule, format, nargs) __root static const char _CONCAT2(SWOSymbol, __LINE__)[] @ ".swo_trace" = APPEND_META_INFORMATION_TO_FORMAT(opcode, isDeferred, isEventSet, __FILE__, __LINE__, logLevel, logModule, format, nargs);

//#if defined (__TI_COMPILER_VERSION__)
#else

/* Place a string in trace format section */
#define SWO_PLACE_FORMAT_IN_SECTOR(opcode, isDeferred, isEventSet, logLevel, logModule, format, nargs) static const char _CONCAT2(SWOSymbol, __LINE__)[] __attribute__((section(".swo_trace"))) __attribute__((used)) = APPEND_META_INFORMATION_TO_FORMAT(opcode, isDeferred, isEventSet, __FILE__, __LINE__, logLevel, logModule, format, nargs);

#endif
/// @endcond //NODOC

/**
 * Create a SWO Event
 *
 * Places an event string in the trace section and creates a @ref SWO_Event that can
 * be used as an "Event Handler"
 *
 * @param logModule  Module that this corresponds to
 * @param event      @ref SWO_Event that this created event can be referenced by in code
 * @param info       String that corresponds to this event
 */
#define SWO_CREATE_EVENT(logModule, event, info) \
         SWO_PLACE_FORMAT_IN_SECTOR(SWO_EVENT_CREATION, 0, 0, event, logModule, info, 0) \
         enum { event = 0, _CONCAT2(event, line)  = __LINE__ } _CONCAT2(logModule, event) = event;

/// @cond NODOC

/* Macros to prevent code placement if no modules is logged */
#define SWO_INIT() SWO_MACRO(__SWO_init();)

#define SWO_OPEN(params, status) SWO_MACRO(__SWO_open(params, status);)

#define SWO_PREPARE_FOR_IDLE(reason) SWO_MACRO(__SWO_prepareForIdle(reason);)

#define SWO_RETURN_FROM_IDLE() SWO_MACRO(__SWO_returnFromIdle();)

#define SWO_CLOSE() SWO_MACRO(__SWO_close();)0

#define SWO_IDLE_FLUSH() SWO_MACRO(__SWO_idleFlush();)

/* Macros to mask string placement and function calls */
#define SWO_PRINTF(logModule, logLevel, isDeferred, isEventSet, format, ...) \
        SWO_MACRO( \
                  if ((logLevel & SWO_LogLevel_MASK) && (logModule & SWO_LogModule_MASK)) { \
                  SWO_PLACE_FORMAT_IN_SECTOR(SWO_OPCODE_FORMATED_TEXT, isDeferred, isEventSet, logLevel, logModule, format,GET_NUMBER_OF_ARGS_MINUS_EVENT_SET(__VA_ARGS__)) \
                  __SWO_printf(isDeferred, isEventSet, (uint32_t) &_CONCAT2(SWOSymbol, __LINE__), \
                               GET_NUMBER_OF_ARGS_MINUS_EVENT_SET(__VA_ARGS__), APPLY(CAST_UINT32, __VA_ARGS__) + 0); }   \
                  )

#define SWO_EVENT(logModule, logLevel, ...) \
        SWO_MACRO( \
                  if ((logLevel & SWO_LogLevel_MASK) && (logModule & SWO_LogModule_MASK)) { \
                  SWO_PLACE_FORMAT_IN_SECTOR(SWO_OPCODE_EVENT, FALSE, FALSE, logLevel, logModule, FIRST_ARG(__VA_ARGS__), GET_NUMBER_OF_ARGS(__VA_ARGS__)) \
                  _EVENT_GET_OVERRIDE(__VA_ARGS__,                                  \
                                      __SWO_event4, __SWO_event3, __SWO_event2,     \
                                      __SWO_event1, __SWO_event0) ((uint32_t) &_CONCAT2(SWOSymbol, __LINE__), \
                                      APPLY(CAST_UINT32, __VA_ARGS__) + _CONCAT2(logModule, FIRST_ARG(__VA_ARGS__)));}     \
                    )

#define SWO_LOGBUF(logModule, logLevel, isDeferred, isEventSet, eventSet, format, data, size) \
        SWO_MACRO( \
                  if ((logLevel & SWO_LogLevel_MASK) && (logModule & SWO_LogModule_MASK)) { \
                  SWO_PLACE_FORMAT_IN_SECTOR(SWO_OPCODE_BUFFER, isDeferred, isEventSet, logLevel, logModule, format, 0) \
                  __SWO_logBuf(isDeferred, isEventSet, (uint32_t) &_CONCAT2(SWOSymbol, __LINE__), eventSet, data, size);} \
                  )

#define SWO_EVENT_SET_INIT(logLevel, logModule, ptr, event) \
        SWO_MACRO( \
                  if ((logLevel & SWO_LogLevel_MASK) && (logModule & SWO_LogModule_MASK)) { \
                  SWO_PLACE_FORMAT_IN_SECTOR(SWO_OPCODE_EVENT_SET_START, FALSE, TRUE, logLevel, logModule, event, 0) \
                  *ptr = __SWO_EventSet_init((uint32_t) &_CONCAT2(SWOSymbol, __LINE__), event);} \
                  )

#define SWO_EVENT_SET_CLOSE(logLevel, logModule, record) \
        SWO_MACRO( \
                  SWO_PLACE_FORMAT_IN_SECTOR(SWO_OPCODE_EVENT_SET_END, FALSE, TRUE, logLevel, logModule, 0, 0) \
                  __SWO_EventSet_close((uint32_t) &_CONCAT2(SWOSymbol, __LINE__), record); \
                  )

#define SWO_ENABLE_WATCHPOINT(logLevel, logModule, string, wp, fxn, addr) \
        SWO_MACRO( \
                  if ((logLevel & SWO_LogLevel_MASK) && (logModule & SWO_LogModule_MASK)) { \
                  SWO_PLACE_FORMAT_IN_SECTOR(SWO_OPCODE_WATCHPOINT, wp, fxn, logLevel, logModule, string, addr) \
                  __SWO_enableWatchpoint((uint32_t) &_CONCAT2(SWOSymbol, __LINE__), wp, fxn, addr);} \
                  )
/// @endcond //NODOC

/*!
 * SWO Event Set Handle
 *
 * A handle that is returned from a @ref SWO_EventSet_init and is used to
 * identify the event set to pass into other EventSet API's
 */
typedef uint8_t SWO_EventSet;

/*!
 * SWO Event Handle
 *
 * These are created by @ref SWO_CREATE_EVENT and used to identify events to
 * pass into other API's.
 */
typedef uintptr_t SWO_Event;

/*!
 * Available Log levels
 *
 * The functionality of these is defined per @ref SWO_LogModule
 */
typedef enum SWO_LogLevel_ {
    SWO_LogLevel_INFO = 1,      //!< Info
    SWO_LogLevel_WARNING = 2,   //!< Warning
    SWO_LogLevel_ERROR = 4,     //!< Error
    SWO_LogLevel_KERNELLOG = 8, //!< Kernel Log
    SWO_LogLevel_USER1 = 16,    //!< User 1
    SWO_LogLevel_USER2 = 32,    //!< User 2
} SWO_LogLevel;

/*!
 *  These are the available log modules in the SWO driver.
 */
typedef enum SWO_LogModule_ {
    SWO_LogModule_BLEStack = 1,   //!< BLE Stack (RFU)
    /**
     * Driver Log Module (experimental)
     *
     * This module provides functionality to route pre-existing TI-DRIVER Log messages.
     *
     * @pre SWO_LogModule_ENABLE_DRIVERS or SWO_LogModule_ENABLE_ALL must be
     * defined at compile-time.
     *
     * ### Routing TI-RTOS Log events out over SWO:
     *
     * To support routing the TI-RTOS Log events out over SWO, a LoggerCallback
     * output function is provided, **SWO_tirtosLoggerCbOutput()**, as part of the
     * SWO.c source file. This can be registered as the LoggerCallback output
     * in the TI-RTOS kernel configuration file in order to use the SWO Driver as
     * output source.
     *
     * Currently the implementation of **SWO_tirtosLoggerCbOutput()** only
     * supports being used for Log events originating from user code and not from
     * modules. To enable TI-RTOS Log over SWO in the kernel, the following
     * modifications need to be done in the kernel configuration file:
     *
     * @code
     * var Diags = xdc.useModule('xdc.runtime.Diags');
     * var Log = xdc.useModule('xdc.runtime.Log');
     * var Main = xdc.useModule('xdc.runtime.Main');
     * var LoggerCallback = xdc.useModule('xdc.runtime.LoggerCallback');
     *
     * LoggerCallback.outputFxn = "&SWO_tirtosLoggerCbOutput";
     * var loggerParams = new LoggerCallback.Params();
     * loggerParams.arg = 1;
     * Main.common$.logger = LoggerCallback.create(loggerParams);
     *
     * Main.common$.diags_USER1    = Diags.ALWAYS_ON;
     * Main.common$.diags_USER2    = Diags.ALWAYS_ON;
     * Main.common$.diags_INFO     = Diags.ALWAYS_ON;
     * @endcode
     *
     * @warning If the TI-RTOS configuration uses UIA LoggingSetup, this has to
     * be disabled as it will override the ``Main.common$.logger`` argument.
     */
    SWO_LogModule_Driver = 2,
    /**
     * The User module is not used anywhere. This is intended to be used by
     * the user.
     *
     * @pre  SWO_LogModule_ENABLE_USER or  SWO_LogModule_ENABLE_ALL must be
     * defined at compile-time.
     */
    SWO_LogModule_User = 4,
    /**
     * Kernel Log Module (experimental)
     *
     * This module provides a few helper functions exist for convenient instrumentation
     * of the kernel. This includes functionality to route TI-RTOS Log messages
     * via the SWO driver and instrumented versions of malloc and free.
     *
     * @pre  SWO_LogModule_ENABLE_KERNELLOG or  SWO_LogModule_ENABLE_ALL must be
     * defined at compile-time.
     *
     * @pre  SWO_LogLevel_ENABLE_KERNELLOG or  SWO_LogLevel_ENABLE_ALL must be
     * defined at compile-time.
     *
     * ### Routing Kernel Log events out over SWO:
     *
     * To support routing the Kernel Log events out over SWO, a LoggerCallback
     * output function is provided, **SWO_tirtosLoggerCbOutput()**, as part of the
     * SWO.c source file. This can be registered as the LoggerCallback output
     * in the TI-RTOS kernel configuration file in order to use the SWO Driver as
     * output source.
     *
     * Currently the implementation of **SWO_tirtosLoggerCbOutput()** only
     * supports being used for Log events originating from user code and not from
     * modules. To enable TI-RTOS Log over SWO in the kernel, the following
     * modifications need to be done in the kernel configuration file:
     *
     * @code
     * var Diags = xdc.useModule('xdc.runtime.Diags');
     * var Log = xdc.useModule('xdc.runtime.Log');
     * var Main = xdc.useModule('xdc.runtime.Main');
     * var LoggerCallback = xdc.useModule('xdc.runtime.LoggerCallback');
     *
     * LoggerCallback.outputFxn = "&SWO_tirtosLoggerCbOutput";
     * var loggerParams = new LoggerCallback.Params();
     * loggerParams.arg = 1;
     * Main.common$.logger = LoggerCallback.create(loggerParams);
     *
     * Main.common$.diags_USER1    = Diags.ALWAYS_ON;
     * Main.common$.diags_USER2    = Diags.ALWAYS_ON;
     * Main.common$.diags_INFO     = Diags.ALWAYS_ON;
     * @endcode
     *
     * @warning If the TI-RTOS configuration uses UIA LoggingSetup, this has to
     * be disabled as it will override the ``Main.common$.logger`` argument.
     *
     * ### Miscellaneous Functionality
     *
     * Periodic sampling of the program counter is supported and can be enabled by
     * defining ```SWO_PcSampling_ENABLE```. When enabled, the program counter will be
     * sampled and sent over the ITM line as a hardware trace packet every 32nd
     * clock cycle. The python Logger will translate the addresses into function
     * names for Wireshark Output.
     */
    SWO_LogModule_KernelLog = 8,  //!< Kernel Log (todo)
    SWO_LogModule_RTLS = 16,      //!< RTLS (RFU)
    SWO_LogModule_DMM  = 32,      //!< DMM (RFU)
    SWO_LogModule_RF  = 64,       //!< RF (RFU)
} SWO_LogModule;

/*!
 * Available ITM stimulus ports.
 *
 * First 16 stimulus ports are reserved for driver back-end and
 * future use. The last 16 ports can be used for raw ITM data output.
 */
typedef enum SWO_StimulusPorts_ {
    STIM_RESV0  = 0, //!< Port 0. Reserved for future use
    STIM_RESV1,  //!< Port 1. Reserved for future use
    STIM_RESV2,  //!< Port 2. Reserved for future use
    STIM_RESV3,  //!< Port 3. Reserved for future use
    STIM_RESV4,  //!< Port 4. Reserved for future use
    STIM_RESV5,  //!< Port 5. Reserved for future use
    STIM_RESV6,  //!< Port 6. Reserved for future use
    STIM_RESV7,  //!< Port 7. Reserved for future use
    STIM_RESV8,  //!< Port 8. Reserved for future use
    STIM_RESV9,  //!< Port 9. Reserved for future use
    STIM_RESV10,  //!< Port 10. Reserved for future use
    STIM_TIME_SYNC = 11,  //!< Port 11. Reserved for driver Time Sync
    STIM_DRIVER, //!< Port 12. Reserved for miscellaneous driver functionality
    STIM_IDLE, //!< Port 13. Reserved for driver messages about Idle
    STIM_HEADER, //!< Port 14. Reserved for driver Header messages
    STIM_TRACE, //!< Port 15. Reserved for driver main data transfer

    /* Ports 16-31 can be used for raw data output  */
    STIM_RAW0 = 16,  //!< Port 16. Can be used for sending raw ITM data
    STIM_RAW1, //!< Port 17. Can be used for sending raw ITM data
    STIM_RAW2, //!< Port 18. Can be used for sending raw ITM data
    STIM_RAW3, //!< Port 19. Can be used for sending raw ITM data
    STIM_RAW4, //!< Port 20. Can be used for sending raw ITM data
    STIM_RAW5, //!< Port 21. Can be used for sending raw ITM data
    STIM_RAW6, //!< Port 22. Can be used for sending raw ITM data
    STIM_RAW7, //!< Port 23. Can be used for sending raw ITM data
    STIM_RAW8, //!< Port 24. Can be used for sending raw ITM data
    STIM_RAW9, //!< Port 25. Can be used for sending raw ITM data
    STIM_RAW10, //!< Port 26. Can be used for sending raw ITM data
    STIM_RAW11, //!< Port 27. Can be used for sending raw ITM data
    STIM_RAW12, //!< Port 28. Can be used for sending raw ITM data
    STIM_RAW13, //!< Port 29. Can be used for sending raw ITM data
    STIM_RAW14, //!< Port 30. Can be used for sending raw ITM data
    STIM_RAW15  //!< Port 31. Can be used for sending raw ITM data
} SWO_StimulusPorts;


/*!
 *  Available watchpoints.
 *
 * These ares used by @ref SWO_enableWatchpoint and @ref SWO_disableWatchpoint
 */
typedef enum SWO_Watchpoint_ {
    SWO_Watchpoint0 = 0,  //!< Watchpoint 0
    SWO_Watchpoint1,      //!< Watchpoint 1
    SWO_Watchpoint2,      //!< Watchpoint 2
    SWO_Watchpoint3,      //!< Watchpoint 3
} SWO_Watchpoint;

/*!
 * Available watchpoint functions.
 *
 * These are defined in the ARM ITM Specification
 */
typedef enum SWO_WatchpointFunction_ {
    SWO_Disabled                        = 0,   //!< Disabled
    SWO_EmitPc                          = 1,   //!< Emit Program Counter
    SWO_EmitDataOnReadWrite             = 2,   //!< Emit Data on Read or Write
    SWO_SamplePcAndEmitDataOnReadWrite  = 3,   //!< Emit Program Counter on Read or Write
    SWO_SampleDataOnRead                = 0xC, //!< Sample Data on Read
    SWO_SampleDataOnWrite               = 0xD, //!< Sample Data on Write
    SWO_SamplePcAndDataOnRead           = 0xE, //!< Sample PC and Data on Read
    SWO_SamplePcAndDataOnWrite          = 0xF, //!< Sample PC and Data on Write
} SWO_WatchpointFunction;

/// @cond NODOC
// TODO These need to be updated
/*!
 *  SWO protocol op codes.
 *
 *  Defines the type of the logging output.
 */
typedef enum SWO_OpCode_ {
    /*! Used for printf logging.
     *
     * Header argument zero is used to pass the scaled pointer-pointer to the format string:
     * * arg0 = **(format string) / 4
     * * arg1 = N/A
     *
     * If the printf is part of an active event set, the arguments order
     * change to also contain the record set id and count:
     * * arg0 = (record set handle << 6) | (record count)
     * * arg1 = **(format string) / 4

     * Following the header is the arguments pass to the printf function.
     * All arguments are sent as 32-bit words. The arguments can either be
     * sent immediately or deferred to the idle buffer. Deferring to the
     * idle buffer requires an idle buffer.
     */
    SWO_OPCODE_FORMATED_TEXT = 0,

    /*! op code used for event logging. Header argument
     * zero is used to pass the scaled pointer-pointer to the event string
     * while argument one is used to pass the scaled pointer-pointer to
     * the string containing the location and meta-data connected to
     * the event call:
     * * arg0 = **(event string) / 4
     * * arg1 = **(location string) / 4
     *
     * Following the header is the arguments pass to the event function.
     * All arguments are sent as 32-bit words.
     */
    SWO_OPCODE_EVENT,

    /*! op code used to initialize event set logging. Header argument
     * one is used to pass the scaled pointer-pointer to the location string
     * while argument zero is used to pass the record set id and count.
     * In case of a third argument, it contains the scaled pointer-pointer to the
     * event string:
     * * arg0 = (record set id << 6) | (record count)
     * * arg1 = **(location string) / 4
     * * arg2 = **(event string) / 4
     */
    SWO_OPCODE_EVENT_SET_START,


    /*! op code used to close an event set. Header argument
     * one contain the scaled pointer-pointer to the location string while
     * argument zero is used to pass the record set id and count:
     * * arg0 = (record set handle << 6) | (record count)
     * * arg1 = **(location string) / 4
     */
    SWO_OPCODE_EVENT_SET_END,

    /*! op code used for buffer logging. Header argument
     * zero is used to pass the size of the buffer  while argument
     * one is used to pass the scaled pointer-pointer to the format string:
     * * arg0 = buffer size
     * * arg1 = **(format string)
     *
     * If the buffer is part of an active event set, the arguments order
     * change to also contain the record set id and count:
     * * arg0 = (record set handle << 6) | (record count)
     * * arg1 = buffer size
     * * arg2 = **(format string) / 4
     *
     * Following the header is the data passed to the logBuf function,
     * data are sent as 8,16 or 32-bit packets. The data can either be
     * sent immediately or deferred to the idle buffer. Deferring to the
     * idle buffer requires an idle buffer.
     */
    SWO_OPCODE_BUFFER,

    /*! op code used to signal a idle buffer overflow and that
     * the data was discarded. Argument zero contains the
     * op code used when the overflow occurred. Argument one depends
     * on the opcode received in argument 0:
     *  * arg0 = SWO_OPCODE_FORMATED_TEXT:
     *     * arg1 = **(format string) / 4
     *
     *  * arg0 = SWO_OPCODE_BUFFER:
     *     * arg1 = **(format string) / 4
     */
    SWO_OPCODE_IDLE_BUFFER_OVERFLOW,

    /*! op code used to signal a watchpoint being enabled.
     * Header argument zero is used to pass the current watchpoint
     * and function configuration while argument one is used to pass the
     * pointer-pointer to the scaled format string. Argument three contains the
     * address for which the watchpoint is configured.
     * * arg0 = (function << 2) | (watchpoint & 0x03)
     * * arg1 = **(format string) / 4
     * ' arg2 = address
     */
    SWO_OPCODE_WATCHPOINT,

    /*! op code used to sync device time.
     * Does not use any of the header arguments.
     *
     * Following an sync header, three 32-bit word will be sent
     * out containing the Radio timer and RTC value:
     * * word 0-1 = RTC Timer value
     */
    SWO_OPCODE_SYNC_TIME,
} SWO_OpCode;
/// @endcond //NODOC

/*!
 *  SWO return statuses.
 */
typedef enum SWO_Status_ {
    /// Functionality completed successfully
    SWO_STATUS_SUCCESS = 0,
    /// SWO can't be opened because the pin is already in use
    SWO_STATUS_PIN_UNAVAILABLE,
} SWO_Status;

// TODO: Is this needed?
/*!
 *  SWO Parameters
 *
 *  Currently no parameters. Added for compatibility
 *  reasons.
 *
 *  @sa       SWO_Params_init()
 */
typedef struct SWO_Params_ {
    uint32_t dummy;  //!< Not used
} SWO_Params;

/*!
 *  Function to initialize the SWO module
 *
 *  @pre The SWO_config structure must exist and be persistent before this
 *       function can be called. This function must also be called before
 *       any other SWO driver APIs.
 */
void SWO_init();

/*!
 *  Function to open the SWO module
 *
 *  @pre    SWO_init() must have been called prior to this API.
 *
 *  @param  params Pointer to a parameter block. Not in use.
 *  @param  status Pointer to a @ref SWO_Status variable to store status in.
 *
 *  @sa     SWO_close()
 */
void SWO_open(SWO_Params *params, SWO_Status* status);

/*!
 *  Function to close the SWO module
 *
 *  @pre SWO_open() must have been called prior to this API.
 *
 * @sa     SWO_init()
 */
void SWO_close();

/*!
 *  Function to perform printf style logging.
 *
 *  This function call will block until all data has been sent out over the
 *  SWO interface.
 *
 *  @sa SWO_printf_deferred()
 *
 *  @param  logModule Module that this corresponds to
 *  @param  logLevel  Level that this corresponds to
 *  @param  format    Formated string including format specifiers
 *  @param  ...       Additional arguments to replace format specifiers
 */
void SWO_printf(SWO_LogModule logModule, SWO_LogLevel logLevel, const char* format, ...);

/*!
 *  Function to perform printf style logging, sending payload from idle loop
 *
 *  This function call will defer the sending of arguments to the idle
 *  buffer. The arguments will be sent following an SWO_idleFlush().
 *
 *  @sa SWO_printf()
 *
 *  @param  logModule Module that this corresponds to
 *  @param  logLevel  Level that this corresponds to
 *  @param  format    Formated string including format specifiers
 *  @param  ...       Additional arguments to replace format specifiers.
 */
void SWO_printf_deferred(SWO_LogModule logModule, SWO_LogLevel logLevel, const char* format, ...);

/*!
 *  Function to log a known-sized buffer.
 *
 *  This function call will block until all data has been sent out over the
 *  SWO interface. The description string may contain a single token to suggest
 *  how to interpret the buffer (see below). If the string contain no tokens,
 *  the buffer will be interpreted as raw data when received.
 *
 *  Tokens:
 *  * %!S - Data is a string
 *  * %!E - Data has reversed endianness
 *
 *  @sa SWO_logBuf_deferred()
 *
 *  @param  logModule Module that this corresponds to
 *  @param  logLevel  Level that this corresponds to
 *  @param  string    String describing the buffer, optionally containing a token
 *  @param  *data     Pointer to the data buffer
 *  @param  size      Size of the buffer
 */
void SWO_logBuf(SWO_LogModule logModule, SWO_LogLevel logLevel, const char* string, uint8_t *data, size_t size);

/*!
 *  Function to log a known-sized buffer, sending payload from idle loop.
 *
 *  This function call will defer the sending of buffer data to the idle
 *  buffer. The arguments will be sent following SWO_idleFlush().
 *  The description string may contain a single token to suggest how to interpret
 *  the buffer. If the string contain no tokens, the buffer will we interpreted as raw data.
 *
 *  Tokens:
 *  * %!S - Data is a string
 *  * %!E - Data has reversed endianness
 *
 *  @sa SWO_logBuf()
 *
 *  @param  logModule Module that this corresponds to
 *  @param  logLevel  Level that this corresponds to
 *  @param  string    String describing the buffer, optionally containing a token
 *  @param  *data     Pointer to the data buffer
 *  @param  size      Size of the buffer
 */
void SWO_logBuf_deferred(SWO_LogModule logModule, SWO_LogLevel logLevel, const char* string, uint8_t *data, size_t size);

/*!
 *  Function to perform event style logging with up to four arguments.
 *
 *  This function call will block until all the event arguments have been sent
 *  out over the SWO interface.
 *
 *  @pre SWO_CREATE_EVENT() must have been called to define a @ref SWO_Event
 *
 *  @param  logModule Module that this corresponds to
 *  @param  logLevel  Level that this corresponds to
 *  @param  event     Event that this corresponds to
 *  @param  ...       Up to four additional 32-bit arguments.
 */
void SWO_event(SWO_LogModule logModule, SWO_LogLevel logLevel, SWO_Event event, ...);

/*!
 *  Initializes an event set
 *
 *  This function call will allocate a new event set that remains open until
 *  closed.
 *
 *  @pre SWO_CREATE_EVENT() must have been called to define a @ref SWO_Event that
 *  will be associated with this event set
 *
 *  @sa SWO_EventSet_close()
 *
 *  @param  logModule Module that this corresponds to
 *  @param  logLevel  Level that this corresponds to*
 *  @param  *set      Pointer to event set handle created from this function
 *  @param  event     Event that this corresponds to
 */
void SWO_EventSet_init(SWO_LogModule logModule, SWO_LogLevel logLevel, SWO_EventSet *set, SWO_Event event);

/*!
 *  Function to add a printf record to an open @ref SWO_EventSet
 *
 *  This function call will block until all data has been sent out over the
 *  SWO interface.
 *
 *  @pre SWO_EventSet_init() must have been called to define a @ref SWO_EventSet that
 *  this printf will be appended to
 *
 *  @sa SWO_EventSet_printf_deferred()
 *
 *  @param  logModule Module that this corresponds to
 *  @param  logLevel  Level that this corresponds to
 *  @param  rec       Handle for @ref SWO_EventSet
 *  @param  format    Formated string including format specifiers
 *  @param  ...       Additional arguments to replace format specifiers
 */
void SWO_EventSet_printf(SWO_LogModule logModule, SWO_LogLevel logLevel, SWO_EventSet rec, const char* format, ...);

/*!
 *  Function to add a printf record to a open @ref SWO_EventSet, sending payload from idle loop
 *
 *  This function call will defer the sending of arguments to the idle
 *  buffer. The arguments will be sent following SWO_idleFlush().
 *
 *  @pre SWO_EventSet_init() must have been called to define a @ref SWO_EventSet that
 *  this printf will be appended to
 *
 *  @sa SWO_EventSet_printf()
 *
 *  @param  logModule Module that this corresponds to
 *  @param  logLevel  Level that this corresponds to
 *  @param  rec       Handle for @ref SWO_EventSet
 *  @param  format    Formated string, including format specifiers
 *  @param  ...       Additional arguments to replace format specifiers
 */
void SWO_EventSet_printf_deferred(SWO_LogModule logModule, SWO_LogLevel logLevel, SWO_EventSet rec, const char* format, ...);

/*!
 *  Function to add a known-size buffer to an open @ref SWO_EventSet
 *
 *  This function call will block until all data has been sent out over the
 *  SWO interface.
 *
 *  @pre SWO_EventSet_init() must have been called to define a @ref SWO_EventSet that
 *  this logged bugger will be appended to
 *
 *  @sa SWO_EventSet_logBuf_deferred()
 *
 *  @param  logModule Module that this corresponds to
 *  @param  logLevel  Level that this corresponds to
 *  @param  rec       Handle for @ref SWO_EventSet
 *  @param  string    String describing the buffer
 *  @param  *data     Pointer to the data buffer
 *  @param  size      Size of the buffer
 */
void SWO_EventSet_logBuf(SWO_LogModule logModule, SWO_LogLevel logLevel, SWO_EventSet rec, const char* string, uint8_t *data, size_t size);

/*!
 *  Function to add a known-size buffer to an open @ref SWO_EventSet, sending payload from idle loop
 *
 *  This function call will defer the sending of buffer data to the idle
 *  buffer. The arguments will be sent following an SWO_idleFlush().
 *
 *  @pre SWO_EventSet_init() must have been called to define a @ref SWO_EventSet that
 *  this logged bugger will be appended to
 *
 *  @sa SWO_EventSet_logBuf()
 *
 *  @param  logModule Module that this corresponds to
 *  @param  logLevel  Level that this corresponds to
 *  @param  rec       Handle for @ref SWO_EventSet
 *  @param  string    String describing the buffer
 *  @param  *data     Pointer to the data buffer
 *  @param  size      Size of the buffer
 */
void SWO_EventSet_logBuf_deferred(SWO_LogModule logModule, SWO_LogLevel logLevel, SWO_EventSet rec, const char* string, uint8_t *data, size_t size);

/*!
 *  Function to close an open @ref SWO_EventSet
 *
 *  This function call will close and free an open event set.
 *
 *  @pre SWO_EventSet_init() must have been called to initalize an event set
 *
 *  @param  logModule Module that this corresponds to
 *  @param  rec       Handle for @ref SWO_EventSet
 */
void SWO_EventSet_close(SWO_LogModule logModule, SWO_EventSet rec);

/*!
 *  Function to enable a data watchpoint
 *
 *  This function call will enable a watchpoint at a specific
 *  address if the watchpoint is available. A string can be used to
 *  easily identify what is being watched.
 *
 *  @sa SWO_disableWatchpoint()
 *
 *  @param  logModule   Module that this corresponds to
 *  @param  string      String describing the watchpoint
 *  @param  watchpoint  Watchpoint to use
 *  @param  function    Watchpoint function to enable
 *  @param  address     Address to watch
 */
void SWO_enableWatchpoint(SWO_LogModule logModule, const char* string, SWO_Watchpoint watchpoint, SWO_WatchpointFunction function, uintptr_t address);

/*!
 *  Function to disable an data watchpoint
 *
 *  This function call will disable a watchpoint
 *
 *  @pre SWO_enableWatchpoint() must have been used to enable a watchpoint
 *
 *  @param  watchpoint  Watchpoint to disable
 */
void SWO_disableWatchpoint(SWO_Watchpoint watchpoint);

/*!
 *  Function to flush the idle buffer.
 *
 *  This function call will block until the idle buffer is empty.
 *  Should only be called from a low-priority task such as the TI-RTOS
 *  idle task.
 */
void SWO_idleFlush();

/// @cond NODOC
/*!
 *  Low-level functions to be implemented by the device specific driver
 *
 *  These functions is only to be used inside the defined macros.
 */
void        __SWO_init();
void        __SWO_open(SWO_Params *params, SWO_Status *status);
void        __SWO_prepareForIdle(uint32_t reason);
void        __SWO_returnFromIdle();
void        __SWO_close();
void        __SWO_idleFlush();

void        __SWO_printf(uint8_t isDeferred, uint8_t isEventSet, uint32_t hdr, uint32_t nArgs, SWO_EventSet eventSet, ...);
void        __SWO_logBuf(uint8_t isDeferred, uint8_t isEventSet, uint32_t hdr, SWO_EventSet eventSet, uint8_t *data, size_t size);

void        __SWO_event0(uint32_t hdr, SWO_Event event);
void        __SWO_event1(uint32_t hdr, SWO_Event event, uint32_t arg0);
void        __SWO_event2(uint32_t hdr, SWO_Event event, uint32_t arg0, uint32_t arg1);
void        __SWO_event3(uint32_t hdr, SWO_Event event, uint32_t arg0, uint32_t arg1, uint32_t arg2);
void        __SWO_event4(uint32_t hdr, SWO_Event event, uint32_t arg0, uint32_t arg1, uint32_t arg2, uint32_t arg3);

SWO_EventSet __SWO_EventSet_init(uint32_t loc, SWO_Event event);
void        __SWO_EventSet_close(uint32_t loc, SWO_EventSet rec);

void        __SWO_enableWatchpoint(uint32_t string, SWO_Watchpoint watchpoint, SWO_WatchpointFunction function, uintptr_t address);
void        __SWO_disableWatchpoint(SWO_Watchpoint watchpoint);

/*!
 *  Mapping functions and macros to top level APIs.
 */
#define SWO_init()                              SWO_INIT()
#define SWO_open(params, status)                SWO_OPEN(params, status)
#define SWO_prepareForIdle(reason)              SWO_PREPARE_FOR_IDLE(reason)
#define SWO_returnFromIdle()                    SWO_RETURN_FROM_IDLE()
#define SWO_close()                             SWO_CLOSE()
#define SWO_idleFlush()                         SWO_IDLE_FLUSH()

#define SWO_printf(logModule, logLevel, format, ...)            SWO_PRINTF(logModule, logLevel, FALSE, FALSE, format, 0, __VA_ARGS__)
#define SWO_printf_deferred(logModule, logLevel, format, ...)   SWO_PRINTF(logModule, logLevel, TRUE, FALSE, format, 0, __VA_ARGS__)

#define SWO_logBuf(logModule, logLevel, ...)                    SWO_LOGBUF(logModule, logLevel, FALSE, FALSE, 0, __VA_ARGS__)
#define SWO_logBuf_deferred(logModule, logLevel, ...)           SWO_LOGBUF(logModule, logLevel, TRUE, FALSE, 0, __VA_ARGS__)

#define SWO_event(logModule, logLevel, ...)                     SWO_EVENT(logModule, logLevel, __VA_ARGS__)

#define SWO_EventSet_init(...)                                  SWO_EVENT_SET_INIT(__VA_ARGS__)
#define SWO_EventSet_printf(logModule, logLevel, eventSet, format, ...)           SWO_PRINTF(logModule, logLevel, FALSE, TRUE, format, eventSet, __VA_ARGS__)
#define SWO_EventSet_printf_deferred(logModule, logLevel, eventSet, format, ...)  SWO_PRINTF(logModule, logLevel, TRUE, TRUE, format, eventSet, __VA_ARGS__)
#define SWO_EventSet_logBuf(logModule, logLevel, ...)           SWO_LOGBUF(logModule, logLevel, FALSE, TRUE, __VA_ARGS__)
#define SWO_EventSet_logBuf_deferred(logModule, logLevel, ...)  SWO_LOGBUF(logModule, logLevel, TRUE, TRUE, __VA_ARGS__)
#define SWO_EventSet_close(...)                                 SWO_EVENT_SET_CLOSE(SWO_LogLevel_INFO, __VA_ARGS__)

#define SWO_enableWatchpoint(...)                               SWO_ENABLE_WATCHPOINT(SWO_LogLevel_INFO, __VA_ARGS__)
#define SWO_disableWatchpoint                                   __SWO_disableWatchpoint
/// @endcond //NODOC

#ifdef __cplusplus
}
#endif

#endif /* ti_drivers_SWO__include */
