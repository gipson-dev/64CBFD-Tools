from pathlib import Path
import subprocess
from tools.tests.test_game_projected_packet_draw import native_command
p=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=p/'conker/build/game-actor-associated-update-1511473c-screen';src=(out/'native.c').read_text()
for name,old,new in [('gate','actor[0x137] != 0','actor[0x137] == 0'),('bound','index < D_800DBEF0','index <= D_800DBEF0'),('scaled','* D_800A2F60','+ D_800A2F60')]:
 assert src.count(old)==1,(name,src.count(old));c=out/('native-negative-'+name+'.c');c.write_text(src.replace(old,new))
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=out/('negative-'+name+alias);q=subprocess.run(native_command('-O2')+['-mstackrealign',alias,'-o',str(exe),str(c)],capture_output=True,text=True);assert q.returncode==0,q.stderr
  r=subprocess.run([str(exe)],capture_output=True);print(name,alias,'exit',r.returncode,flush=True);assert r.returncode==42
