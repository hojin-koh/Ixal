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

import Eikthyr as eik
import luigi as lg

import os
import time
from pathlib import Path

class TaskPackageInfo(eik.Task):
    src = eik.TaskParameter()
    srcs = eik.TaskListParameter(significant=False)
    unit = eik.WhateverParameter(significant=False)

    def requires(self):
        return (self.src, self.srcs)

    def generates(self):
        return eik.Target(self, Path(self.src.output().path) / '.PKGINFO')

    def task(self):
        tstamp = int(time.time())
        size = 0
        for f in Path(self.src.output().path).glob('**/*'):
            os.utime(f, (tstamp, tstamp))
            if f.is_file():
                size += f.stat().st_size
        
        with self.output().fpWrite() as fpw:
            fpw.write('pkgname = {}\n'.format(self.unit.name))
            fpw.write('pkgbase = {}\n'.format(self.unit.base))
            fpw.write('pkgver = {}\n'.format(self.unit.getFullVersion(filename=False)))
            fpw.write('pkgdesc = {}\n'.format(self.unit.desc))
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


class TaskPackageMTree(eik.Task):
    src = eik.TaskParameter() # Presumbly this is the .PKGINFO file

    def requires(self):
        return self.src

    def generates(self):
        return eik.Target(self, Path(self.src.output().path).parent / '.MTREE')

    def task(self):
        with self.chdir(Path(self.src.output().path).parent):
            with self.local.env(LANG='C'):
                with self.output().pathWrite() as fw:
                    basename = str(Path(fw).name)
                    self.ex(
                            self.cmd.bsdtar['-cf', '-', '--format=mtree', '--options=!all,use-set,type,uid,gid,mode,time,size,md5,sha256,link', '--exclude', basename, '--exclude', '.MTREE', '.']
                            | self.cmd.grep['-Ev', '^\\. ']
                            | self.cmd.gzip['-nc', '-9'] > basename
                            )
        tstamp = Path(self.src.output().path).stat().st_mtime
        os.utime(self.output().path, (tstamp, tstamp))

class TaskPackageTar(eik.Task):
    src = eik.TaskParameter() # Presumbly this is the .MTREE file
    out = eik.PathParameter()

    def requires(self):
        return self.src

    def generates(self):
        return eik.Target(self, self.out)

    def task(self):
        dirPkg = str(Path(self.src.output().path).parent)
        with self.local.env(LANG='C'):
            with self.output().pathWrite() as fw:
                self.ex(self.cmd.bsdtar['-cf', '-', '--strip-components', '1', '-C', dirPkg, '.'] | self.cmd.zstd['-T0', '-c', '-19'] > fw)
