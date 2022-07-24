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

from .download import TaskDownload
from .extract import TaskExtractTar, TaskExtract7z, TaskExtract7zOptional
from .build import TaskRunScript, TaskRunPackageScript
from .pack import TaskPackageInfo, TaskPackageMTree, TaskPackageTar
from .tidy import TaskStrip, TaskPurge, TaskCompressMan
from .cmd import MixinBuildUtilities
from .task import pickTask
from .logging import logger

import Eikthyr as eik
import luigi as lg
from plumbum import FG

import re
import inspect
from copy import deepcopy
from pathlib import Path

class UnitConfig(lg.Config):
    pathBuild = eik.PathParameter('.build')
    pathPrefix = eik.PathParameter('/opt')
    pathOutput = eik.PathParameter('.pkg')
    packager = eik.Parameter('Unknown')

class Unit(MixinBuildUtilities):
    name = ''
    src = ()
    lsrc = ()
    epoch = 0
    ver = '1.0'
    desc = ''
    rel = '1'
    arch = 'any'
    url = ''
    packager = UnitConfig().packager
    replaces = ()
    groups = ()
    depends = ()

    mTaskDownload = [
            ('^(http|https|ftp)://.*', TaskDownload),
            ]
    mTaskExtract = [
            ('.*\.tar(\.[^.]+)?$', TaskExtractTar),
            ('.*\.(7z|zip)$', TaskExtract7z),
            ('.*\.exe$', TaskExtract7zOptional),
            ]
    aTaskPostProcess = [TaskPurge, TaskStrip, TaskCompressMan]

    logger = logger

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
        self.pathPrefixRel = self.pathPrefix.relative_to('/')

    def getFullVersion(self, filename=True):
        if self.epoch == 0:
            return '{}-{}'.format(self.ver, self.rel)
        else:
            if filename:
                return '{}^{}-{}'.format(self.epoch, self.ver, self.rel)
            else:
                return '{}:{}-{}'.format(self.epoch, self.ver, self.rel)

    def loadPKGINFO(self, fp):
        self.replaces = []
        self.groups = []
        self.depends = []
        for line in iter(fp):
            key, val = line.strip().split(' = ', 1)
            if key == 'pkgname':
                self.name = val
            elif key == 'pkgbase':
                self.base = val
            elif key == 'pkgver':
                self.fullver = val
            elif key == 'pkgdesc':
                self.desc = val
            elif key == 'url':
                self.url = val
            elif key == 'packager':
                self.packager = val
            elif key == 'arch':
                self.arch = val
            elif key == 'size':
                self.size = int(val)
            elif key == 'builddate':
                self.builddate = int(val)
            elif key == 'replaces':
                self.replaces.append(val)
            elif key == 'group':
                self.groups.append(val)
            elif key == 'depend':
                self.depends.append(val)
        return self

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
            tDl = pickTask(self.mTaskDownload, f)(f, self.pathCache)
            clsExtract = pickTask(self.mTaskExtract, tDl.output().path)
            if clsExtract == None:
                aTaskSource.append(tDl)
                self.src.append(tDl.output().path)
            else:
                tEx = clsExtract(tDl, self.pathBuild / '{:d}'.format(i))
                aTaskSource.append(tEx)
                self.src.append(tEx.output().path)
        for (i,f) in enumerate(lfiles):
            fThis = Path(inspect.getfile(self.__class__)).parent / f
            clsExtract = pickTask(self.mTaskExtract, fThis)
            if clsExtract == None:
                aTaskSource.append(eik.InputTask(fThis))
                self.lsrc.append(fThis)
            else:
                tEx = clsExtract(eik.InputTask(fThis), self.pathBuild / 'L{:d}'.format(i))
                aTaskSource.append(tEx)
                self.lsrc.append(tEx.output().path)

        tPre = TaskRunScript(aTaskSource, self, 'prepare', pathStamp=self.pathBuild)
        tBuild = TaskRunScript((tPre,), self, 'build', pathStamp=self.pathBuild)

        aTaskFinal = []
        aNames = self.name
        if isinstance(aNames, str): # Single package mode
            aNames = (aNames,)
        for (i,name) in enumerate(aNames):
            unitThis = deepcopy(self)
            unitThis.name = name
            pathPkg = Path(UnitConfig().pathBuild).resolve() / 'pkg-{}-{}'.format(name, self.fullver)
            if len(aNames) == 1:
                tPkg = TaskRunPackageScript(tBuild, unitThis, 'package', pathPkg)
            else:
                tPkg = TaskRunPackageScript(tBuild, unitThis, 'package{:d}'.format(i), pathPkg)

            # Cleanup/Tidying installed package
            aTaskPost = []
            taskPostPrev = tPkg
            for cls in self.aTaskPostProcess:
                taskThis = cls(tPkg, taskPostPrev, pathStamp=self.pathBuild)
                aTaskPost.append(taskThis)
                taskPostPrev = taskThis

            # Final touch and tarring things up
            tInfo = TaskPackageInfo(tPkg, aTaskPost, unitThis)
            tMTree = TaskPackageMTree(tInfo)
            tPack = TaskPackageTar(tMTree, self.pathOutput / '{}-{}-{}.pkg.tar.zst'.format(name, self.fullver, self.arch))
            aTaskFinal.append(tPack)

        eik.run(aTaskFinal)

    def prepare(self):
        pass

    def build(self):
        pass

    def package(self):
        pass

    # Expected to get a plumbum object
    def ex(self, chain):
        self.logger.info("RUN: {}".format(chain))
        chain & FG
