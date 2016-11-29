#
# Copyright (c) 2016 Mirantis Inc.
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from collections import OrderedDict
import os

from oslo_concurrency import processutils

CFG_PATH = "/etc/network/interfaces.d/"

INT_BRIDGE = 'br-int'


class ConfFile(object):

    def __init__(self, int_name):
        self.int_name = int_name
        self.path = self._get_int_cfg_file_name(int_name)
        self.data = OrderedDict()

    def _get_int_cfg_file_name(self, int_name):
        return CFG_PATH+"%s.intf" % int_name

    def read(self):
        if not os.path.isfile(self.path):
            return

        with open(self.path, 'r') as f:
            for line in f:
                words = line.split()
                if len(words) > 0:
                    self.data[words[0]] = words[1:]

    def write(self):
        content = []
        for opt, val in self.data.items():
            content.append(opt)
            content.append(' ')
            content.append(' '.join(val))
            content.append('\n')

        with open(self.path, 'w') as f:
            f.write(''.join(content))

    def ensure_opt_contain_value(self, option, value):
        cur_values = self.data.get(option) or []
        if value not in cur_values:
            new_values = cur_values
            new_values.append(value)
            self.data[option] = new_values

    def ensure_opt_has_value(self, option, value):
        cur_value = self.data.get(option) or []
        if value not in cur_value:
            self.data[option] = [value]

    def ensure_opt_not_contain_value(self, option, value):
        cur_values = self.data[option]

        if value in cur_values:
            new_values = cur_values
            new_values.remove(value)
            if len(new_values) == 0:
                self.data.pop(option)
            else:
                self.data[option] = new_values

    def __enter__(self):
        if not os.path.isfile(self.path):
            self.data['auto'] = [self.int_name]
            self.data['iface'] = [self.int_name]
        else:
            self.read()
        return self

    def __exit__(self, type, value, traceback):
        self.write()
        kwargs = {}
        cmd = ['sudo', 'ifreload', '-c']
        processutils.execute(*cmd, **kwargs)
