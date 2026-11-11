"""Typed SDK32 radial dispatcher tests with effective source controls."""
import itertools,json,subprocess
from tools.experiments import game_radial_dispatch_1514c2f0_match as p
from tools.tests import game_radial_dispatch_1514c2f0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=(p.out/'selected-source.c').read_text(encoding='utf-8');body=p.body(selected,p.NAME)
 controls={'quarter':('angle - 64','angle - 63'),'count':('i < count','i <= count'),'radius':('radius * sample + z','radius * sample - z'),'x':('x + radius * quarter','x - radius * quarter'),'step':('angle += step','angle -= step'),'callback':('if (!callback(','if (callback('),'start':('angle, start, radius','angle, angle, radius'),'selector':('D_8008AA00[selector]','D_8008AA00[selector ^ 1]')}
 rows=[]
 for count,mode,fail,step,mutation in itertools.product((-1,0,1,2,4),(0,1),(0,1,100),(-128,-2,0,7,127),(0,1,2,8,11)):
  c=g.Case(count=count,mode=mode,fail=fail,step=step,mutation=mutation);initial=g.fixture(c);g.put(initial,g.STACK+20,c.step&0xFFFFFFFF);want,calls=g.reference(initial,c);rows.append((c,calls,g.read(want,g.TABLE+c.selector*4)))
 code='#include <ultra64.h>\n'+p.DECLS+r'''
_Static_assert(sizeof(void*)==4 && sizeof(f32)==4 && sizeof(s16)==2,"SDK32");
typedef struct {u32 target;u32 args[15];} Event;
typedef struct {s32 count,step,mode,fail,mutation;u32 n,table;Event events[12];} Fixture;
static const Fixture *current;static u32 eventCount,sineCount,callbackCount,bad;
RadialCallback176A00 D_8008AA00[256];
static u32 asbits(f32 n){union{u32 u;f32 f;}v;v.f=n;return v.u;}
static s32 cb0(s32,s16,f32,f32,f32,f32,f32,f32,u8,u8,f32,s32,f32,s32,u8);
static s32 cb1(s32,s16,f32,f32,f32,f32,f32,f32,u8,u8,f32,s32,f32,s32,u8);
static void event(u32 target,const u32 *args,u32 n){u32 i;if(eventCount>=current->n){bad=1;eventCount++;return;}if(current->events[eventCount].target!=target)bad=1;for(i=0;i<n;i++)if(args[i]!=current->events[eventCount].args[i])bad=1;eventCount++;}
f32 func_151423D8(u8 a){u32 x=a;event(1,&x,1);if((current->mutation&1)&&sineCount==0)D_8008AA00[2]=cb1;sineCount++;return ((s32)a-128)/128.f;}
static s32 callback(u32 target,s32 a,s16 b,f32 c,f32 d,f32 e,f32 f,f32 h,f32 i,u8 j,u8 k,f32 l,s32 m,f32 n,s32 o,u8 q){u32 args[]={a,(u32)(s32)b,asbits(c),asbits(d),asbits(e),asbits(f),asbits(h),asbits(i),j,k,asbits(l),(u32)m,asbits(n),(u32)o,q};u32 ordinal=callbackCount++;event(target,args,15);if(ordinal==0){if(current->mutation&2)D_8008AA00[2]=0;if(current->mutation&8)D_8008AA00[2]=cb1;}return ordinal!=(u32)current->fail;}
static s32 cb0(s32 a,s16 b,f32 c,f32 d,f32 e,f32 f,f32 h,f32 i,u8 j,u8 k,f32 l,s32 m,f32 n,s32 o,u8 q){return callback(2,a,b,c,d,e,f,h,i,j,k,l,m,n,o,q);}
static s32 cb1(s32 a,s16 b,f32 c,f32 d,f32 e,f32 f,f32 h,f32 i,u8 j,u8 k,f32 l,s32 m,f32 n,s32 o,u8 q){return callback(3,a,b,c,d,e,f,h,i,j,k,l,m,n,o,q);}
'''
 for name,changed in {'selected':body,**{n:body.replace(old,new,1)for n,(old,new)in controls.items()}}.items():
  if name!='selected':assert changed!=body,name
  code+='\n'+changed.replace(p.NAME,'test_'+name,1)+'\n'
 code+='\nstatic const Fixture fixtures[]={\n'
 for c,calls,table in rows:
  events=[]
  for t,args in calls:
   a=list(args)+[0]*(15-len(args));events.append('{%du,{%s}}'%(1 if t==g.SINE else 2 if t==g.CB else 3,','.join(str(x&0xFFFFFFFF)+'u'for x in a)))
  events+=['{0,{0}}']*(12-len(events));tablecode=0 if table==0 else 2 if table==g.CB else 3
  code+='{%d,%d,%d,%d,%d,%du,%du,{%s}},\n'%(c.count,c.step,c.mode,c.fail,c.mutation,len(calls),tablecode,','.join(events))
 code+='};\n'
 code+=r'''
typedef void(*Update)(f32,f32,f32,f32,u8,s8,s16,u8,s32,f32,s32,u8);
static int check(Update fn){u32 n,i,t;for(n=0;n<CASE_COUNT;n++){current=fixtures+n;eventCount=sineCount=callbackCount=bad=0;for(i=0;i<256;i++)D_8008AA00[i]=0;D_8008AA00[2]=current->mode?cb0:0;
 fn(10.f,-10.f,5.f,2.f,250,(s8)current->step,(s16)current->count,2,(s32)0x81234567,0.75f,(s32)0xAABBCCDD,0xFE);
 t=D_8008AA00[2]==0?0:D_8008AA00[2]==cb0?2:D_8008AA00[2]==cb1?3:4;if(bad||eventCount!=current->n||t!=current->table)return 1;}return 0;}
static int run(void){if(check(test_selected))return 10;
'''.replace('CASE_COUNT',str(len(rows)))
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');src=p.out/'native.c';src.write_text(code);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=p.out/('native'+opt);v=subprocess.run(native_command(opt)+[str(src),'-o',str(exe)],cwd=p.root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr);v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(rows),controls=len(controls),UBSan=True,typed_12_argument_ABI=True)
 r=dict(profiles=reports,stack_home_mutations_excluded_from_native=True,callback_and_sine_modeled=True,source_installed=False);(p.out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
