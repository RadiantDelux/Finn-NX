TOPDIR ?= $(CURDIR)
APP_TITLE := Jumping Finn Turbo
APP_AUTHOR := RadiantDelux
APP_VERSION := $(shell cat $(TOPDIR)/../VERSION)
TARGET := finn_nx
PORT_PAYLOAD := finn32
ICON := icon.jpg
LAUNCHER_SOURCES := source
A32 ?= $(TOPDIR)/../runtime
include $(A32)/launcher/launcher.mk
CFLAGS += -DFINN_VERSION=\"$(APP_VERSION)\"
$(OUTPUT).nacp: $(TOPDIR)/../VERSION $(TOPDIR)/Makefile

# A new ARM32 payload must rebuild the NRO even when its ARM64 code did not
# change. The generic devkitPro NRO rule otherwise misses RomFS changes.
$(OUTPUT).nro: $(TOPDIR)/romfs/$(PORT_PAYLOAD).nsp $(TOPDIR)/romfs/$(PORT_PAYLOAD).build $(TOPDIR)/icon.jpg
$(OUTPUT).nro: $(wildcard $(TOPDIR)/romfs/finn-auto-*.nca) $(TOPDIR)/romfs/finn-forwarder-license.txt
$(OUTPUT).nro: $(TOPDIR)/romfs/LICENSES.txt
