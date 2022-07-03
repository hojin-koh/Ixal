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

from .download import TaskDownload
from .extract import TaskExtractTar
from .build import TaskRunScript, TaskRunPackageScript
from .pack import TaskPackageInfo, TaskPackageMTree, TaskPackageTar
from .logging import logger

import Eikthyr as eik
import luigi as lg
import plumbum.cmd as cmd
from plumbum import local

import re
import inspect
from copy import deepcopy
from pathlib import Path

class UnitConfig(lg.Config):
    pathBuild = eik.PathParameter('.build')
    pathPrefix = eik.PathParameter('/opt')
    pathOutput = eik.PathParameter('.pkg')
    packager = eik.Parameter('Unknown')

class Unit(eik.MixinCmdUtilities):
    src = ()
    lsrc = ()
    epoch = 0
    desc = ''
    rel = '1'
    arch = 'any'
    url = ''
    packager = UnitConfig().packager
    replaces = ()
    groups = ()
    depends = ()

    mTaskDownload = [
            ('^(http|https|ftp)://.*', TaskDownload)
            ]
    mTaskExtract = [
            ('.*\.tar(\.[^.]+)?$', TaskExtractTar)
            ]

    def __init__(self):
        if isinstance(self.name, str):
            self.base = self.name
        else:
            self.base = self.name[0]
        self.fullver = self.getFullVersion()
        self.pathCache = Path(UnitConfig().pathBuild).resolve() / '.cache'
        self.pathBuild = Path(UnitConfig().pathBuild).resolve() / 'src-{}-{}'.format(self.base, self.fullver)
        self.pathOutput = Path(UnitConfig().pathOutput).resolve()
        self.pathPrefix = Path(UnitConfig().pathPrefix).resolve()

    def getFullVersion(self, filename=True):
        if self.epoch == 0:
            return '{}-{}'.format(self.ver, self.rel)
        else:
            if filename:
                return '{}^{}-{}'.format(self.epoch, self.ver, self.rel)
            else:
                return '{}:{}-{}'.format(self.epoch, self.ver, self.rel)

    def pickTask(self, mapping, key):
        for (p,t) in mapping:
            if re.match(p, key):
                return t
        return None

    def make(self):
        urls = self.src
        self.src = []
        if isinstance(urls, str):
            urls = (urls,)
        lfiles = self.lsrc
        self.lsrc = []
        if isinstance(lfiles, str):
            lfiles = (lfiles,)

        aTaskSource = []
        for (i,f) in enumerate(urls):
            tDl = self.pickTask(self.mTaskDownload, f)(f, str(self.pathCache))
            classExtract = self.pickTask(self.mTaskExtract, tDl.output().path)
            if classExtract == None:
                aTaskSource.append(tDl)
                self.src.append(tDl.output().path)
            else:
                tEx = classExtract(tDl, str(self.pathBuild / '{:d}'.format(i)))
                aTaskSource.append(tEx)
                self.src.append(tEx.output().path)
        for (i,f) in enumerate(lfiles):
            fThis = str(Path(inspect.getfile(self.__class__)).parent / f)
            classExtract = self.pickTask(self.mTaskExtract, fThis)
            if classExtract == None:
                aTaskSource.append(eik.InputTask(fThis))
                self.lsrc.append(fThis)
            else:
                tEx = classExtract(eik.InputTask(fThis), str(self.pathBuild / 'L{:d}'.format(i)))
                aTaskSource.append(tEx)
                self.lsrc.append(tEx.output().path)

        tPre = TaskRunScript(aTaskSource, self, 'prepare', pathStamp=str(self.pathBuild))
        tBuild = TaskRunScript((tPre,), self, 'build', pathStamp=str(self.pathBuild))

        aTaskFinal = []
        aNames = self.name
        if isinstance(aNames, str): # Single package mode
            aNames = (aNames,)
        for (i,name) in enumerate(aNames):
            unitThis = deepcopy(self)
            unitThis.name = name
            pathPkg = Path(UnitConfig().pathBuild).resolve() / 'pkg-{}-{}'.format(name, self.fullver)
            if len(aNames) == 1:
                tPkg = TaskRunPackageScript(tBuild, unitThis, 'package', str(pathPkg))
            else:
                tPkg = TaskRunPackageScript(tBuild, unitThis, 'package{:d}'.format(i), str(pathPkg))
            tInfo = TaskPackageInfo(tPkg, unitThis)
            tMTree = TaskPackageMTree(tInfo)
            tPack = TaskPackageTar(tMTree, str(self.pathOutput / '{}-{}-{}.pkg.tar.zst'.format(name, self.fullver, self.arch)))
            aTaskFinal.append(tPack)

        eik.run(aTaskFinal)

    def prepare(self):
        pass

    def build(self):
        pass

    def package(self):
        pass

    def patch(self, filePatch, lvl=None):
        if lvl != None:
            lvlseq = (lvl,)
        else:
            lvlseq = (0,1,2,3,4,5,6)

        # First, try to reverse patch (in dry run)
        for lvl in lvlseq:
            try:
                cmd.patch('-RftNp{:d}'.format(lvl), '--dry-run', '-i', filePatch)
            except:
                continue
            logger.debug("At level {:d} already applied patch {}".format(lvl, filePatch))
            return

        for lvl in lvlseq:
            try:
                out = cmd.patch('-ltNp{:d}'.format(lvl), '-i', filePatch)
            except:
                continue
            logger.debug("At level {:d} successfully applied patch {}".format(lvl, filePatch))
            return
        raise RuntimeError("Failed to apply patch {} at any level".format(filePatch))

    def runConfigure(self, *args, prefix=None):
        if prefix == None:
            prefix = self.pathPrefix
        self.ex(self.local['./configure'][('--prefix={}'.format(prefix), *args)])

    def runMake(self, *args):
        self.ex(self.cmd.make[('-j{:d}'.format(3), *args)])

    def runMakeInstall(self, path, *args):
        self.ex(self.cmd.make[('DESTDIR={}/'.format(path), *args, 'install')])
