"""Native SDK32 tests against the independent guest-level reference."""
import itertools,json,subprocess
from tools.experiments import game_mode_transition_1511172c_match as p
from tools.tests import game_mode_transition_1511172c_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 source=(p.out/'selected-source.c').read_text();selected=p.body(source,p.NAME)
 controls={'mode':('mode == 1','mode == 2'),'changed':('mode != D_800B0DF0[9]','mode == D_800B0DF0[9]'),'status':('D_800B0DF0[8] == 4','D_800B0DF0[8] == 3'),'flag':('D_80038080 != 0','D_80038080 == 0'),'loop':('index < 360','index < 359'),'cleanup':('[0] + index','[0] + index + 1'),'mode_store':('D_800B0DF0[9] = mode;','D_800B0DF0[9] = mode + 1;'),'load_arg':('&D_800DBE80, 2, 13,','&D_800DBE80, 2, 12,'),'release_gate':('if (D_800DBE80)','if (!D_800DBE80)')}
 def digest(calls):
  h=2166136261
  for target,args in calls:
   tag={g.RELEASE:1,g.RESET:2,g.CLEAN:3,g.LOAD:4}[target];vals=list(args)+[0]*(4-len(args))
   if target==g.RELEASE:vals[0]={0:0,0x80000:1,0x81000:2}[vals[0]]
   if target==g.LOAD:assert vals[0]==g.BLOCK;vals[0]=1
   for value in [tag,*vals]:h=((h^g.u32(value))*16777619)&0xffffffff
  return h
 rows=[]
 for i,(mode,current,status,flag,allocated,mutation)in enumerate(itertools.product((1,4,6,0x101),(1,4),(0,4),(0,1),(0,1),(0,1,4,11))):
  c=g.Case(mode,current,status,flag,allocated,mutation,0,i%3);m,calls=g.reference(c,g.fixture(c));rows.append((c,digest(calls),len(calls),int(g.read(m,g.STATEPTR)==g.STATE1),m[g.STATE0+8],m[g.STATE0+9],m[g.STATE1+8],m[g.STATE1+9],{0:0,0x80000:1,0x81000:2}[g.read(m,g.BLOCK)]))
 code='#include <ultra64.h>\n'+r'''
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {u32 mode,current,status,flag,allocated,mutation,hash,calls,which,s08,s09,s18,s19,block;} Fixture;
 static u8 state0[64],state1[64],token1,token2;static s32 slots[256];static const Fixture *cur;static u32 h,calls,cleans;
 u8 *D_800B0DF0;u8 D_80038080;s32 *D_800891BC[256];void *D_800DBE80;
 static void event(u32 t,u32 a,u32 b,u32 c,u32 d){u32 v[5],i;v[0]=t;v[1]=a;v[2]=b;v[3]=c;v[4]=d;for(i=0;i<5;i++)h=(h^v[i])*16777619u;calls++;}
 static u32 blockid(void *p){if(p==0)return 0;if(p==&token1)return 1;if(p==&token2)return 2;return 99;}
 void func_10004074(void *p){event(1,blockid(p),0,0,0);if(cur->mutation&4)D_800B0DF0=state1;if(cur->mutation&8)D_800DBE80=&token2;}
 s32 func_15111858(void){event(2,0,0,0,0);return 0;}
 void func_1510D694(s32 n){event(3,(u32)n,0,0,0);if(cleans++==0){if(cur->mutation&1)D_800B0DF0=state1;if(cur->mutation&2)D_800891BC[7]=&slots[8];}}
 void func_1502B7F0(void **p,s32 a,s32 b,s32 c){event(4,(u32)(p==&D_800DBE80),(u32)a,(u32)b,(u32)c);}
 '''
 for name,text in {'selected':selected,**{n:selected.replace(a,b,1)for n,(a,b) in controls.items()}}.items():
  if name!='selected':assert text!=selected,name
  code+='\n'+text.replace(p.NAME,'test_'+name,1)+'\n'
 code+='\nstatic const Fixture fixtures[]={\n'
 for c,h,n,which,s08,s09,s18,s19,block in rows:
  vals=(c.mode,c.current,c.status,c.flag,c.allocated,c.mutation,h,n,which,s08,s09,s18,s19,block);code+='{'+','.join(str(x)+'u' for x in vals)+'},\n'
 code+='};\n'+r'''
 typedef void(*Update)(s32);
 static int check(Update fn){u32 n,i;for(n=0;n<CASE_COUNT;n++){cur=fixtures+n;for(i=0;i<64;i++){state0[i]=state1[i]=0;}state0[8]=cur->status;state0[9]=cur->current;state1[8]=4;state1[9]=7;D_800B0DF0=state0;D_80038080=cur->flag;D_800DBE80=cur->allocated?&token1:0;for(i=0;i<256;i++){slots[i]=0x1000+i*512;D_800891BC[i]=&slots[i];}h=2166136261u;calls=cleans=0;fn(cur->mode);if(h!=cur->hash||calls!=cur->calls||(u32)(D_800B0DF0==state1)!=cur->which||state0[8]!=cur->s08||state0[9]!=cur->s09||state1[8]!=cur->s18||state1[9]!=cur->s19||blockid(D_800DBE80)!=cur->block)return 1;}return 0;}
 static int run(void){if(check(test_selected))return 10;
 '''.replace('CASE_COUNT',str(len(rows)))
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');src=p.out/'native.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=p.out/('native'+opt);v=subprocess.run(native_command(opt)+[str(src),'-o',str(exe)],cwd=p.root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr);v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(rows),negative_controls=len(controls),UBSan=True)
 result=dict(profiles=reports,modeled_helpers=True,source_installed=False);(p.out/'native.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
