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

import Eikthyr as eik

class TaskRunScript(eik.StampTask):
    srcs = eik.TaskListParameter(significant=False)
    unit = eik.WhateverParameter(significant=False)
    fun = eik.Parameter()

    checkInputHash = True  # we DO actually care about the upstream status

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workdir = self.pathStamp

    def getCode(self):
        return getattr(self.unit.__class__, self.fun)

    def requires(self):
        return self.srcs

    def task(self):
        dirCD = Path(self.workdir)
        dirCD.mkdir(parents=True, exist_ok=True)
        if (dirCD / '0').is_dir():
            dirCD = dirCD / '0'
        with self.chdir(dirCD):
            getattr(self.unit.__class__, self.fun)(self.unit)

class TaskRunPackageScript(eik.Task):
    src = eik.TaskParameter(significant=False)
    unit = eik.WhateverParameter(significant=False)
    fun = eik.Parameter()
    out = eik.PathParameter()

    checkOutputHash = False

    def getCode(self):
        return getattr(self.unit.__class__, self.fun)

    def requires(self):
        return self.src

    def generates(self):
        return eik.Target(self, self.out)

    def task(self):
        with self.output().pathWrite() as fw:
            Path(fw).mkdir(parents=True, exist_ok=True)
            with self.chdir(fw):
                getattr(self.unit.__class__, self.fun)(self.unit)
