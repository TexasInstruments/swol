SWOL_INSTALL_DIR ?= $(abspath ../../../../../../..)

include $(SWOL_INSTALL_DIR)/imports.mak

KERNEL_BUILD := $(SIMPLELINK_CC2640R2_SDK_INSTALL_DIR)/kernel/tirtos/builds/CC2640R2_LAUNCHXL/release

CC = "$(CCS_ARMCOMPILER)/bin/armcl"
LNK = "$(CCS_ARMCOMPILER)/bin/armcl"

OBJECTS = swo_test.obj SWO.obj SWOCC26XX.obj ccfg.obj main_tirtos.obj CC2640R2_LAUNCHXL.obj CC2640R2_LAUNCHXL_fxns.obj PowerCC26XX_tirtos.obj

CONFIGPKG = $(KERNEL_BUILD)/ccs

NAME = swol_test

CFLAGS = -I../.. \
    "-I$(SIMPLELINK_CC2640R2_SDK_INSTALL_DIR)/source/ti/posix/ccs" \
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
    --silicon_version=7M3 \
    --code_state=16 \
    --little_endian \
    --display_error_number \
    --diag_warning=255 \
    --diag_wrap=off \
    --gen_func_subsections=on \
    --float_support=vfplib \
    --symdebug:dwarf \
    "-I$(CCS_ARMCOMPILER)/include"

LFLAGS = "-i$(SIMPLELINK_CC2640R2_SDK_INSTALL_DIR)/source" \
    -lti/display/lib/display.aem3 \
    -lti/grlib/lib/ccs/m3/grlib.a \
    -lthird_party/spiffs/lib/ccs/m3/spiffs_cc26xx.a \
    -lti/drivers/lib/drivers_cc26x0r2.aem3 \
    "-i$(SIMPLELINK_CC2640R2_SDK_INSTALL_DIR)/kernel/tirtos/packages" \
    -lti/dpl/lib/dpl_cc26x0r2.aem3 \
    "-l$(KERNEL_BUILD)/ccs/linker.cmd" \
    -lti/devices/cc26x0r2/driverlib/bin/ccs/driverlib.lib \
    ../../tirtos/ccs/CC2640R2_LAUNCHXL_TIRTOS.cmd \
    "-m$(NAME).map" \
    --warn_sections \
    --display_error_number \
    --diag_wrap=off \
    --rom_model \
    "-i$(CCS_ARMCOMPILER)/lib" \
    -llibc.a

all: $(NAME).out

$(CONFIGPKG)/linker.cmd $(CONFIGPKG)/compiler.opt:
	@ $(ECHOBLANKLINE)
	@ echo $(CONFIGPKG) is not built.
	@ echo You can build it by issuing $(MAKE) in $(CONFIGPKG).
	@ $(ECHOBLANKLINE)

swo_test.obj: ../../Application/swo_test.c $(CONFIGPKG)/compiler.opt
	@ echo Building $@
	@ $(CC) $(CFLAGS) $< --cmd_file=$(CONFIGPKG)/compiler.opt --output_file=$@

SWO.obj: ../../Drivers/SWO/SWO.c $(CONFIGPKG)/compiler.opt
	@ echo Building $@
	@ $(CC) $(CFLAGS) $< --cmd_file=$(CONFIGPKG)/compiler.opt --output_file=$@

SWOCC26XX.obj: ../../Drivers/SWO/SWOCC26XX.c $(CONFIGPKG)/compiler.opt
	@ echo Building $@
	@ $(CC) $(CFLAGS) $< --cmd_file=$(CONFIGPKG)/compiler.opt --output_file=$@

ccfg.obj: ../../ccfg.c $(CONFIGPKG)/compiler.opt
	@ echo Building $@
	@ $(CC) $(CFLAGS) $< --cmd_file=$(CONFIGPKG)/compiler.opt --output_file=$@

main_tirtos.obj: ../../Startup/main_tirtos.c $(CONFIGPKG)/compiler.opt
	@ echo Building $@
	@ $(CC) $(CFLAGS) $< --cmd_file=$(CONFIGPKG)/compiler.opt --output_file=$@

CC2640R2_LAUNCHXL.obj: ../../CC2640R2_LAUNCHXL.c $(CONFIGPKG)/compiler.opt
	@ echo Building $@
	@ $(CC) $(CFLAGS) $< --cmd_file=$(CONFIGPKG)/compiler.opt --output_file=$@

CC2640R2_LAUNCHXL_fxns.obj: ../../CC2640R2_LAUNCHXL_fxns.c $(CONFIGPKG)/compiler.opt
	@ echo Building $@
	@ $(CC) $(CFLAGS) $< --cmd_file=$(CONFIGPKG)/compiler.opt --output_file=$@

PowerCC26XX_tirtos.obj: ../../PowerCC26XX_tirtos.c $(CONFIGPKG)/compiler.opt
	@ echo Building $@
	@ $(CC) $(CFLAGS) $< --cmd_file=$(CONFIGPKG)/compiler.opt --output_file=$@

$(NAME).out: $(OBJECTS) $(CONFIGPKG)/linker.cmd
	@ echo linking $@
	@ $(LNK) $(CFLAGS) -z $(OBJECTS) $(LFLAGS) -o $(NAME).out

clean:
	@ echo Cleaning...
	@ $(RM) $(OBJECTS) > $(DEVNULL) 2>&1
	@ $(RM) $(NAME).out > $(DEVNULL) 2>&1
	@ $(RM) $(NAME).map > $(DEVNULL) 2>&1
