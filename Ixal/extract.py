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
import shutil
from pathlib import Path
from plumbum import local

class TaskExtractBase(eik.Task):
    src = eik.TaskParameter()
    pathOut = eik.PathParameter()

    checkOutputHash = False

    def requires(self):
        return self.src

    def generates(self):
        return eik.Target(self, self.pathOut)

    def killRedundantDir(self, path):
        # TODO: what if there's a directory with identical name?
        aContent = list(Path(path).iterdir())
        if len(aContent) > 1 or not aContent[0].is_dir():
            return
        for p in aContent[0].iterdir():
            shutil.move(p, path)
        if len(list(aContent[0].iterdir())) == 0:
            aContent[0].rmdir()
        

class TaskExtractTar(TaskExtractBase):
    cmd = eik.ListParameter(significant=False, default=('tar', 'xf', '{0}', '-C', '{1}'))

    def task(self):
        with self.output().pathWrite() as fw:
            Path(fw).mkdir(parents=True, exist_ok=True)
            args = [s.format(self.input().path, fw) for s in self.cmd[1:]]
            self.ex(local[self.cmd[0]][args])
            self.killRedundantDir(fw)
