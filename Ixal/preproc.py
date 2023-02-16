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

import os
import re
import shutil
import time
from pathlib import Path

from .cmd import MixinBuildUtilities

import Eikthyr as eik

class TaskPreProcessingBase(eik.StampTask):
    src = eik.TaskParameter()
    prefix = eik.PathParameter()
    enabled = eik.BoolParameter(True)

    checkInputHash = True  # we DO actually care about the upstream status
    ReRunAfterDeps = True

class TaskHostPath(TaskPreProcessingBase):
    def task(self):
        if not self.enabled: return
        if not Path(self.input().path).is_dir(): return
        obj = MixinBuildUtilities()
        obj.logger = self.logger
        with eik.chdir(self.input().path):
            obj.replaceTree(
                    R'.',
                    (R'#!\s*/(usr/local/bin|usr/bin|bin)/(sh|bash|python|perl|zsh|csh|lua)(\S*)', R'#!!!!!!!!!!! \2\3'),
                    (R'#!\s*/(usr/bin|bin)/env\b', R'#!!!!!!!!!!! '),
                    (R'([^A-Za-z0-9_})/-])/usr/local', R'\1{}'.format(self.prefix)),
                    (R'([^A-Za-z0-9_})/-])/etc', R'\1{}/etc'.format(self.prefix)),
                    (R'([^A-Za-z0-9_})/-])/usr/(sbin|bin|lib64|lib|include|share)', R'\1{}/\2'.format(self.prefix)),
                    (R'#!!!!!!!!!!! ', R'#!/usr/bin/env '),
                    exclude=R'.*(\.html|\.xml|yo|\.yml|\.txt|\.md|\.rst|\.guess|\.sub|[A-Z]|\.am|\.ac|\.m4|configure|bootstrap|autogen\.sh|CMake[^/]+|meson\.build|meson_options\.txt)$|.*(debian/|CCache/|[Ee]xamples?/|[Dd]ocs?/|[Mm]an/|[Pp][Oo]/)',
                    )
