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
/*!*****************************************************************************
 *  @file       SWOUtils.h
 *  @brief      SWO utilities
 *
 *  This file contains helpful utility macros to ease the SWO macro magic.
 */
#include <stdint.h>

/* Helper macros used to create token and strings*/
#define __CONCAT2(x,y) x ## _ ## y
#define _CONCAT2(x,y) __CONCAT2(x,y)          // Create a pointer symbol token
#define __TOKEN2STRING(x) #x
#define _TOKEN2STRING(x) __TOKEN2STRING(x)    // Convert a token to string
#define APPEND_META_INFORMATION_TO_FORMAT(opcode, isDeferred, isEventSet, file, line, \
                                          logLevel, logModule, format, nargs)  \
                                           _TOKEN2STRING(opcode)     ":::" \
                                           _TOKEN2STRING(isDeferred) ":::" \
                                           _TOKEN2STRING(isEventSet) ":::" \
                                           _TOKEN2STRING(file)       ":::" \
                                           _TOKEN2STRING(line)       ":::" \
                                           _TOKEN2STRING(logLevel)   ":::" \
                                           _TOKEN2STRING(logModule)  ":::" \
                                           _TOKEN2STRING(format)     ":::" \
                                           _TOKEN2STRING(nargs)

/* Helper macro to get specific argument from __VA_ARGS__ */
#define FIRST_ARG(N, ...) N

/* Helper macro to count number of VA_ARGS passed in the macro (0 and 1 will both appear as 1) */
#define GET_NUMBER_OF_ARGS(...) \
         _GET_NUMBER_OF_ARGS(__VA_ARGS__,_COUNT_ARGS())
#define GET_NUMBER_OF_ARGS_MINUS_EVENT_SET(...) \
        _GET_NUMBER_OF_ARGS(__VA_ARGS__,_COUNT_ARGS_MINUS_EVENT_SET())
#define _GET_NUMBER_OF_ARGS(...) \
         _NUMBER_OF_ARGS(__VA_ARGS__)
#define _NUMBER_OF_ARGS( \
            _1, _2, _3, _4, _5, _6, _7, _8, _9,_10, \
            _11,_12,_13,_14,_15,_16,_17,_18,_19,_20, \
            _21,_22,_23,_24,_25,_26,_27,_28,_29,_30, \
            _31,_32,_33,_34,_35,_36,_37,_38,_39,_40, \
            _41,_42,_43,_44,_45,_46,_47,_48,_49,_50, \
            _51,_52,_53,_54,_55,_56,_57,_58,_59,_60, \
            _61,_62,_63,N,...) N
#define _COUNT_ARGS() \
            63,62,61,60,                   \
            59,58,57,56,55,54,53,52,51,50, \
            49,48,47,46,45,44,43,42,41,40, \
            39,38,37,36,35,34,33,32,31,30, \
            29,28,27,26,25,24,23,22,21,20, \
            19,18,17,16,15,14,13,12,11,10, \
            9,8,7,6,5,4,3,2,1,0
/* Exclude event set from the argument count by offsetting by 1 */
#define _COUNT_ARGS_MINUS_EVENT_SET() \
            62,61,60,               \
            59,58,57,56,55,54,53,52,51,50, \
            49,48,47,46,45,44,43,42,41,40, \
            39,38,37,36,35,34,33,32,31,30, \
            29,28,27,26,25,24,23,22,21,20, \
            19,18,17,16,15,14,13,12,11,10, \
            9,8,7,6,5,4,3,2,1,0,0

/* Macro to select function depending on number of arguments.
 * Support up to 5 arguments. */
#define _EVENT_GET_OVERRIDE(_1, _2, _3, _4, _5, NAME, ...)    NAME

/* Helper function to apply casting to each argumentt in VA_ARGS */
#define APPLY(macro, ...) CAT(APPLY_, GET_NUMBER_OF_ARGS(__VA_ARGS__))(macro, __VA_ARGS__)
#define PRIMITIVE_CAT(x, y) x ## y
#define CAT(x, y) PRIMITIVE_CAT(x, y)
#define CAST_UINT32(x) (uint32_t) x
/* A define is needed for each number of arguments supported, currently up to 16*/
#define APPLY_1(m, x1) m(x1)
#define APPLY_2(m, x1, x2) m(x1), m(x2)
#define APPLY_3(m, x1, x2, x3) m(x1), m(x2), m(x3)
#define APPLY_4(m, x1, x2, x3, x4) m(x1), m(x2), m(x3), m(x4)
#define APPLY_5(m, x1, x2, x3, x4, x5) m(x1), m(x2), m(x3), m(x4), m(x5)
#define APPLY_6(m, x1, x2, x3, x4, x5, x6) m(x1), m(x2), m(x3), m(x4), m(x5), m(x6)
#define APPLY_7(m, x1, x2, x3, x4, x5, x6, x7) m(x1), m(x2), m(x3), m(x4), m(x5), m(x6), m(x7)
#define APPLY_8(m, x1, x2, x3, x4, x5, x6, x7, x8) m(x1), m(x2), m(x3), m(x4), m(x5), m(x6), m(x7), m(x8)
#define APPLY_9(m, x1, x2, x3, x4, x5, x6, x7, x8, x9) m(x1), m(x2), m(x3), m(x4), m(x5), m(x6), m(x7), m(x8), m(x9)
#define APPLY_10(m, x1, x2, x3, x4, x5, x6, x7, x8, x9, x10) m(x1), m(x2), m(x3), m(x4), m(x5), m(x6), m(x7), m(x8), x(x9), m(x10)
#define APPLY_11(m, x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11) m(x1), m(x2), m(x3), m(x4), m(x5), m(x6), m(x7), m(x8), x(x9), m(x10), m(x11)
#define APPLY_12(m, x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12) m(x1), m(x2), m(x3), m(x4), m(x5), m(x6), m(x7), m(x8), x(x9), m(x10), m(x11), m(x12)
#define APPLY_13(m, x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12, x13) m(x1), m(x2), m(x3), m(x4), m(x5), m(x6), m(x7), m(x8), x(x9), m(x10), m(x11), m(x12), m(x13)
#define APPLY_14(m, x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12, x13, x14) m(x1), m(x2), m(x3), m(x4), m(x5), m(x6), m(x7), m(x8), x(x9), m(x10), m(x11), m(x12), m(x13), m(x14)
#define APPLY_15(m, x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12, x13, x14, x15) m(x1), m(x2), m(x3), m(x4), m(x5), m(x6), m(x7), m(x8), x(x9), m(x10), m(x11), m(x12), m(x13), m(x14), m(x15)
#define APPLY_16(m, x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12, x13, x14, x15, x16) m(x1), m(x2), m(x3), m(x4), m(x5), m(x6), m(x7), m(x8), x(x9), m(x10), m(x11), m(x12), m(x13), m(x14), m(X15), m(x16)
