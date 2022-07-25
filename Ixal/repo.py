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

from .unit import UnitConfig, Unit
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

    def requires(self):
        return (self.src, self.taskOut)

    def generates(self):
        pathOut = Path(self.taskOut.output().path) / self.src.output().path.rpartition('-')[0]
        return (eik.Target(self, pathOut / 'desc'), eik.Target(self, pathOut / 'files'))

    def task(self):
        pathPkg = Path(self.input()[0].path)
        with eik.cmd.bsdtar.popen(('xOqf', str(pathPkg), '--zstd', '.PKGINFO'), encoding='utf-8') as p:
            unitPkg = Unit().loadPKGINFO(p.stdout)
        with self.output()[0].fpWrite() as fpw:
            fpw.write('%FILENAME%\n{}\n\n'.format(pathPkg.name))
            fpw.write('%NAME%\n{}\n\n'.format(unitPkg.name))
            fpw.write('%BASE%\n{}\n\n'.format(unitPkg.base))
            fpw.write('%VERSION%\n{}\n\n'.format(unitPkg.fullver))
            fpw.write('%DESC%\n{}\n\n'.format(unitPkg.desc))
            if len(unitPkg.groups) > 0:
                fpw.write('%GROUPS%\n{}\n\n'.format('\n'.join(unitPkg.groups)))
            fpw.write('%CSIZE%\n{}\n\n'.format(pathPkg.stat().st_size))
            fpw.write('%ISIZE%\n{}\n\n'.format(unitPkg.size))

            fpw.write('%MD5SUM%\n{}\n\n'.format(md5(pathPkg.read_bytes()).hexdigest()))
            fpw.write('%SHA256SUM%\n{}\n\n'.format(sha256(pathPkg.read_bytes()).hexdigest()))

            if unitPkg.url:
                fpw.write('%URL%\n{}\n\n'.format(unitPkg.url))
            fpw.write('%ARCH%\n{}\n\n'.format(unitPkg.arch))
            fpw.write('%BUILDDATE%\n{}\n\n'.format(unitPkg.builddate))
            fpw.write('%PACKAGER%\n{}\n\n'.format(unitPkg.packager))

            if len(unitPkg.replaces) > 0:
                fpw.write('%REPLACES%\n{}\n\n'.format('\n'.join(unitPkg.replaces)))
            if len(unitPkg.depends) > 0:
                fpw.write('%DEPENDS%\n{}\n\n'.format('\n'.join(unitPkg.depends)))
        with self.output()[1].fpWrite() as fpw:
            fpw.write('%FILES%\n')
            with eik.withEnv(LANG='C', LC_ALL='C'):
                with eik.cmd.bsdtar.popen(('tf', str(pathPkg), '--exclude=^.*'), encoding='utf-8') as p:
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


class TaskRepoAdd(eik.Task):
    src = eik.TaskParameter() # The original "files" file
    out = eik.PathParameter() # The output "db" file
    out2 = eik.PathParameter() # The output "files" file
    pkg = eik.TaskListParameter() # All packages

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tDir = TaskExtractDB(self.src, Path(UnitConfig().pathBuild) / '.db')
        aTaskDesc = [TaskMakeRepoDesc(p, tDir) for p in self.pkg]

        tClean = TaskCleanupRepo(tDir, '{}.cleanup'.format(self.out), prev=aTaskDesc)
        self.tPack = TaskPackDB(tDir, self.out, prev=(tClean,), dbonly=True)
        self.tPack2 = TaskPackDB(tDir, self.out2, prev=(tClean,))

    def requires(self):
        return (self.src, self.pkg)

    def generates(self):
        return (self.tPack.output(), self.tPack2.output())

    def task(self):
        yield self.tPack
        yield self.tPack2
