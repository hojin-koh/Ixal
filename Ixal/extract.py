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
import re
import shutil
import sys
from pathlib import Path

import Eikthyr as eik

class TaskExtractBase(eik.Task):
    src = eik.TaskParameter()
    out = eik.PathParameter()
    password = eik.Parameter('', significant=False)

    simplifiedOutputHash = True

    def killRedundantDir(self, path):
        while True:
            aContent = list(Path(path).iterdir())
            if len(aContent) > 1 or not aContent[0].is_dir():
                return
            for p in aContent[0].iterdir():
                shutil.move(p, path)
            if len(list(aContent[0].iterdir())) == 0:
                aContent[0].rmdir()

    def normalizePerm(self, path):
        if sys.platform == "cygwin": # Special perm normalization
            for f in Path(path).glob('**/*'):
                if f.is_dir():
                    f.chmod(0o755)
                    continue
                if re.match('.*\.(dll|exe|cmd|bat|com|ps|ps1|js|vbs)$', f.name):
                    f.chmod(0o755)
                else:
                    f.chmod(0o644)

    def makeWritable(self, path):
        # Make all extracted files writable
        for f in Path(path).glob('**/*'):
            mode = f.stat().st_mode
            if not mode & 0o200:
                f.chmod(mode | 0o200)


class TaskExtractTar(TaskExtractBase):
    cmdTar = eik.ListParameter(significant=False, default=('bsdtar', 'xf', '{0}', '-C', '{1}'))

    def task(self):
        cmdReal = list(self.cmdTar)
        if self.cmdTar[0] == 'bsdtar' and not 'bsdtar' in eik.local: # Default fallback
            cmdReal[0] = 'tar'
        with self.output().pathWrite() as fw:
            Path(fw).mkdir(parents=True, exist_ok=True)
            self.ex(eik.cmdfmt(cmdReal, self.input().path, fw))
            self.makeWritable(fw)
            self.killRedundantDir(fw)

class TaskExtractMSI(TaskExtractBase):
    cmdMSI = eik.ListParameter(significant=False, default=('msiexec', '/a', '{0}', '/qb', 'TARGETDIR={1}'))

    def doExtract(self, cmd, target):
        try:
            pathPackage = eik.cmd.cygpath('-aw', self.input().path).strip()
            pathTarget = eik.cmd.cygpath('-aw', target).strip()
            self.ex(eik.cmdfmt(cmd, pathPackage, pathTarget))
        except:
            shutil.copy(self.input().path, target)

    def task(self):
        with self.output().pathWrite() as fw:
            Path(fw).mkdir(parents=True, exist_ok=True)
            self.doExtract(self.cmdMSI, fw)
            self.makeWritable(fw)
            self.normalizePerm(fw)
            self.killRedundantDir(fw)

class TaskExtract7z(TaskExtractBase):
    cmd7z = eik.ListParameter(significant=False, default=('7zz', '-y', 'x', '-o{1}', '{0}'))

    def doExtract(self, cmd, target):
        self.ex(eik.cmdfmt(cmd, self.input().path, target))

    def task(self):
        cmdReal = list(self.cmd7z)
        if self.cmd7z[0] == '7zz' and not '7zz' in eik.local: # Default fallback
            if '7z' in eik.local:
                cmdReal[0] = '7z'
            elif '7za' in eik.local:
                cmdReal[0] = '7za'
        if self.password != '':
            cmdReal.insert(1, '-p{}'.format(self.password))
        with self.output().pathWrite() as fw:
            Path(fw).mkdir(parents=True, exist_ok=True)
            self.doExtract(cmdReal, fw)
            self.makeWritable(fw)
            self.normalizePerm(fw)
            self.killRedundantDir(fw)

class TaskExtract7zOptional(TaskExtract7z):
    def doExtract(self, cmd, target):
        try:
            super().doExtract(cmd, target)
            # If everything starts with a dot, we've accidently killed an working executable...
            if all(f.name.startswith('.') for f in Path(target).iterdir()) or (Path(target)/'COFF_SYMBOLS').exists():
                shutil.rmtree(target)
                Path(target).mkdir(parents=True, exist_ok=True)
                raise "Bad decompression"
        except:
            shutil.copy(self.input().path, target)
