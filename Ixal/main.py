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

import Eikthyr as eik
import Ixal

def doAdd(fnameOutput, fnameInput, *aPkg):
    fnameDB = '{}.db'.format(fnameOutput.removesuffix('.files'))
    aTPkg = [eik.InputTask(f) for f in aPkg]
    eik.run(Ixal.TaskRepoAdd(fnameDB, fnameOutput, eik.InputTask(fnameInput), aTPkg))

def main():
    sys.stderr.write("sys.argv = {}\n".format(sys.argv))
    nameArgv0 = sys.argv.pop(0)
    if len(sys.argv) < 1:
        sys.stderr.write("Usage: {} add\n".format(nameArgv0))
        return 1

    # Add: add packages into a repository
    nameCmd = sys.argv.pop(0)
    if nameCmd == "add":
        if len(sys.argv) < 3:
            sys.stderr.write("Usage: {} add <output.files> <input.files> <pkg1.tar.zst> [<pkg2.tar.zst>...]\n".format(nameArgv0))
            return 3
        return doAdd(*sys.argv)
    
    else:
        sys.stderr.write("Error: Unknown command {}\n".format(nameCmd))
        return 2

#tDec = stdcmd.TaskMiniDec(withName('.build/{0}.files'), tDown, key=os.environ['REPO_KEY'])


