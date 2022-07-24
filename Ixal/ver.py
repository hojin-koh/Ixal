# -*- coding: utf-8 -*-
# Copyright 2021-2022, Hojin Koh
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import rpm_vercmp

def getVersionString(ver, rel, epoch=0, filename=True):
    if epoch == 0:
        return '{}-{}'.format(ver, rel)
    else:
        if filename:
            return '{}^{}-{}'.format(epoch, ver, rel)
        else:
            return '{}:{}-{}'.format(epoch, ver, rel)

# Returns (ver, rel, epoch) tuple, epoch will be string '0' if not present, rel will be empty string if not present
def parseVersionString(src):
    epoch = '0'
    if ':' in src:
        epoch = src[0:src.find(':')]
        src = src.removeprefix('{}:'.format(epoch))
    elif '^' in src:
        epoch = src[0:src.find('^')]
        src = src.removeprefix('{}^'.format(epoch))

    rel = ''
    if '-' in src:
        rel = src[src.rfind('-')+1:]
        src = src.removesuffix('-{}'.format(rel))

    return (src, rel, epoch)

# Return 0 if equal, 1 if ver1 is newer, -1 if ver2 is newer
def vercmp(src1, src2):
    if src1 == '' or src1 == None:
        if src2 == '' or src2 == None:
            return 0
        return -1
    if src2 == '' or src2 == None:
        return 1
    if src1 == src2:
        return 0

    ver1, rel1, epoch1 = parseVersionString(src1)
    ver2, rel2, epoch2 = parseVersionString(src2)

    ret = rpm_vercmp.vercmp(epoch1, epoch2)
    if ret == 0:
        ret = rpm_vercmp.vercmp(ver1, ver2)
    if ret == 0 and rel1 != '' and rel2 != '':
        ret = rpm_vercmp.vercmp(rel1, rel2)

    return ret
