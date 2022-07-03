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

class TaskStrip(eik.StampTask):
    src = eik.TaskParameter()
    enabled = lg.BoolParameter(True)

    checkInputHash = True  # we DO actually care about the upstream status

    def requires(self):
        return self.src

    def task(self):
        for f in Path(self.src.output().path).glob('**/*'):
            if f.is_dir(): continue
            if f.stat().st_mode & 0o0100 or re.match('.*\.(a|so|dll|lib)(\..*)?$', f.name):
                try:
                    self.ex(self.cmd.strip['-pD', '-S', str(f)])
                except:
                    continue
