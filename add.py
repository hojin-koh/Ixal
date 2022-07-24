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

import sys
from hashlib import md5, sha256
from pathlib import Path

from plumbum import cmd
import Eikthyr as eik
import Ixal

class TaskCreateDB(eik.Task):
    out = eik.PathParameter()

    def generates(self):
        return eik.Target(self, self.out)

    def task(self):
        with self.output().pathWrite() as fw:
            with open('{}.tar'.format(fw), 'wb'):
                pass
            self.ex(eik.cmd.zstd['--rm', '{}.tar'.format(fw), '-fo', fw])

class TaskExtractDB(eik.Task):
    src = eik.TaskParameter() # Presumbly this is the db file
    out = eik.PathParameter()

    def requires(self):
        return self.src

    def generates(self):
        return eik.Target(self, self.out)

    def task(self):
        with self.output().pathWrite() as fw:
            Path(fw).mkdir(parents=True, exist_ok=True)
            self.ex(eik.cmd.bsdtar['xf', self.input().path, '--zstd', '-C', fw])

class TaskMakeDesc(eik.Task):
    src = eik.TaskParameter() # Presumbly this is the package file
    unit = eik.WhateverParameter(significant=False)
    outPath = eik.PathParameter()

    def requires(self):
        return self.src

    def generates(self):
        return eik.Target(self, self.outPath / '{}-{}'.format(self.unit.name, self.unit.fullver) / 'desc')

    def task(self):
        pathPkg = Path(self.input().path)
        with self.output().fpWrite() as fpw:
            fpw.write('%FILENAME%\n{}\n\n'.format(pathPkg.name))
            fpw.write('%NAME%\n{}\n\n'.format(self.unit.name))
            fpw.write('%BASE%\n{}\n\n'.format(self.unit.base))
            fpw.write('%VERSION%\n{}\n\n'.format(self.unit.fullver))
            fpw.write('%DESC%\n{}\n\n'.format(self.unit.desc))
            if len(self.unit.groups) > 0:
                fpw.write('%GROUPS%\n{}\n\n'.format('\n'.join(self.unit.groups)))
            fpw.write('%CSIZE%\n{}\n\n'.format(pathPkg.stat().st_size))
            fpw.write('%ISIZE%\n{}\n\n'.format(self.unit.size))

            fpw.write('%MD5SUM%\n{}\n\n'.format(md5(pathPkg.read_bytes()).hexdigest()))
            fpw.write('%SHA256SUM%\n{}\n\n'.format(sha256(pathPkg.read_bytes()).hexdigest()))

            if self.unit.url:
                fpw.write('%URL%\n{}\n\n'.format(self.unit.url))
            fpw.write('%ARCH%\n{}\n\n'.format(self.unit.arch))
            fpw.write('%BUILDDATE%\n{}\n\n'.format(self.unit.builddate))
            fpw.write('%PACKAGER%\n{}\n\n'.format(self.unit.packager))

            if len(self.unit.replaces) > 0:
                fpw.write('%REPLACES%\n{}\n\n'.format('\n'.join(self.unit.replaces)))
            if len(self.unit.depends) > 0:
                fpw.write('%DEPENDS%\n{}\n\n'.format('\n'.join(self.unit.depends)))

class TaskMakeFileList(eik.Task):
    src = eik.TaskParameter() # Presumbly this is the package file
    unit = eik.WhateverParameter(significant=False)
    outPath = eik.PathParameter()

    def requires(self):
        return self.src

    def generates(self):
        return eik.Target(self, self.outPath / '{}-{}'.format(self.unit.name, self.unit.fullver) / 'files')

    def task(self):
        with self.output().fpWrite() as fpw:
            fpw.write('%FILES%\n')
            with eik.withEnv(LANG='C', LC_ALL='C'):
                with cmd.bsdtar.popen(('tf', self.input().path, '--exclude=^.*'), encoding='utf-8') as p:
                    fpw.write(p.stdout.read())

if __name__ == '__main__':
    if len(sys.argv) < 3:
        Ixal.logger.error("Usage: add db pkg [pkg...]")
        sys.exit(1)
    fileDB = sys.argv[1]
    if not fileDB.endswith('.db'):
        Ixal.logger.error("Expected to get a db with filename *.db")
        sys.exit(1)
    fileDB2 = '{}.files'.format(fileDB.removesuffix('.db'))

    if Path(fileDB).exists():
        tDB = eik.InputTask(fileDB)
    else:
        tDB = TaskCreateDB(fileDB)

    if Path(fileDB2).exists():
        tDB2 = eik.InputTask(fileDB2)
    else:
        tDB2 = TaskCreateDB(fileDB2)

    tDir = TaskExtractDB(tDB, Path(Ixal.UnitConfig().pathBuild) / '.db')
    tDir2 = TaskExtractDB(tDB2, Path(Ixal.UnitConfig().pathBuild) / '.files')

    for filePkg in sys.argv[2:]:
        with cmd.bsdtar.popen(('xOqf', filePkg, '--zstd', '.PKGINFO'), encoding='utf-8') as p:
            unitPkg = Ixal.Unit().loadPKGINFO(p.stdout)
        tDesc = TaskMakeDesc(eik.InputTask(filePkg), unitPkg, tDir.output().path)
        tDesc2 = TaskMakeDesc(eik.InputTask(filePkg), unitPkg, tDir2.output().path)
        tFileList = TaskMakeFileList(eik.InputTask(filePkg), unitPkg, tDir2.output().path)
        eik.run((tFileList, tDesc, tDesc2))
    
