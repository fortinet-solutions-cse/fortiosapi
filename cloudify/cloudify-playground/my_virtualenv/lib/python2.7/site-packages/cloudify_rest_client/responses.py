########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.


class Metadata(dict):
    """
    Metadata dict returned by various list operations.
    """

    def __init__(self, metadata):
        self.update(metadata)
        self['pagination'] = Pagination(metadata.get('pagination'))

    @property
    def pagination(self):
        """
        :return: The pagination properties
        """
        return self.get('pagination')


class Pagination(dict):
    """
    Pagination properties.
    """
    @property
    def offset(self):
        """
        :return: The list offset.
        """
        return int(self.get('offset'))

    @property
    def size(self):
        """
        :return: The returned page size.
        """
        return int(self.get('size'))

    @property
    def total(self):
        """
        :return: The total number of finds.
        """
        return int(self.get('total'))


class ListResponse(object):

    def __init__(self, items, metadata):
        self.items = items
        self.metadata = Metadata(metadata)

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, index):
        return self.items[index]

    def __len__(self):
        return len(self.items)

    def sort(self, cmp=None, key=None, reverse=False):
        return self.items.sort(cmp, key, reverse)
