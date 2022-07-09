import shutil
from pathlib import Path

from Ixal import Unit

class WinPy(Unit):
    name = 'winpy'
    ver = '3.10.4.0'
    _subver='3.10'
    rel = '1'
    desc = "Native Windows Python"
    arch = 'x86_64'
    src = "https://sourceforge.net/projects/winpython/files/WinPython_{0}/{1}/Winpython64-{1}dot.exe/download".format(_subver, ver)

    def build(self):
        dirSrc = next(Path(self.src[0]).glob('python-*.amd64'))
        with self.chdir(dirSrc):
            shutil.rmtree('Doc', ignore_errors=True)
            shutil.rmtree('tcl', ignore_errors=True)

    def package(self):
        dirDest = Path('winpy')
        dirDest.mkdir(exist_ok=True, parents=True)
        with self.chdir(dirDest):
            dirSrc = next(Path(self.src[0]).glob('python-*.amd64'))
            for f in dirSrc.iterdir():
                shutil.move(f, '.')
            #shutil.move(Path(self.src[0]) / 'scripts' / 'env.bat', '.') # Doesn't seem to be useful

if __name__ == '__main__':
    WinPy().make()


