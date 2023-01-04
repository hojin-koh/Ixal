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

import requests
from lastversion import has_update

from .ver import vercmp

def isLatest(spec, ver):
    src, repo = spec.split(':', 1)
    if src == 'arch':
        res = requests.get('https://archlinux.org/packages/{}'.format(repo))
        html = res.content.decode('utf-8')
        latest = re.search(R'<h2>[^< ]+ ([^<-]+)-[^<]*</h2>', html)[1]
    elif src == 'alpine':
        res = requests.get('https://pkgs.alpinelinux.org/package/edge/{}'.format(repo))
        html = res.content.decode('utf-8')
        latest = re.search(R'Flag this package out of date[^>]+>([^<-]+)-[^<]*</a>', html)[1]
    elif src == 'portapps':
        res = requests.get('https://portableapps.com/apps/{}'.format(repo))
        html = res.content.decode('utf-8')
        latest = re.search(R'<p class=[^>]+>Version ([^ ]+) ', html)[1]
    else:
        return has_update(repo=repo, at=src, current_version=ver)

    if vercmp(ver, latest) == -1:
        return latest
    else:
        return None
