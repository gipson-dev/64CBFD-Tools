from pathlib import Path
import importlib.util,sys,itertools,json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_point_transform_match import read
r=Path.cwd();out=r/'conker/build/game-emitter-descriptor-150d7120-screen'
from tools.tests import game_emitter_descriptor_150d7120_behavior as b
s=(out/'selected.c').read_text();start=s.index('typedef struct { f32 x, y, z; } Position150D7120;');end=s.index('s32 func_150D728C',start);piece=s[start:end]
head,body=piece.split('/* Prepare a world emitter',1);body='/* Prepare a world emitter'+body
bad={
 'opacity':body.replace('descriptor.f02 = 255','descriptor.f02 = 254'),
 'signed_offset':body.replace('descriptor.f04 = -64','descriptor.f04 = -63'),
 'missing_position':body.replace('descriptor.position = *position;','descriptor.position.x = 0.0f; descriptor.position.y = 0.0f; descriptor.position.z = 0.0f;'),
 'wrong_scale':body.replace('descriptor.f30 = 414.0f','descriptor.f30 = 415.0f'),
 'wrong_global':body.replace('descriptor.f40 = D_800A0AE0','descriptor.f40 = D_800A0AE4'),
 'missing_precursor':body.replace('    func_151C05A4(position, slot, context);\n',''),
 'wrong_slot':body.replace('func_1514FCE8(&descriptor, slot, context);','func_1514FCE8(&descriptor, slot ^ 1, context);')}
assert all(v!=body for v in bad.values()) and len(set(bad.values()))==len(bad)
code='#include <ultra64.h>\n'+head+'\n'.join(v.replace('func_150D7120','candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
code+=r'''
typedef union {u32 u;f32 f;} Bits;
typedef struct {u32 slot,context,mutation,seed,initial[3],expected[3],globals[3];} Case;
static const Case cases[]={
'''
rows=[]
for slot,context,mutation,seed in itertools.product((0,1,0xff,0x78),(0,1,0xffffffff),(0,1),(0,1,127,255)):
 c=b.Case(slot,context,mutation,0,seed);fixture=b.fixture(c);m,_,obs=b.reference(fixture,c);p=b.STACK-0x5c
 initial=[read(fixture,b.P+i*4) for i in range(3)];pos=[read(m,p+0x10+i*4) for i in range(3)];glob=[read(m,p+0x40+i*4) for i in range(3)]
 rows.append('{%s,%s,%s,%s,{%s},{%s},{%s}}'%tuple(['0x%Xu'%x for x in (slot,context,mutation,seed)]+[','.join('0x%Xu'%x for x in v) for v in (initial,pos,glob)]))
code+=',\n'.join(rows)+'\n};\n'
code+=r'''
typedef char Layout[sizeof(void*)==4 && sizeof(EmitterDescriptor150D7120)==92 && __builtin_offsetof(EmitterDescriptor150D7120,position)==16 && __builtin_offsetof(EmitterDescriptor150D7120,f58)==88?1:-1];
f32 D_800A0AE0,D_800A0AE4,D_800A0AE8;
static Position150D7120 pos;static const Case *current;static u32 step,error;
static f32 real(u32 x){Bits b;b.u=x;return b.f;}static u32 word(f32 x){Bits b;b.f=x;return b.u;}
static void precursor(u32 which,Position150D7120*p,u8 slot,s32 context){
 if(which!=step||p!=&pos||slot!=(u8)current->slot||(u32)context!=current->context)error=1;step++;
 if(current->mutation){p->x=real(0x10203040u+current->seed+which*0x100);p->y=real(0x10203041u+current->seed+which*0x100);p->z=real(0x10203042u+current->seed+which*0x100);
  if(which==0)D_800A0AE0=real(0x40000000u+current->seed);
  if(which==1)D_800A0AE4=real(0x40000001u+current->seed);
  if(which==2)D_800A0AE8=real(0x40000002u+current->seed);
 }}
void func_151C04F8(Position150D7120*p,u8 s,s32 c){precursor(0,p,s,c);}
void func_151C05A4(Position150D7120*p,u8 s,s32 c){precursor(1,p,s,c);}
void func_151C05F0(Position150D7120*p,u8 s,s32 c){precursor(2,p,s,c);}
void func_1514FCE8(EmitterDescriptor150D7120*d,u8 s,s32 c){
 if(step!=3||s!=(u8)current->slot||(u32)c!=current->context)error=1;step++;
 if(d->f00!=0||d->f02!=255||d->f04!=-64||d->f06!=71||d->f08!=6||d->f0C!=4||
 word(d->position.x)!=current->expected[0]||word(d->position.y)!=current->expected[1]||word(d->position.z)!=current->expected[2]||
 word(d->f1C)!=0x41b80000||word(d->f20)!=0x41f00000||word(d->f24)!=0x42340000||word(d->f28)!=0x42540000||
 word(d->f2C)!=0x434b0000||word(d->f30)!=0x43cf0000||d->f34!=7||d->f38!=3||word(d->f3C)!=0x41700000||
 word(d->f40)!=current->globals[0]||word(d->f44)!=current->globals[1]||word(d->f48)!=current->globals[2]||
 d->f4C!=25||d->f4E!=15||d->f50!=100||d->f52!=100||d->f54!=12||d->f56!=20||d->f58!=0)error=1;
}
typedef void(*Candidate)(Position150D7120*,u8,s32);
'''
code+='static Candidate candidates[]={'+','.join('candidate_'+str(i) for i in range(len(bad)+1))+'};\n'
code+=r'''
static int run(void){u32 i,j,killed=0;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;
  for(j=0;j<sizeof(candidates)/sizeof(candidates[0]);j++){
   pos.x=real(current->initial[0]);pos.y=real(current->initial[1]);pos.z=real(current->initial[2]);
   D_800A0AE0=real(0x80000000);D_800A0AE4=real(0x7fc12345);D_800A0AE8=real(0x3f800001);
   step=error=0;candidates[j](&pos,(u8)current->slot,(s32)current->context);
   if(step!=4)error=1;if(error){if(j==0)return 10;killed|=1u<<(j-1);}
  }
 }
 return killed==127u?0:11;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
p=out/'native-emitter.c';p.write_text(code);profiles=[]
for opt in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=out/('native-emitter'+opt+alias);q=subprocess.run(native_command(opt)+[alias,'-o',str(exe),str(p)],cwd=r,capture_output=True,text=True)
  assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(exe)],cwd=r,capture_output=True);assert q.returncode==0,(opt,alias,q.returncode,q.stderr)
  profiles.append((opt,alias))
report=dict(native32=True,cases=len(rows),profiles=profiles,ubsan=True,negative_controls=list(bad),all_controls_detected=True,retained_bytes_excluded=3,helpers_modeled=True)
(out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
