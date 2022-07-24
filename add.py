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

import sys
from pathlib import Path

from plumbum import cmd
import Eikthyr as eik
import Ixal


if __name__ == '__main__':
    if len(sys.argv) < 3:
        Ixal.logger.error("Usage: add db pkg [pkg...]")
        sys.exit(1)
    fileDB = sys.argv[1]
    if not fileDB.endswith('.db'):
        Ixal.logger.error("Expected to get a db with filename *.db")
        sys.exit(1)
    fileDB2 = '{}.files'.format(fileDB.removesuffix('.db'))

    tDB = eik.InputTask(fileDB2)

    tDir = Ixal.TaskExtractDB(tDB, Path(Ixal.UnitConfig().pathBuild) / '.db')

    aTaskAdd = []
    for filePkg in sys.argv[2:]:
        with cmd.bsdtar.popen(('xOqf', filePkg, '--zstd', '.PKGINFO'), encoding='utf-8') as p:
            unitPkg = Ixal.Unit().loadPKGINFO(p.stdout)
        tDesc = Ixal.TaskMakeRepoDesc(eik.InputTask(filePkg), tDir, unitPkg)
        tFileList = Ixal.TaskMakeRepoFileList(eik.InputTask(filePkg), tDir, unitPkg)
        aTaskAdd += (tDesc, tFileList)
    
    tClean = Ixal.TaskCleanupRepo(tDir, '{}.cleanup'.format(fileDB), prev=aTaskAdd)
    tPack = Ixal.TaskPackDB(tDir, '{}.new'.format(fileDB), prev=(tClean,), dbonly=True)
    tPack2 = Ixal.TaskPackDB(tDir, '{}.new'.format(fileDB2), prev=(tClean,))
    eik.run((tPack, tPack2))
