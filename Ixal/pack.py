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

import os
import time
import shutil
from pathlib import Path

import Eikthyr as eik
import luigi as lg

class TaskPackageInfo(eik.NITask):
    src = eik.TaskParameter()
    unit = eik.WhateverParameter(significant=False)

    def generates(self):
        return eik.Target(self, Path(self.src.output().path) / '.PKGINFO')

    def task(self):
        tstamp = int(time.time())
        size = 0
        for f in Path(self.input().path).glob('**/*'):
            os.utime(f, (tstamp, tstamp))
            if f.is_file():
                size += f.stat().st_size

        with self.output().fpWrite() as fpw:
            fpw.write('pkgname = {}\n'.format(self.unit.name))
            fpw.write('pkgbase = {}\n'.format(self.unit.base))
            fpw.write('pkgver = {}\n'.format(self.unit.getFullVersion(filename=False)))
            fpw.write('pkgdesc = {}\n'.format(self.unit.desc))
            if self.unit.url:
                fpw.write('url = {}\n'.format(self.unit.url))
            fpw.write('builddate = {}\n'.format(tstamp))
            fpw.write('packager = {}\n'.format(self.unit.packager))
            fpw.write('size = {}\n'.format(size))
            fpw.write('arch = {}\n'.format(self.unit.arch))
            for n in self.unit.replaces:
                fpw.write('replaces = {}\n'.format(n))
            for n in self.unit.groups:
                fpw.write('group = {}\n'.format(n))
            for n in self.unit.depends:
                fpw.write('depend = {}\n'.format(n))
        os.utime(self.output().path, (tstamp, tstamp))


class TaskPackageMTree(eik.NITask):
    src = eik.TaskParameter() # Presumbly this is the .PKGINFO file

    def generates(self):
        return eik.Target(self, Path(self.src.output().path).parent / '.MTREE')

    def task(self):
        with eik.chdir(Path(self.input().path).parent):
            with eik.withEnv(LANG='C', LC_ALL='C'):
                with self.output().pathWrite() as fw:
                    basename = str(Path(fw).name)
                    self.ex(
                            eik.cmd.bsdtar['-cf', '-', '--format=mtree', '--options=!all,use-set,type,uid,gid,mode,time,size,md5,sha256,link', '--exclude', basename, '--exclude', '.MTREE', '.']
                            | eik.cmd.grep['-Ev', '^\\. ']
                            | eik.cmd.gzip['-nc', '-9'] > basename
                            )
        tstamp = Path(self.input().path).stat().st_mtime
        os.utime(self.output().path, (tstamp, tstamp))

class TaskPackageTar(eik.NITask):
    src = eik.TaskParameter() # Presumbly this is the .MTREE file
    out = eik.PathParameter()
    lvl = eik.IntParameter(19)

    def task(self):
        dirPkg = str(Path(self.input().path).parent)
        with eik.withEnv(LANG='C', LC_ALL='C'):
            with self.output().pathWrite() as fw:
                self.ex(eik.cmd.bsdtar['-cf', '{}.tar'.format(fw), '--no-xattrs', '--strip-components', '1', '-C', dirPkg, '.'])
                if self.output().path.endswith('.gz'):
                    self.ex(eik.cmd.gzip['--rsyncable', '-9', '{}.tar'.format(fw)])
                    shutil.move('{}.tar.gz'.format(fw), fw)
                else:
                    self.ex(eik.cmd.zstd['--rsyncable', '-T0', '--ultra', '--rm', '-{:d}'.format(self.lvl), '{}.tar'.format(fw), '-fo', fw])
