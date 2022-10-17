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

import importlib.util
import sys
from inspect import isclass
from pathlib import Path

import Eikthyr as eik
import Ixal
from colorama import Fore, Style

from .latest import isLatest

def doAdd(fnameOutput, fnameInput, *aPkg):
    fnameDB = '{}.db'.format(fnameOutput.removesuffix('.files'))
    aTPkg = [eik.InputTask(f) for f in aPkg]
    eik.run(Ixal.TaskRepoAdd(fnameDB, fnameOutput, eik.InputTask(fnameInput), aTPkg))

def doLatest(directory):
    if Path(directory).is_dir():
        itr = Path(directory).glob('**/*.py')
    else:
        itr = (Path(directory),)
    for f in itr:
        spec = importlib.util.spec_from_file_location("module.dumb", f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for cls in (c for name,c in mod.__dict__.items() if not name.startswith('_')):
            if not isclass(cls) or not issubclass(cls, Ixal.Unit):
                continue
            if '_upstream' not in dir(cls) or 'name' not in dir(cls) or 'ver' not in dir(cls):
                continue
            print('Checking {} from {} ...'.format(cls.name, cls._upstream), end=' ')
            try:
                lv = isLatest(cls._upstream, cls.ver)
                if lv:
                    print('{}{}Outdated: {}{}'.format(Fore.YELLOW, Style.BRIGHT, lv, Style.RESET_ALL))
                else:
                    print('{}{}OK{}'.format(Fore.GREEN, Style.BRIGHT, Style.RESET_ALL))
            except BaseException as e:
                print('{}{}ERROR {}{}'.format(Fore.RED, Style.BRIGHT, e, Style.RESET_ALL))

def main():
    sys.stderr.write("sys.argv = {}\n".format(sys.argv))
    nameArgv0 = sys.argv.pop(0)
    if len(sys.argv) < 1:
        sys.stderr.write("Usage: {} add|latest\n".format(nameArgv0))
        return 1

    # Add: add packages into a repository
    nameCmd = sys.argv.pop(0)
    if nameCmd == "add":
        if len(sys.argv) < 3:
            sys.stderr.write("Usage: {} add <output.files> <input.files> <pkg1.tar.zst> [<pkg2.tar.zst>...]\n".format(nameArgv0))
            return 3
        return doAdd(*sys.argv)

    elif nameCmd == "latest":
        if len(sys.argv) < 1:
            sys.stderr.write("Usage: {} latest <dir>\n".format(nameArgv0))
            return 3
        return doLatest(*sys.argv)

    else:
        sys.stderr.write("Error: Unknown command {}\n".format(nameCmd))
        return 2
