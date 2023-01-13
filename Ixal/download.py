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

# Source: https://gist.github.com/sidneys/7095afe4da4ae58694d128b1034e01e2
MAPYTEXT = {
        "5": "flv", "6": "flv",
        "17": "3gp",
        "18": "mp4", "22": "mp4",
        "34": "flv", "35": "flv",
        "36": "3gp",
        "37": "mp4", "38": "mp4",
        "43": "webm", "44": "webm", "45": "webm", "46": "webm",
        "82": "mp4", "83": "mp4", "84": "mp4", "85": "mp4",
        "92": "hls", "93": "hls", "94": "hls", "95": "hls", "96": "hls",
        "100": "webm", "101": "webm", "102": "webm",
        "132": "hls",
        "133": "mp4", "134": "mp4", "135": "mp4", "136": "mp4", "137": "mp4", "138": "mp4",
        "139": "m4a", "140": "m4a", "141": "m4a",
        "151": "hls",
        "160": "mp4",
        "167": "webm", "168": "webm", "169": "webm", "171": "webm", "218": "webm", "219": "webm",
        "242": "webm", "243": "webm", "244": "webm", "245": "webm", "246": "webm", "247": "webm",
        "248": "webm", "249": "webm", "250": "webm", "251": "webm",
        "264": "mp4", "266": "mp4",
        "271": "webm", "272": "webm", "278": "webm",
        "298": "mp4", "299": "mp4",
        "302": "webm", "303": "webm", "308": "webm", "313": "webm", "315": "webm", "330": "webm",
        "331": "webm", "332": "webm", "333": "webm", "334": "webm", "335": "webm", "336": "webm",
        "337": "webm",
        }

class TaskDownloadYoutube(TaskDownload):
    cmdytd = eik.ListParameter(significant=False, default=('yt-dlp', '-f', '{2}', '-o', '{1}', '--', '{0}'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fmt, self.vidid = self.url.removeprefix('youtube://').split(':', 1)

    def parseFileName(self): # This is purely heuristic...
        return '{}.{}'.format(self.vidid, MAPYTEXT[self.fmt])

    def task(self):
        with self.output().pathWrite() as fw:
            self.ex(eik.cmdfmt(self.cmdytd, self.vidid, fw, self.fmt))
