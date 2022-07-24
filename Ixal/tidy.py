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

import Eikthyr as eik
import luigi as lg

import os
import re
import time
from pathlib import Path


class TaskPostProcessingBase(eik.StampTask):
    src = eik.TaskParameter()
    enabled = lg.BoolParameter(True)

    checkInputHash = True  # we DO actually care about the upstream status

    def requires(self):
        return self.src

class TaskStrip(TaskPostProcessingBase):
    def task(self):
        if not self.enabled: return
        for f in Path(self.src.output().path).glob('**/*'):
            if f.is_dir(): continue
            if f.stat().st_mode & 0o0100 or re.match('.*\.(a|so|dll|lib|exe)(\.[^/]*)?$', f.name):
                try:
                    self.ex(eik.cmd.strip['-pD', '-S', str(f)])
                except:
                    continue

class TaskPurge(TaskPostProcessingBase):
    pattern = eik.ListParameter(significant=False, default=(
        '.*__pycache__/',
        '(.*/|^)share/(info|doc|gtk-doc|locale)/',
        '(.*/|^)man/man[367]/',
        '.*\.(pyc|pod)'
        '(.*/|^).packlist',
        '^\.[^/]+'
        ))
    patternExtra = eik.ListParameter(significant=False, default=())

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
        for f in Path(self.src.output().path).glob('**/*'):
            f = f.relative_to(self.src.output().path)
            if not f.exists(): continue
            if f.is_dir():
                if self.reDir.match(f):
                    shutil.rmtree(f)
            else:
                if self.reFile.match(f):
                    f.unlink()
