"""Fingerprint and reproduce the private viewport helper qualification."""
from pathlib import Path
import hashlib, json, os, subprocess, sys
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
out=root/'conker/build/game-viewport-helper-shape-screen'
expected={'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382', 'conker/build/conker.us.elf': '120d4983b9d32f40e208a8cb81d299e1e8b90f64938209aba3332a0cc4375ec1', 'conker/build/conker.ld': '6479ca7cef48dc77d746c16afcc244de6bfb80c6789ba79a03d6f110e42a98d5', 'conker/src/game/generated_138520.c': '4296bc1df7c67483fc8cdb6dab3704b722b25cc395e7a2bffd990a1d4d4b47c1', 'conker/build/src/game/generated_138520.c.o': '6e1c28ccd7908f35b84050ef2177826b3bbdb1fb2d2dc4fafcf48d07f812594e', 'conker/asm/138520.s': 'ad0efe574a623e2a2a9ef2446c7536d7ccf35a12d90388c7cf60aa947e519761', 'conker/retail_word_patches.us.csv': '53f66c763ff6113111f0a3c1f02a77af75df4a4a42108b57cb4c4a6543368837', 'conker/retail_layout.us.txt': '2e354c2be1de84126bb0d15b716a1af2eb21aea8e5befe669c7c03c1731a3365', 'conker/progress.csv': '05df80ca5e4799ca0186104ce8c9200fd5845ef1bf309afa8ceca51063bdf871', 'ido/ido5.3_recomp/cc': 'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a'}
for name,want in expected.items():
 data=(root/name).read_bytes()
 if hashlib.sha256(data).hexdigest()!=want:raise ValueError('qualification input changed: '+name)
env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root),PYTHONDONTWRITEBYTECODE='1')
for name in ('owner','guard','behavior','native','padder','fault','image'):
 subprocess.run([sys.executable,'-m','tools.tests.game_viewport_helper_1510b7b4_'+name],cwd=root,env=env,check=True)
print('viewport helper private qualification passed; candidate remains uncredited',flush=True)
