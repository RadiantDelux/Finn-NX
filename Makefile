TARGET := finn32
FINN_VERSION := $(shell cat VERSION)
PORT_CFLAGS += -DFINN_VERSION=\"$(FINN_VERSION)\"
PORT_NPDM_PROGRAM_ID := 0x01000000000010F1
PORT_NPDM_VERSION := $(FINN_VERSION)
ELF2NSO := python tools/elf32_to_nso.py
include runtime/runtime.mk

$(TARGET).elf: Makefile runtime/runtime.mk $(wildcard portlibs32/lib/*.a)
$(BUILD)/$(TARGET).nso: tools/elf32_to_nso.py

$(BUILD)/finn_controls.o: $(BUILD)/finn_controls_assembly.h
$(OFILES): VERSION
