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

import filecmp
import os
import re
import shutil
import time
from pathlib import Path

import Eikthyr as eik

class TaskPostProcessingBase(eik.StampTask):
    src = eik.TaskParameter()
    prefix = eik.PathParameter()
    enabled = eik.BoolParameter(True)

    checkInputHash = True  # we DO actually care about the upstream status
    ReRunAfterDeps = True

class TaskCanonicalize(TaskPostProcessingBase):
    def task(self):
        if not self.enabled: return
        pathPrefix = Path(self.input().path) / Path(self.prefix).relative_to('/')
        if not pathPrefix.is_dir(): return # Nothing to see here
        with eik.chdir(pathPrefix):
            # Put everything in lib64 into lib
            if Path('lib64').is_dir():
                self.logger.info('Canonicalizing lib64')
                shutil.copytree('lib64', 'lib', symlinks=True, dirs_exist_ok=True)
                shutil.rmtree('lib64')
            # Replacing identical *.so, *.so.\d+, *.so.\d+.\d+.\d+ into symlinks
            if Path('lib').is_dir():
                for f in Path('lib').glob('*.so.*'):
                    m = re.match(R'(.*\.so)\.([0-9]+)\.([0-9]+)(\.([0-9]+))?$', str(f))
                    if not m: continue
                    self.logger.info('Soft-linking {}'.format(f))
                    p1 = Path('{}.{}'.format(m[1], m[2]))
                    if not p1.exists() or (p1.exists() and filecmp.cmp(f, p1, shallow=False)):
                        p1.unlink(missing_ok=True)
                        p1.symlink_to(f.name)
                    p2 = Path('{}'.format(m[1]))
                    if not p2.exists() or (p2.exists() and filecmp.cmp(p1, p2, shallow=False)):
                        p2.unlink(missing_ok=True)
                        p2.symlink_to(p1.name)


class TaskStrip(TaskPostProcessingBase):
    def task(self):
        if not self.enabled: return
        for f in Path(self.input().path).glob('**/*'):
            if f.is_dir(): continue
            if f.stat().st_mode & 0o0100 or re.match('.*\.(a|so|dll|lib|exe)(\.[^/]*)?$', f.name):
                try:
                    eik.cmd.strip('-pD', '-S', str(f))
                except:
                    continue

class TaskPurge(TaskPostProcessingBase):
    pattern = eik.ListParameter((
        '.*__pycache__/',
        '.*\.(pyc|pod)',
        '(.*/|^).packlist',
        '^\.[^/]+',
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
                    if len(self.reDir.pattern) > 0 and self.reDir.match(str(f)):
                        self.logger.debug("Purged folder: {}".format(str(f)))
                        shutil.rmtree(f)
                else:
                    if f.name == '.INSTALL': continue # Try not to purge out the installation script
                    if len(self.reFile.pattern) > 0 and self.reFile.match(str(f)):
                        self.logger.debug("Purged file: {}".format(str(f)))
                        f.unlink()

class TaskPurgeLinux(TaskPurge):
    pattern = eik.ListParameter((
        '(.*/|^)share/(info|doc|gtk-doc|locale)/',
        '(.*/|^)man/man[367]/',
        ), significant=False)

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
                    if f.is_symlink():
                        tgt = f.readlink()
                        f.unlink()
                        Path('{}.gz'.format(str(f))).symlink_to('{}.gz'.format(str(tgt)))
                        continue
                    self.ex(eik.cmd.gzip['-n9', str(f)])
