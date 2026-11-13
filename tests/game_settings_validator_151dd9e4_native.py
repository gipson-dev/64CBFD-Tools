"""Native32 UBSan model and effective controls for the settings validator."""
from pathlib import Path
import json,subprocess
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-settings-validator-151dd9e4-durable'
text=(out/'formatted.c').read_text();fn=body(text,'func_151DD9E4')
prefix='''typedef signed char s8; typedef int s32;
s8 D_800E0BE0[28],D_8008FE54[23],D_8008FE6C[23],D_8008FE84[23];\n'''
harness='''
int run(void) {
  int mode,index,value,i,ret; s8 expected[28];
  for(mode=0;mode<2;mode++) for(index=0;index<23;index++) for(value=0;value<256;value++) {
    for(i=0;i<28;i++) D_800E0BE0[i]=(s8)(value+i*13+mode*5);
    for(i=0;i<23;i++) {
      D_8008FE54[i]=(s8)(i*11+mode*17);
      D_8008FE6C[i]=(s8)(mode ? i*17+29 : -5);
      D_8008FE84[i]=(s8)(mode ? i*37+7 : 5);
    }
    D_800E0BE0[index]=(s8)value;
    for(i=0;i<28;i++) expected[i]=D_800E0BE0[i];
    for(i=0;i<23;i++) if(expected[i]<D_8008FE6C[i] || expected[i]>D_8008FE84[i]) expected[i]=D_8008FE54[i];
    ret=func_151DD9E4();
    if(ret!=23) return 1;
    for(i=0;i<28;i++) if(D_800E0BE0[i]!=expected[i]) return 2;
  }
  return 0;
}
'''
controls={
 'exclusive_min':fn.replace('D_800E0BE0[i] < D_8008FE6C[i]','D_800E0BE0[i] <= D_8008FE6C[i]'),
 'exclusive_max':fn.replace('D_800E0BE0[i] > D_8008FE84[i]','D_800E0BE0[i] >= D_8008FE84[i]'),
 'wrong_default':fn.replace('D_800E0BE0[i] = D_8008FE54[i]','D_800E0BE0[i] = 0'),
 'wrong_return':fn.replace('return 23;','return 22;'),
 'missing_last':fn.replace('i < 23','i < 22'),
}
assert all(x!=fn for x in controls.values())
def run(name,code,opt):
    src=out/(name+'.c');exe=out/name;src.write_text(prefix+code+harness+START)
    p=subprocess.run(native_command(opt)+[str(src),'-o',str(exe)],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    return subprocess.run([str(exe)],capture_output=True,text=True)
for opt in ('-O0','-O2','-O3'):
    p=run('native-'+opt[1:],fn,opt);assert p.returncode==0,(opt,p.stdout,p.stderr)
    for name,code in controls.items():
        p=run('control-'+opt[1:]+'-'+name,code,opt);assert p.returncode!=0,(opt,name)
report={'cases_per_optimization':11776,'optimizations':['O0','O2','O3'],'effective_controls':list(controls),'ubsan':True,'uncredited':True}
(out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
