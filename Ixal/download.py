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

from pathlib import Path
from urllib.parse import urlparse

import Eikthyr as eik
import luigi as lg
from plumbum import local


class TaskDownload(eik.Task):
    url = eik.Parameter()
    pathCache = eik.PathParameter(significant=False)
    cmdcurl = eik.ListParameter(significant=False, default=('curl', '-qfLC', '-', '--ftp-pasv', '--retry', '5', '--retry-delay', '5', '-o', '{1}', '{0}'))

    def parseFileName(self):
        p = Path(urlparse(self.url).path)
        if p.name == 'download':
            p = p.parent
        return p.name

    def generates(self):
        return eik.Target(self, Path(self.pathCache) / self.parseFileName())

    def task(self):
        with self.output().pathWrite() as fw:
            self.ex(eik.cmdfmt(self.cmdcurl, self.url, fw))
