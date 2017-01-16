# Copyright 2015 Fortinet, Inc.
#
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

BUILD_DIR = ../fortigate_vnfd

CHARMS:= fortios
CHARM_SRC_DIR := layers
CHARM_BUILD_DIR := $(BUILD_DIR)/charms

CHARM_SRC_DIRS := $(addprefix $(CHARM_SRC_DIR)/, $(CHARMS))
CHARM_BUILD_DIRS := $(addprefix $(CHARM_BUILD_DIR)/, $(CHARMS))

all: $(CHARM_BUILD_DIRS)

clean:
	-@ $(RM) -rf $(CHARM_BUILD_DIR)

$(CHARM_BUILD_DIR)/%: $(CHARM_SRC_DIR)/%
	charm-build -o $(BUILD_DIR) $<

