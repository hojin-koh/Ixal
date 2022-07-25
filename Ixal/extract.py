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
import shutil
import sys
from pathlib import Path

import Eikthyr as eik

class TaskExtractBase(eik.Task):
    src = eik.TaskParameter()
    out = eik.PathParameter()

    checkOutputHash = False

    def killRedundantDir(self, path):
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


class TaskExtractTar(TaskExtractBase):
    cmdTar = eik.ListParameter(significant=False, default=('bsdtar', 'xf', '{0}', '-C', '{1}'))

    def task(self):
        cmdReal = list(self.cmdTar)
        if self.cmdTar[0] == 'bsdtar' and not 'bsdtar' in eik.local: # Default fallback
            cmdReal[0] = 'tar'
        with self.output().pathWrite() as fw:
            Path(fw).mkdir(parents=True, exist_ok=True)
            self.ex(eik.cmdfmt(cmdReal, self.input().path, fw))
            self.killRedundantDir(fw)

class TaskExtract7z(TaskExtractBase):
    cmd7z = eik.ListParameter(significant=False, default=('7zz', '-y', 'x', '-o{1}', '{0}'))

    def doExtract(self, cmd, target):
        self.ex(eik.cmdfmt(cmd, self.input().path, target))

    def task(self):
        cmdReal = list(self.cmd7z)
        if self.cmd7z[0] == '7zz' and not '7zz' in eik.local: # Default fallback
            cmdReal[0] = '7za'
        with self.output().pathWrite() as fw:
            Path(fw).mkdir(parents=True, exist_ok=True)
            self.doExtract(cmdReal, fw)
            self.killRedundantDir(fw)
            self.normalizePerm(fw)

class TaskExtract7zOptional(TaskExtract7z):
    def doExtract(self, cmd, target):
        try:
            super().doExtract(cmd, target)
        except:
            shutil.copy(self.input().path, target)
