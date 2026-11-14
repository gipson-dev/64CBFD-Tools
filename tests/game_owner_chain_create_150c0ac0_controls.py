from pathlib import Path
import subprocess
from tools.tests.test_game_projected_packet_draw import native_command
p=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=p/'conker/build/game-owner-chain-create-150c0ac0-screen';src=(out/'native.c').read_text();controls=[('kind','func_15167A68(0x25, context','func_15167A68(0x24, context'),('size','allocation.size = *(s16 *)(descriptor + 0x14) * 8 + 0x48;','allocation.size = *(s16 *)(descriptor + 0x14) * 4 + 0x48;'),('gate','if (!**(u32 **)(descriptor + 8)) return 0;','if (0) return 0;'),('copy','test_copy(allocation.result + 0x18, descriptor, 0x1c);','test_copy(allocation.result + 0x18, descriptor, 0x1b);'),('last',' + *(s16 *)(descriptor + 0x14) * 8 - 4) = -1;',' + *(s16 *)(descriptor + 0x14) * 8 - 2) = -1;'),('head','*(s16 *)(allocation.result + 0x46) = 0;','*(s16 *)(allocation.result + 0x46) = 1;'),('position','*(f32 *)(allocation.result + 0x38) = *(f32 *)(position + 8);','*(f32 *)(allocation.result + 0x38) = *(f32 *)(position + 4);')]
for name,old,new in controls:
 assert src.count(old)==1,(name,src.count(old));f=out/('negative-'+name+'.c');f.write_text(src.replace(old,new))
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=out/('negative-'+name+alias);q=subprocess.run(native_command('-O2')+['-mstackrealign',alias,'-o',str(exe),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
  r=subprocess.run([str(exe)],capture_output=True);print(name,alias,'exit',r.returncode,flush=True);assert r.returncode==42
