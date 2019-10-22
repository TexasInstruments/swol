SWOL_INSTALL_DIR ?= $(abspath ../../../../../../..)

include $(SWOL_INSTALL_DIR)/imports.mak

KERNEL_BUILD := $(SIMPLELINK_CC2640R2_SDK_INSTALL_DIR)/kernel/tirtos/builds/CC2640R2_LAUNCHXL/release

CC = "$(IAR_ARMCOMPILER)/bin/iccarm"
LNK = "$(IAR_ARMCOMPILER)/bin/ilinkarm"

OBJECTS = swo_test.obj SWO.obj SWOCC26XX.obj ccfg.obj main_tirtos.obj CC2640R2_LAUNCHXL.obj CC2640R2_LAUNCHXL_fxns.obj PowerCC26XX_tirtos.obj

CONFIGPKG = $(KERNEL_BUILD)/iar

NAME = swol_test

CFLAGS = -I../.. \
    "-I$(SIMPLELINK_CC2640R2_SDK_INSTALL_DIR)/source/ti/posix/iar" \
    "-I$(SWOL_INSTALL_DIR)/source" \
    "-I$(SIMPLELINK_CC2640R2_SDK_INSTALL_DIR)/source" \
    -DxSWO_PcSampling_ENABLE \
    -DSWO_LogModule_ENABLE_ALL \
    -DSWO_LogLevel_ENABLE_KERNELLOG \
    -DSWO_LogLevel_ENABLE_INFO \
    -DSWO_LogLevel_ENABLE_WARNING \
    -DSWO_LogLevel_ENABLE_ERROR \
    -DSWO_LogLevel_ENABLE_USER1 \
    -DDeviceFamily_CC26X0R2 \
    --debug \
    --silent \
    -e \
    --aeabi \
    --thumb \
    --diag_suppress=Pa050

LFLAGS = --keep \
    __vector_table \
    "$(SIMPLELINK_CC2640R2_SDK_INSTALL_DIR)/source/ti/display/lib/display.arm3" \
    "$(SIMPLELINK_CC2640R2_SDK_INSTALL_DIR)/source/ti/grlib/lib/iar/m3/grlib.a" \
    "$(SIMPLELINK_CC2640R2_SDK_INSTALL_DIR)/source/third_party/spiffs/lib/iar/m3/spiffs_cc26xx.a" \
    "$(SIMPLELINK_CC2640R2_SDK_INSTALL_DIR)/source/ti/drivers/lib/drivers_cc26x0r2.arm3" \
    "$(SIMPLELINK_CC2640R2_SDK_INSTALL_DIR)/kernel/tirtos/packages/ti/dpl/lib/dpl_cc26x0r2.arm3" \
    -f "$(KERNEL_BUILD)/iar/linker.cmd" \
    "$(SIMPLELINK_CC2640R2_SDK_INSTALL_DIR)/source/ti/devices/cc26x0r2/driverlib/bin/iar/driverlib.lib" \
    --config ../../tirtos/iar/CC2640R2_LAUNCHXL_TIRTOS.icf \
    --map "$(NAME).map" \
    --silent \
    --cpu=Cortex-M3 \
    --semihosting=iar_breakpoint

all: $(NAME).out

$(CONFIGPKG)/linker.cmd $(CONFIGPKG)/compiler.opt:
	@ $(ECHOBLANKLINE)
	@ echo $(CONFIGPKG) is not built.
	@ echo You can build it by issuing $(MAKE) in $(CONFIGPKG).
	@ $(ECHOBLANKLINE)

swo_test.obj: ../../Application/swo_test.c $(CONFIGPKG)/compiler.opt
	@ echo Building $@
	@ $(CC) $(CFLAGS) $< -f $(CONFIGPKG)/compiler.opt -o $@

SWO.obj: ../../Drivers/SWO/SWO.c $(CONFIGPKG)/compiler.opt
	@ echo Building $@
	@ $(CC) $(CFLAGS) $< -f $(CONFIGPKG)/compiler.opt -o $@

SWOCC26XX.obj: ../../Drivers/SWO/SWOCC26XX.c $(CONFIGPKG)/compiler.opt
	@ echo Building $@
	@ $(CC) $(CFLAGS) $< -f $(CONFIGPKG)/compiler.opt -o $@

ccfg.obj: ../../ccfg.c $(CONFIGPKG)/compiler.opt
	@ echo Building $@
	@ $(CC) $(CFLAGS) $< -f $(CONFIGPKG)/compiler.opt -o $@

main_tirtos.obj: ../../Startup/main_tirtos.c $(CONFIGPKG)/compiler.opt
	@ echo Building $@
	@ $(CC) $(CFLAGS) $< -f $(CONFIGPKG)/compiler.opt -o $@

CC2640R2_LAUNCHXL.obj: ../../CC2640R2_LAUNCHXL.c $(CONFIGPKG)/compiler.opt
	@ echo Building $@
	@ $(CC) $(CFLAGS) $< -f $(CONFIGPKG)/compiler.opt -o $@

CC2640R2_LAUNCHXL_fxns.obj: ../../CC2640R2_LAUNCHXL_fxns.c $(CONFIGPKG)/compiler.opt
	@ echo Building $@
	@ $(CC) $(CFLAGS) $< -f $(CONFIGPKG)/compiler.opt -o $@

PowerCC26XX_tirtos.obj: ../../PowerCC26XX_tirtos.c $(CONFIGPKG)/compiler.opt
	@ echo Building $@
	@ $(CC) $(CFLAGS) $< -f $(CONFIGPKG)/compiler.opt -o $@

$(NAME).out: $(OBJECTS) $(CONFIGPKG)/linker.cmd
	@ echo linking $@
	@ $(LNK)  $(OBJECTS) $(LFLAGS) -o $(NAME).out

clean:
	@ echo Cleaning...
	@ $(RM) $(OBJECTS) > $(DEVNULL) 2>&1
	@ $(RM) $(NAME).out > $(DEVNULL) 2>&1
	@ $(RM) $(NAME).map > $(DEVNULL) 2>&1
