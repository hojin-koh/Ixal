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

import plumbum.cmd as cmd
from plumbum import local
import Eikthyr as eik

from .logging import logger

class MixinBuildUtilities(object):
    def patch(self, filePatch, lvl=None):
        if lvl != None:
            lvlseq = (lvl,)
        else:
            lvlseq = (0,1,2,3,4,5,6)

        # First, try to reverse patch (in dry run)
        for lvl in lvlseq:
            try:
                cmd.patch('-RftNp{:d}'.format(lvl), '--dry-run', '-i', filePatch)
            except:
                continue
            logger.debug("At level {:d} already applied patch {}".format(lvl, filePatch))
            return

        for lvl in lvlseq:
            try:
                out = cmd.patch('-ltNp{:d}'.format(lvl), '-i', filePatch)
            except:
                continue
            logger.debug("At level {:d} successfully applied patch {}".format(lvl, filePatch))
            return
        raise RuntimeError("Failed to apply patch {} at any level".format(filePatch))

    def runConfigure(self, *args, prefix=None):
        if prefix == None:
            prefix = self.pathPrefix
        self.ex(eik.local['./configure'][('--prefix={}'.format(prefix), *args)])

    def runMake(self, *args):
        self.ex(eik.cmd.make[('-j{:d}'.format(3), *args)])

    def runMakeInstall(self, path, *args):
        self.ex(eik.cmd.make[('DESTDIR={}/'.format(path), *args, 'install')])
