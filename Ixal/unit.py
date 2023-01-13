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

import re
import inspect
from copy import deepcopy
from pathlib import Path

import Eikthyr as eik
import luigi as lg
from plumbum import FG

from .build import TaskRunScript, TaskRunPackageScript
from .cmd import MixinBuildUtilities
from .download import TaskDownload, TaskDownloadYoutube
from .extract import TaskExtractTar, TaskExtract7z, TaskExtract7zOptional, TaskExtractMSI
from .logging import logger
from .pack import TaskPackageInfo, TaskPackageMTree, TaskPackageTar
from .task import pickTask
from .tidy import TaskStrip, TaskPurge, TaskPurgeLinux, TaskCompressMan
from .ver import getVersionString


class UnitConfig(lg.Config):
    pathBuild = eik.PathParameter('.build')
    pathCache = eik.PathParameter('.cache')
    pathPrefix = eik.PathParameter('/opt')
    pathOutput = eik.PathParameter('.pkg')
    packager = eik.Parameter('Unknown')
    isRepackage = eik.BoolParameter(False)

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
            ('^youtube://.*', TaskDownloadYoutube),
            ]
    mTaskExtract = [
            ('.*\.(tar(\.[^.]+)?|tgz|tbz|txz)$', TaskExtractTar),
            ('.*\.msi$', TaskExtractMSI),
            ('.*\.(7z|zip|rar)$', TaskExtract7z),
            ('.*\.exe$', TaskExtract7zOptional),
            ]

    isRepackage = UnitConfig().isRepackage
    aTaskPostProcess = []

    extension = 'pkg.tar.zst'
    environ = {}
    logger = logger

    def __init__(self):
        if not self.isRepackage:
            self.aTaskPostProcess = [TaskPurge, TaskPurgeLinux, TaskCompressMan, TaskStrip] + self.aTaskPostProcess
        else:
            self.aTaskPostProcess = [TaskPurge] + self.aTaskPostProcess
        if isinstance(self.name, str):
            self.base = self.name
        else:
            self.base = self.name[0]
        self.fullver = self.getFullVersion()
        self.pathCache = Path(UnitConfig().pathCache).resolve()
        self.pathBuild = Path(UnitConfig().pathBuild).resolve() / 'src-{}-{}'.format(self.base, self.fullver)
        self.pathOutput = Path(UnitConfig().pathOutput).resolve()
        self.pathPrefix = Path(UnitConfig().pathPrefix).resolve()
        self.pathPrefixRel = self.pathPrefix.relative_to('/')
        self.doSanityCheck()

    def doSanityCheck(self):
        if '-' in self.ver or '-' in self.rel:
            self.logger.error('No dash allowed in version number')
            raise

    def getFullVersion(self, filename=True):
        return getVersionString(self.ver, self.rel, self.epoch, filename=filename)

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
        if isinstance(urls, str) or isinstance(urls, dict):
            urls = (urls,)
        lfiles = self.lsrc
        self.lsrc = []
        if isinstance(lfiles, str) or isinstance(lfiles, dict):
            lfiles = (lfiles,)

        aTaskSource = []
        for (i,f) in enumerate(urls):
            if isinstance(f, str):
                f = {'url': f}
            tDl = pickTask(self.mTaskDownload, f['url'])(f['url'], self.pathCache, filename=f.get('filename', ''))
            if 'extract' not in f:
                f['extract'] = pickTask(self.mTaskExtract, tDl.output().path)
            if f['extract'] == None:
                aTaskSource.append(tDl)
                self.src.append(tDl.output().path)
            else:
                tEx = f['extract'](tDl, self.pathBuild / '{:d}'.format(i), canChange=True, **f.get('extractArgs', {}))
                aTaskSource.append(tEx)
                self.src.append(tEx.output().path)
        for (i,f) in enumerate(lfiles):
            if isinstance(f, str):
                f = {'url': f}
            fThis = Path(inspect.getfile(self.__class__)).parent / f['url']
            if 'extract' not in f:
                f['extract'] = pickTask(self.mTaskExtract, fThis)
            if f['extract'] == None:
                aTaskSource.append(eik.InputTask(fThis, canChange=True))
                self.lsrc.append(fThis)
            else:
                tEx = f['extract'](eik.InputTask(fThis, canChange=True), self.pathBuild / 'L{:d}'.format(i), canChange=True, **f.get('extractArgs', {}))
                aTaskSource.append(tEx)
                self.lsrc.append(tEx.output().path)

        tPre = TaskRunScript(aTaskSource, self, 'prepare', pathStamp=self.pathBuild)
        tBuild = TaskRunScript(aTaskSource, self, 'build', pathStamp=self.pathBuild, prev=(tPre,))

        aTaskFinal = []
        aNames = self.name
        if isinstance(aNames, str): # Single package mode
            aNames = (aNames,)
        for (i,name) in enumerate(aNames):
            unitThis = deepcopy(self)
            unitThis.name = name
            pathPkg = Path(UnitConfig().pathBuild).resolve() / 'pkg-{}-{}'.format(name, self.fullver)
            if len(aNames) == 1:
                tPkg = TaskRunPackageScript(aTaskSource, unitThis, 'package', pathPkg, prev=(tBuild,))
            else:
                tPkg = TaskRunPackageScript(aTaskSource, unitThis, 'package{:d}'.format(i), pathPkg, prev=(tBuild,))

            # Cleanup/Tidying installed package
            aTaskPost = []
            for cls in self.aTaskPostProcess:
                taskThis = cls(tPkg, pathStamp=self.pathBuild, prev=aTaskPost)
                aTaskPost.append(taskThis)

            # Final touch and tarring things up
            tInfo = TaskPackageInfo(tPkg, unitThis, prev=aTaskPost)
            tMTree = TaskPackageMTree(tInfo)
            tPack = TaskPackageTar(tMTree, self.pathOutput / '{}-{}-{}.{}'.format(name, self.fullver, self.arch, self.extension))
            aTaskFinal.append(tPack)

        with eik.withEnv(**self.environ):
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
