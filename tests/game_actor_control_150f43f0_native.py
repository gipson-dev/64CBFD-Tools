"""Defined typed actor cases and effective controls for the callback."""
import itertools,json,subprocess
from tools.experiments import game_actor_control_150f43f0_match as p
from tools.tests import game_actor_control_150f43f0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=(p.out/'selected-source.c').read_text(encoding='utf-8');body=p.body(selected,p.NAME)
 controls={'kind':('== 0x3B','== 0x3C'),'audio':('0x405C, 1','0x405C, 0'),'state':('!= 0x100','!= 0x101'),'gate':('actor, 8, 0, 0, 0','actor, 9, 0, 0, 0'),'flags':('|= 0x300000','|= 0x100000'),'half':('0x1E0) = 3','0x1E0) = 4'),'float':('= 125.0f','= 124.0f'),'input':('0x405E, 6, 0x9000','0x405F, 6, 0x9000')}
 rows=[]
 for kind,state,held,gate,first,second,mutation in itertools.product((0,0x3B),(0,8,0x100),(0,1),(0,1),(0,1),(0,1),(0,1,2,4,8,16,31)):
  c=g.Case(kind,state,held,gate,first,second,mutation);want,calls=g.reference(g.fixture(c),c)
  events=[1 if t==g.AUDIO and a[2] else 2 if t==g.AUDIO else 3 if t==g.GATE else 4 if t==g.START else 5 if t==g.EXIT else 6 if a[1]==0x4054 else 7 for t,a in calls]
  values=[g.read(want,g.ACTOR+off,n)for off,n in((0x2C,4),(0x84,4),(0x134,4),(0x190,4),(0x1B4,2),(0x1E0,2),(0x348,4),(0x34C,4),(0x374,4),(0x6C8,4))];rows.append((c,events,values))
 code='#include <ultra64.h>\n'+p.DECLS+r'''
typedef struct {u8 pad00[0x2c];u32 state;u8 pad30[0x54];u32 flags;u8 pad88[0xac];u32 word134;u8 pad138[0x58];f32 value190;u8 pad194[0x20];s16 half1b4;u8 pad1b6[0x2a];s16 half1e0;u8 pad1e2[0x5c];u8 kind;u8 pad23f[0x109];f32 value348,value34c;u8 pad350[0x24];f32 value374;u8 pad378[0x350];u32 held;} TestActor;
_Static_assert(sizeof(void*)==4 && __builtin_offsetof(TestActor,flags)==0x84 && __builtin_offsetof(TestActor,word134)==0x134 && __builtin_offsetof(TestActor,kind)==0x23e && __builtin_offsetof(TestActor,held)==0x6c8,"actor layout");
typedef struct {u32 kind,state,held,gate,first,second,mutation,n,events[6],values[10];} Fixture;
static TestActor actor;static const Fixture *current;static u32 calls,bad,inputCount,audioCount;
static u32 floatbits(const f32 *p){u32 v;__builtin_memcpy(&v,p,4);return v;}
static void event(u32 x){if(calls>=current->n || current->events[calls]!=x)bad=1;calls++;}
void func_1509BFB0(s32 a,s32 b,s32 c,...){if(a!=0||b!=0x405c||(c!=0&&c!=1))bad=1;event(c?1:2);if((current->mutation&1)&&audioCount==0){actor.state=0;actor.held=0;}audioCount++;}
s32 func_15123934(u8 *a,s32 b,s32 c,s32 d,s32 e){if(a!=(u8*)&actor||b!=8||c||d||e)bad=1;event(3);if(current->mutation&2)actor.flags=0xA0000005;return current->gate;}
void func_15124B18(u8 *a){if(a!=(u8*)&actor)bad=1;event(4);if(current->mutation&4){actor.word134=0xDEADBEEF;actor.value190=99.f;}}
s32 func_151239CC(u8 *a,s32 b){if(a!=(u8*)&actor||b)bad=1;event(5);return 0;}
s32 func_1509BE40(s32 a,s32 b,s32 c,s32 d){u32 value;if(a!=1||b!=(inputCount?0x405e:0x4054)||c!=6||d!=0x9000)bad=1;event(inputCount?7:6);if((current->mutation&8)&&inputCount==0)actor.flags=0x12340005;if((current->mutation&16)&&inputCount==1)actor.flags=0x90000007;value=inputCount?current->second:current->first;inputCount++;return value;}
'''
 for name,changed in {'selected':body,**{n:body.replace(old,new,1)for n,(old,new)in controls.items()}}.items():
  if name!='selected':assert changed!=body,name
  code+='\n'+changed.replace(p.NAME,'test_'+name,1)+'\n'
 code+='\nstatic const Fixture fixtures[]={\n'
 for c,events,vals in rows:
  padded=events+[0]*(6-len(events));code+='{%du,%du,%du,%du,%du,%du,%du,%du,{%s},{%s}},\n'%(c.kind,c.state,c.held,c.gate,c.first,c.second,c.mutation,len(events),','.join(str(x)+'u'for x in padded),','.join(str(x)+'u'for x in vals))
 code+='};\n'
 code+=r'''
typedef void(*Update)(u8*);
static int check(Update fn){u32 n,i,values[10];for(n=0;n<CASE_COUNT;n++){current=fixtures+n;calls=bad=inputCount=audioCount=0;for(i=0;i<sizeof(actor);i++)((u8*)&actor)[i]=(u8)(i*29+90);actor.kind=(u8)current->kind;actor.state=current->state;actor.held=current->held;actor.flags=0x1234567F;INIT_FIELDS fn((u8*)&actor);
 values[0]=actor.state;values[1]=actor.flags;values[2]=actor.word134;values[3]=floatbits(&actor.value190);values[4]=(u16)actor.half1b4;values[5]=(u16)actor.half1e0;values[6]=floatbits(&actor.value348);values[7]=floatbits(&actor.value34c);values[8]=floatbits(&actor.value374);values[9]=actor.held;
 if(bad||calls!=current->n)return 1;for(i=0;i<10;i++)if(values[i]!=current->values[i])return 2;}return 0;}
static int run(void){if(check(test_selected))return 10;
'''.replace('CASE_COUNT',str(len(rows)))
 initial=g.fixture(g.Case());init='actor.word134=%du;actor.half1b4=(s16)%du;actor.half1e0=(s16)%du;'%(g.read(initial,g.ACTOR+0x134),g.read(initial,g.ACTOR+0x1B4,2),g.read(initial,g.ACTOR+0x1E0,2))
 for name,off in (('value190',0x190),('value348',0x348),('value34c',0x34C),('value374',0x374)):init+='{u32 v=%du;__builtin_memcpy(&actor.%s,&v,4);}'%(g.read(initial,g.ACTOR+off),name)
 code=code.replace('INIT_FIELDS',init)
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');src=p.out/'native.c';src.write_text(code);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=p.out/('native'+opt);v=subprocess.run(native_command(opt)+[str(src),'-o',str(exe)],cwd=p.root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr);v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(rows),controls=len(controls),UBSan=True,typed_layout_asserted=True)
 r=dict(profiles=reports,mutating_helpers_modeled=True,return_value_not_claimed=True,source_installed=False);(p.out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
