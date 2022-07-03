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

from pathlib import Path

class TaskRunScript(eik.StampTask):
    srcs = eik.TaskListParameter()
    unit = eik.WhateverParameter(significant=False)
    fun = lg.Parameter()
    workdir = lg.Parameter()

    def getCode(self):
        return getattr(self.unit.__class__, self.fun)

    def requires(self):
        return self.srcs

    def task(self):
        Path(self.workdir).mkdir(parents=True, exist_ok=True)
        with self.chdir(self.workdir):
            getattr(self.unit.__class__, self.fun)(self.unit)

class TaskRunPackageScript(eik.Task):
    srcs = eik.TaskListParameter()
    unit = eik.WhateverParameter(significant=False)
    fun = lg.Parameter()
    out = lg.Parameter()

    checkOutputHash = False

    def getCode(self):
        return getattr(self.unit.__class__, self.fun)

    def requires(self):
        return self.srcs

    def generates(self):
        return eik.Target(self, self.out)

    def task(self):
        with self.output().pathWrite() as fw:
            Path(fw).mkdir(parents=True, exist_ok=True)
            with self.chdir(fw):
                getattr(self.unit.__class__, self.fun)(self.unit, fw)
