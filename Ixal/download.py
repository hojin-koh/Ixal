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
from pathlib import Path
from urllib.parse import urlparse

import Eikthyr as eik
import luigi as lg
from plumbum import local


class TaskDownload(eik.Task):
    url = eik.Parameter()
    pathCache = eik.PathParameter(significant=False)
    cmdcurl = eik.ListParameter(significant=False, default=('curl', '-qfLC', '-', '--ftp-pasv', '--retry', '5', '--retry-delay', '5', '-o', '{1}', '{0}'))
    filename = eik.Parameter('', significant=False)

    def parseFileName(self): # This is purely heuristic...
        url = urlparse(self.url)
        if re.search(R'\.[^.]{2,5}$', url.query):
            p = Path(url.query.rpartition('=')[-1])
        else:
            p = Path(url.path)
        # Github archive special heuristic
        if url.netloc == 'github.com' and '/archive/' in url.path:
            p = Path('{}-{}'.format(p.parts[p.parts.index('archive')-1], p.name))
        # Github release special heuristic
        if url.netloc == 'github.com' and '/releases/' in url.path:
            p = Path('{}-{}-{}'.format(p.parts[p.parts.index('releases')-1], p.parts[-2], p.name))
        # Sourceforge special heuristic
        if p.name == 'download':
            p = p.parent
        return p.name

    def generates(self):
        if self.filename == '':
            return eik.Target(self, Path(self.pathCache) / self.parseFileName())
        else:
            return eik.Target(self, Path(self.pathCache) / self.filename)

    def task(self):
        with self.output().pathWrite() as fw:
            self.ex(eik.cmdfmt(self.cmdcurl, self.url, fw))
