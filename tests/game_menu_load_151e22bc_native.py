"""Private native32 finite selector and shared-backing alias checks."""
from pathlib import Path
import importlib.util,itertools,json,subprocess,sys
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-menu-load-151e22bc-durable'
from tools.tests import game_menu_load_151e22bc_guest as g
source=body((out/'alias-00.c').read_text(),'func_151E22BC')
header='''typedef signed char s8; typedef unsigned char u8; typedef int s32;
extern s8 *D_8008FDD4, *D_80082BBC; extern s8 D_800AB690[], D_800E0BE0[];
s32 func_151DD9E4(void);
'''
cases=[g.Case(i,(-128,0,1)[i%3],(0,3,4,5,255)[i%5],0) for i in range(-128,128)]
cases += [g.Case(i,v,k,a) for i,v,k,a in itertools.product((0,1,2,5,7,8,9),(-128,1),(3,4,255),range(-16,22)) if a]
rows=[]
for c in cases:
    initial,rec=g.fixture(c);wanted=g.reference(initial,c,rec)
    dest=','.join(str(wanted[g.DEST+i]) for i in range(28));record=','.join(str(wanted[rec+i]) for i in range(10))
    rows.append('{%d,%d,%d,%d,{%s},{%s}}'%(c.index,c.value,c.clamp,c.alias,dest,record))
harness=r'''
typedef signed char s8; typedef unsigned char u8; typedef int s32;
s8 *D_8008FDD4,*D_80082BBC; s8 D_800AB690[16];
s8 settingsArena[256];
__asm__(".globl D_800E0BE0\n.set D_800E0BE0,settingsArena+128");
static s8 statusBytes[128],records[3000]; static int calls;
s32 func_151DD9E4(void){calls++;return 0x12345678;}
s32 func_151E22BC(void);
typedef struct {s32 index,value,clamp,alias;u8 dest[28],record[10];} Row;
static const Row rows[]={ROWS};
static int run(void){unsigned n,i;u8 *rec,*dest=(u8*)settingsArena+128;
 if(sizeof(void*)!=4)return 10;
 D_8008FDD4=statusBytes;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){
  for(i=0;i<256;i++)settingsArena[i]=(s8)0xa5;
  for(i=0;i<96;i++)settingsArena[96+i]=(s8)(i*29+0x35);
  for(i=0;i<3000;i++)records[i]=(s8)0xa5;
  statusBytes[0x42]=0;D_800AB690[0]=(s8)rows[n].index;
  if(rows[n].alias){rec=dest+rows[n].alias-1;D_80082BBC=(s8*)(rec-rows[n].index*10);}
  else{D_80082BBC=records+1280;rec=(u8*)(D_80082BBC+rows[n].index*10);}
  for(i=0;i<10;i++)rec[i]=(u8)(i*37+11);
  rec[1]=(u8)rows[n].value;rec[3]=(u8)rows[n].clamp;calls=0;
  if(func_151E22BC()!=0x12345678||calls!=1)return 11;
  for(i=0;i<28;i++)if(dest[i]!=rows[n].dest[i])return 12;
  for(i=0;i<10;i++)if(rec[i]!=rows[n].record[i])return 13;
 }
 return 0;
}
'''.replace('ROWS',',\n'.join(rows))
candidate=out/'native-selected.c';fixture=out/'native-fixture.c';candidate.write_text(header+source);fixture.write_text(harness+START)
def execute(text,name,opt):
    code=out/(name+'.c');code.write_text(header+text);exe=out/(name+'-'+opt[1:])
    cmd=native_command(opt)+['-Wno-type-limits',str(code),str(fixture),'-o',str(exe)]
    cc=subprocess.run(cmd,cwd=root,capture_output=True,text=True);assert not cc.returncode,(name,opt,cc.stderr)
    return subprocess.run([str(exe)]).returncode
for opt in ('-O0','-O2','-O3'):assert execute(source,'native-selected',opt)==0,opt
controls=[('wrong-clamp','clamped>=5','clamped>=3'),
          ('wrong-positive-check','value<=0','value<0'),
          ('missing-byte-snapshot','value=record[6];D_800E0BE0[0x11]=1;D_800E0BE0[3]=2;D_800E0BE0[0x13]=value;',
                                   'D_800E0BE0[0x11]=1;D_800E0BE0[3]=2;D_800E0BE0[0x13]=record[6];')]
rejected=[]
for name,old,new in controls:
    assert source.count(old)==1,(name,source.count(old))
    code=execute(source.replace(old,new),name,'-O2');assert code!=0,(name,code);rejected.append(name)
report={'cases_per_optimization':len(cases),'optimizations':['-O0','-O2','-O3'],'effective_controls':rejected,
        'shared_backing_via_linker_alias':True,'callee_modeled':True,'ubsan_trapping':True,'uncredited':True}
(out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
