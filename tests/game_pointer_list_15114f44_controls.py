from pathlib import Path
import subprocess
from tools.tests.test_game_projected_packet_draw import native_command
p=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=p/'conker/build/game-pointer-list-validation-15114f44-screen';src=(out/'native.c').read_text()
controls=[('mode','D_800BE9F0 == 0x36','D_800BE9F0 == 0x37'),('align','(x & 3) || (y & 3) || (z & 3)','(y & 3) || (z & 3)'),('reload','func_150AD770();\n                    count = *counts;','func_150AD770();'),('publish','D_800DBFA0 = b;','D_800DBFA0 = a;')]
for name,old,new in controls:
 assert src.count(old)==1,(name,src.count(old));f=out/('negative-'+name+'.c');f.write_text(src.replace(old,new))
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=out/('negative-'+name+alias);q=subprocess.run(native_command('-O2')+['-mstackrealign',alias,'-o',str(exe),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
  result=subprocess.run([str(exe)],capture_output=True);print(name,alias,'exit',result.returncode,flush=True);assert result.returncode==42
