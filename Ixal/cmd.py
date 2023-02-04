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
import sys
from pathlib import Path

import Eikthyr as eik
import plumbum.cmd as cmd
from plumbum import local

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

    def runConfigure(self, *args, prefix=None, configure='./configure'):
        if prefix == None:
            prefix = self.pathPrefix
        self.ex(eik.local[configure][('--prefix={}'.format(prefix), *args)])

    def runCMake(self, *args, prefix=None):
        if prefix == None:
            prefix = self.pathPrefix
        aParam = ['-DCMAKE_INSTALL_PREFIX={}'.format(prefix), '-GNinja', '-DCMAKE_BUILD_TYPE=Release', *args]
        if 'CMAKE_PREFIX_PATH' in os.environ:
            aParam.append('-DCMAKE_PREFIX_PATH={}'.format(os.environ['CMAKE_PREFIX_PATH']))
        if len(args) == 0 or (len(args) > 0 and args[-1].startswith('-')):
            aParam.append('.')
        self.ex(eik.local['cmake'][aParam])

    def runMeson(self, *args, prefix=None):
        if sys.platform == 'cygwin' and os.getenv('MSYSTEM', '') != 'MSYS':
            with eik.withEnv(MSYSTEM='MSYS'):
                return self.runMeson(*args, prefix=prefix)

        if prefix == None:
            prefix = self.pathPrefix
        aParam = ['--prefix={}'.format(prefix), '--buildtype=release', '-Doptimization=3', *args]
        if len(args) == 0 or (len(args) > 0 and args[-1].startswith('-')):
            aParam.append('..')
        self.ex(eik.local['meson'][aParam])

    def runNinja(self, *args, njobs=int(eik.getenv('IXAL_NUM_JOBS', '3'))):
        if sys.platform == 'cygwin' and os.getenv('MSYSTEM', '') != 'MSYS':
            with eik.withEnv(MSYSTEM='MSYS'):
                return self.runNinja(*args)
        self.ex(eik.cmd.ninja[('-j', '{:d}'.format(njobs), *args)])

    def runNinjaInstall(self, path, *args):
        if sys.platform == 'cygwin' and os.getenv('MSYSTEM', '') != 'MSYS':
            with eik.withEnv(MSYSTEM='MSYS'):
                return self.runNinjaInstall(path, *args)
        with eik.withEnv(DESTDIR='{}/'.format(path)):
            self.ex(eik.cmd.ninja[(*args, 'install')])

    def runMake(self, *args, njobs=int(eik.getenv('IXAL_NUM_JOBS', '3'))):
        self.ex(eik.cmd.make[('-O', '-j{:d}'.format(njobs), *args)])

    def runMakeInstall(self, path, *args):
        with eik.withEnv(DESTDIR='{}/'.format(path)):
            self.ex(eik.cmd.make[('DESTDIR={}/'.format(path), *args, 'install')])

    def replaceTree(self, patternFile, *args, patternContent='', exclude=None):
        reFile = re.compile(patternFile)
        reContent = re.compile(patternContent)
        for f in eik.Path('.').glob('**/*'):
            if not reFile.match(str(f)): continue
            if exclude and re.match(exclude, str(f)): continue
            if not f.exists(): continue
            if not f.is_file() or f.is_symlink(): continue
            stat = f.stat()
            try:
                strContent = f.read_text()
            except:
                continue
            if not reContent.search(strContent): continue
            for patternFind, strReplace in args:
                def fReplace(match):
                    rslt = match.expand(strReplace)
                    self.logger.info("RE:{}: '{}' -> '{}'".format(str(f), match[0], rslt))
                    return rslt
                strContent = re.sub(patternFind, fReplace, strContent)
            f.write_text(strContent)
            os.utime(f, (stat.st_atime, stat.st_mtime))


    def writeTemplate(self, dest, src, executable=True):
        try:
            text = Path(src).read_text('utf-8')
        except:
            text = src.strip()
        dest = Path(dest)
        dest.write_text(text
                .replace('{{PREFIX}}', str(self.pathPrefix))
                .replace('{{PKGVER}}', str(self.ver))
                ,'utf-8')
        if executable:
            dest.chmod(0o755)

    def retrieveFromSystem(self, dest, program):
        pathFull = cmd.which(program).strip()
        shutil.copy(pathFull, dest)
        if sys.platform == "cygwin":
            for f in (cmd.ldd[pathFull] | cmd.awk[R'/bin\/cyg/ {print $3}'])().split():
                shutil.copy(f, dest)
        else:
            raise "Not implemented"

    def makePythonVEnv(self, prefix, *pkgs):
        self.ex(eik.cmd.python3['-m', 'venv', 'venv'])
        pathVEnv = Path('venv').resolve()
        with eik.withEnv(VIRTUAL_ENV=str(pathVEnv)):
            for p in pkgs:
                self.ex(eik.local[str(pathVEnv/'bin'/'pip')]['install', '--require-virtualenv', p])
            self.ex(eik.local[str(pathVEnv/'bin'/'pip')]['uninstall', '-y', '--require-virtualenv', 'pip', 'setuptools'])
        for f in (pathVEnv / 'bin').iterdir():
            self.ex(eik.cmd.sed['-i', 's@{}@{}@g'.format(str(pathVEnv), str(prefix)), str(f)])
