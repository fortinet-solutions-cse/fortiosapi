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

BUILD_DIR = apache_vnfd

all: $(BUILD_DIR)/%

clean:
	-@ $(RM) -rf $(BUILD_DIR)

$(BUILD_DIR)/%: 
	rm -rf $(BUILD_DIR)/*
	mkdir -p $(BUILD_DIR)
	cp -rf cloud_init icons apache_vnfd.yaml $(BUILD_DIR)
	cd $(BUILD_DIR); find * -type f   | xargs md5sum > checksums.txt; cd ..
	tar czf ../apache_vnfd.tar.gz $(BUILD_DIR)
	echo "apache_vnfd.tar.gz ready to be on-boarded" 
