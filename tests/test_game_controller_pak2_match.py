"""Retail controller-pak copies: byte binding, packet model, and bounded providers."""
import os, struct, subprocess, sys, unittest
from pathlib import Path

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()

class ControllerPak2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env=dict(os.environ,CBFD_CONSUMER_ROOT=str(ROOT),PYTHONDONTWRITEBYTECODE='1')
        cls.run_module('tools.experiments.game_controller_pak2_match')

    @classmethod
    def run_module(cls,name):
        result=subprocess.run([sys.executable,'-m',name],cwd=ROOT,env=cls.env,text=True,capture_output=True,timeout=180)
        if result.returncode:raise AssertionError((name,result.stdout,result.stderr))
        print(result.stdout.strip(),flush=True)

    def test_packet_model(self):self.run_module('tools.tests.game_controller_pak2_packet_guest')
    def test_transaction_model(self):self.run_module('tools.tests.game_controller_pak2_transaction_guest')
    def test_native_ubsan(self):self.run_module('tools.tests.game_controller_pak2_native')
    def test_relocated_links(self):self.run_module('tools.tests.game_controller_pak2_rebase')
    def test_aligned_direct_caller_census(self):
        rom=(ROOT/'conker/conker.us.bin').read_bytes()
        for address,expected in ((0x151f2080,()),(0x151f22c4,(0x21f578,)),
                                 (0x151f2430,()),(0x151f2660,(0x21f95c,))):
            for word,sites in ((0x0c000000|((address>>2)&0x3ffffff),expected),(address,())):
                needle=struct.pack('>I',word)
                actual=tuple(i for i in range(0,len(rom)-3,4) if rom[i:i+4]==needle)
                self.assertEqual(actual,sites)

if __name__=='__main__':unittest.main()
