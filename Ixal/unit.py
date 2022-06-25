import Eikthyr as eik
import luigi as lg
from urllib.parse import urlparse
from pathlib import Path
from plumbum import local

from logzero import setup_logger
logger = setup_logger('Ixal')


class DownloadTask(eik.Task):
    url = lg.Parameter()
    cmd = lg.ListParameter(significant=False, default=("curl", "-qfLC", "-", "--retry", "5", "--retry-delay", "5", "-o", "{1}", "{0}"))

    def parseFileName(self):
        p = Path(urlparse(self.url).path)
        if p.name == "download":
            p = p.parent
        return p.name

    def generates(self):
        return eik.MetaTarget(self, self.parseFileName())

    def run(self):
        with self.output().pathWrite() as fw:
            args = [s.format(self.url, fw) for s in self.cmd[1:]]
            self.ex(local[self.cmd[0]][args])


class Unit:
    # Expected to get a plumbum object
    def ex(self, chain):
        logger.info("EX: {}".format(chain))
        chain & FG

    def make(self):
        eik.run((DownloadTask(self.src),))
        print("MAKE")

