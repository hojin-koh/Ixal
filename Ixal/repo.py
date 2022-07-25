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

import shutil
import sys
from functools import cmp_to_key
from hashlib import md5, sha256
from pathlib import Path

import Eikthyr as eik
from plumbum import cmd

from .ver import vercmp

class TaskExtractDB(eik.Task):
    src = eik.TaskParameter() # Presumbly this is the db file
    out = eik.PathParameter()

    def task(self):
        with self.output().pathWrite() as fw:
            Path(fw).mkdir(parents=True, exist_ok=True)
            self.ex(eik.cmd.bsdtar['xf', self.input().path, '--zstd', '-C', fw])

class TaskMakeRepoDesc(eik.Task):
    src = eik.TaskParameter() # Presumbly this is the package file
    taskOut = eik.TaskParameter() # ExtractDB
    unit = eik.WhateverParameter(significant=False) # This is the unit with package information

    def requires(self):
        return (self.src, self.taskOut)

    def generates(self):
        return eik.Target(self, Path(self.taskOut.output().path) / '{}-{}'.format(self.unit.name, self.unit.fullver) / 'desc')

    def task(self):
        pathPkg = Path(self.input()[0].path)
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

class TaskMakeRepoFileList(eik.Task):
    src = eik.TaskParameter() # Presumbly this is the package file
    taskOut = eik.TaskParameter() # ExtractDB
    unit = eik.WhateverParameter(significant=False)

    def requires(self):
        return (self.src, self.taskOut)

    def generates(self):
        return eik.Target(self, Path(self.taskOut.output().path) / '{}-{}'.format(self.unit.name, self.unit.fullver) / 'files')

    def task(self):
        with self.output().fpWrite() as fpw:
            fpw.write('%FILES%\n')
            with eik.withEnv(LANG='C', LC_ALL='C'):
                with cmd.bsdtar.popen(('tf', self.input()[0].path, '--exclude=^.*'), encoding='utf-8') as p:
                    fpw.write(p.stdout.read())

class TaskCleanupRepo(eik.Task):
    src = eik.TaskParameter() # Repo directory
    out = eik.PathParameter() # A list of file to delete

    def task(self):
        hVer = {}
        hDir = {} # key="pkgname fullver"
        hFile = {} # key="pkgname fullver"
        aDelete = []
        with eik.chdir(self.input().path):
            for d in Path('.').iterdir():
                if not d.is_dir(): continue
                if not (d / 'desc').exists(): continue
                with (d / 'desc').open() as fp:
                    aInfo = [l.strip() for l in fp.readlines()]
                fname = aInfo[aInfo.index('%FILENAME%')+1]
                namePkg = aInfo[aInfo.index('%NAME%')+1]
                verPkg = aInfo[aInfo.index('%VERSION%')+1]
                if namePkg not in hVer:
                    hVer[namePkg] = []
                hVer[namePkg].append(verPkg)
                hDir['{} {}'.format(namePkg, verPkg)] = str(d)
                hFile['{} {}'.format(namePkg, verPkg)] = fname
            for (namePkg, aVer) in hVer.items():
                if len(aVer) == 1: continue
                for v in sorted(aVer, key=cmp_to_key(vercmp), reverse=True)[1:]:
                    self.logger.debug("Found outdated package: {}-{}".format(namePkg, v))
                    shutil.rmtree(hDir['{} {}'.format(namePkg, v)])
                    aDelete.append(hFile['{} {}'.format(namePkg, v)])
        with self.output().fpWrite() as fpw:
            for f in aDelete:
                fpw.write('{}\n'.format(f))

class TaskPackDB(eik.Task):
    src = eik.TaskParameter() # Presumbly this is the extracted db directory
    out = eik.PathParameter()
    dbonly = eik.BoolParameter()

    def task(self):
        with self.output().pathWrite() as fw:
            if self.dbonly:
                objTar = eik.cmd.bsdtar['-cf', '-', '--exclude', 'files', '--strip-components', '1', '-C', self.input().path, '.']
            else:
                objTar = eik.cmd.bsdtar['-cf', '-', '--strip-components', '1', '-C', self.input().path, '.']
            self.ex(objTar | eik.cmd.zstd['--rsyncable', '-cT0', '--ultra', '-22'] > fw)
