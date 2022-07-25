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
import time
from pathlib import Path

import Eikthyr as eik
import luigi as lg

class TaskPostProcessingBase(eik.StampTask):
    src = eik.TaskParameter()
    enabled = lg.BoolParameter(True)

    checkInputHash = True  # we DO actually care about the upstream status

class TaskStrip(TaskPostProcessingBase):
    def task(self):
        if not self.enabled: return
        for f in Path(self.input().path).glob('**/*'):
            if f.is_dir(): continue
            if f.stat().st_mode & 0o0100 or re.match('.*\.(a|so|dll|lib|exe)(\.[^/]*)?$', f.name):
                try:
                    self.ex(eik.cmd.strip['-pD', '-S', str(f)])
                except:
                    continue

class TaskPurge(TaskPostProcessingBase):
    pattern = eik.ListParameter((
        '.*__pycache__/',
        '(.*/|^)share/(info|doc|gtk-doc|locale)/',
        '(.*/|^)man/man[367]/',
        '.*\.(pyc|pod)'
        '(.*/|^).packlist',
        '^\.[^/]+'
        ), significant=False)
    patternExtra = eik.ListParameter((), significant=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aPatDir = []
        aPatFile = []
        for pat in self.pattern + self.patternExtra:
            if pat.endswith('/'):
                aPatDir.append('{}$'.format(pat[:-1]))
            else:
                aPatFile.append('{}$'.format(pat))
        self.reDir = re.compile('|'.join(aPatDir))
        self.reFile = re.compile('|'.join(aPatFile))

    def task(self):
        if not self.enabled: return
        with eik.chdir(self.input().path):
            for f in Path('.').glob('**/*'):
                if not f.exists(): continue
                if f.is_dir():
                    if self.reDir.match(str(f)):
                        self.logger.debug("Purged folder: {}".format(str(f)))
                        shutil.rmtree(f)
                else:
                    if self.reFile.match(str(f)):
                        self.logger.debug("Purged file: {}".format(str(f)))
                        f.unlink()

class TaskCompressMan(TaskPostProcessingBase):
    pattern = eik.ListParameter((
        '(.*/|^)share/man/man[124589]/',
        ), significant=False)
    patternExtra = eik.ListParameter((), significant=False)

    patternMan = eik.Parameter('^.*\.[1-9]$', significant=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aPatDir = []
        for pat in self.pattern + self.patternExtra:
            if pat.endswith('/'):
                aPatDir.append('{}$'.format(pat[:-1]))
        self.reDir = re.compile('|'.join(aPatDir))
        self.reMan = re.compile(self.patternMan)

    def task(self):
        if not self.enabled: return
        with eik.chdir(self.input().path):
            for d in Path('.').glob('**/*'):
                if not d.exists() and not d.is_dir(): continue
                if not self.reDir.match(str(d)): continue
                for f in d.iterdir():
                    if f.is_dir() or not self.reMan.match(f.name): continue
                    self.ex(eik.cmd.gzip['-n9', str(f)])
