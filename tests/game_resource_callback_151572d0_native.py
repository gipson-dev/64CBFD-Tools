"""SDK32 native semantic screen with effective negative controls."""
import itertools
import json
import subprocess
from pathlib import Path
from tools.experiments import game_resource_callback_151572d0_match as match
from tools.tests import game_resource_callback_151572d0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
p=match.OUT; root=match.ROOT
declarations=match.MANIFEST['declarations']
function=match.MANIFEST['body']
controls={
    'no_timer':('if (state->flags & 1)', 'if (0)'),
    'first_result':('if (!D_8008AD90[state->first]((u8 *)object))', 'if (D_8008AD90[state->first]((u8 *)object))'),
    'fade_gate':('(state->flags & 0x20)', '(state->flags & 0x40)'),
    'fade_rate':('state->remaining * state->fadeRate', 'state->remaining + state->fadeRate'),
}
for name,(a,b) in controls.items():assert function.count(a)==1,name
code='''#include <ultra64.h>
typedef struct { u8 unused; } struct102;
'''+declarations+r'''
_Static_assert(sizeof(void*)==4 && __builtin_offsetof(ResourceCallback151572D0,remaining)==0x16 &&
 __builtin_offsetof(ResourceCallback151572D0,alpha)==0x43 &&
 __builtin_offsetof(ResourceCallback151572D0,fadeStart)==0x64 &&
 __builtin_offsetof(ResourceCallback151572D0,linked)==0x68,"SDK32 layout");
s32 D_800BE9E4;
static u8 object[0x90] __attribute__((aligned(8)));
static u8 link[32];
struct Case {s32 flags,first,second,r1,r2,timer,delta,mutation;
 s32 outFlags,outSecond,outTimer,outAlpha,outStart,outRate,ncalls,calls[3];};
static const struct Case cases[] = {
'''
cases=[]
for flags,first,second,results,timer,delta,mutation in itertools.product(
    (0,1,0x20,0x21),(-1,0,1,2,3),(-1,0,1),((0,0),(0,1),(1,0),(1,1)),
    (-1,0,32767),(0,1,0xffff),(0,1)):
    c=g.Case(flags,first,second,*results,timer,delta,mutation,0)
    m,calls=g.reference(c)
    ids=[(g.FIRST_FNS.index(t)+1 if t in g.FIRST_FNS else
          5+g.SECOND_FNS.index(t) if t in g.SECOND_FNS else 7 if t==g.UPDATE else 8)
         for t,_ in calls]
    vals=[flags,first,second,*results,timer,delta,mutation,m[g.OBJ+0x10],m[g.OBJ+0x12],
          g.s16(g.read(m,g.OBJ+0x16,2)),m[g.OBJ+0x43],g.s16(g.read(m,g.OBJ+0x64,2)),
          g.s16(g.read(m,g.OBJ+0x66,2)),len(ids)]
    assert len(ids)<=3
    code+='{'+','.join(map(str,vals))+',{'+','.join(map(str,ids+[0]*(3-len(ids))))+'}},\n'
    cases.append(c)
code+=r'''};
static const struct Case *current;static int ncall,bad;
static int act(int id,struct102 *arg){ResourceCallback151572D0 *s=(void*)object;
 if(arg!=(struct102 *)(id==7?link:object)||ncall>=3||current->calls[ncall]!=id)bad=1;
 ncall++;
 if(current->mutation && id>=1 && id<=4){s->second=1;s->flags=0x20;s->remaining=-3;s->alpha=100;}
 if(current->mutation && id==7){s->flags|=0x20;s->remaining=4;s->fadeStart=8;s->fadeRate=7;s->alpha=50;}
 return id<=4?current->r1:current->r2;
}
static s32 f1(u8 *p){return act(1,(struct102*)p);}static s32 f2(u8 *p){return act(2,(struct102*)p);}
static s32 f3(u8 *p){return act(3,(struct102*)p);}static s32 f4(u8 *p){return act(4,(struct102*)p);}
static s32 s1(u8 *p){return act(5,(struct102*)p);}static s32 s2(u8 *p){return act(6,(struct102*)p);}
s32 (*D_8008AD90[])(u8 *)={f1,f2,f3,f4};s32 (*D_8008ADA0[])(u8 *)={s1,s2};
void func_1503F4B0(u8 *p){(void)act(7,(struct102*)p);}
void func_1516972C(struct102 *p){(void)act(8,p);}
'''
for name,text in [('selected',function)]+[(name,function.replace(a,b,1)) for name,(a,b) in controls.items()]:
    code+='\n'+text.replace('func_151572D0','test_'+name,1)+'\n'
code+=r'''
typedef void(*T)(struct102*);
static int check(T fn){u32 i,j;u8 original[0x90];
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  const struct Case *c=&cases[i];ResourceCallback151572D0 *s=(void*)object;
  for(j=0;j<sizeof(object);j++)object[j]=(u8)(j*13+0x5a);
  s->flags=c->flags;s->first=c->first;s->second=c->second;s->remaining=c->timer;
  s->alpha=130;s->fadeStart=100;s->fadeRate=3;s->linked=link;D_800BE9E4=c->delta;
  for(j=0;j<sizeof(object);j++)original[j]=object[j];
  current=c;ncall=bad=0;fn((struct102*)object);
  if(bad||ncall!=c->ncalls||s->flags!=c->outFlags||(u8)s->second!=c->outSecond||
     s->remaining!=c->outTimer||s->alpha!=c->outAlpha||s->fadeStart!=c->outStart||
     s->fadeRate!=c->outRate||s->linked!=link)return 1;
  for(j=0;j<sizeof(object);j++)if(j!=0x10&&j!=0x12&&j!=0x16&&j!=0x17&&j!=0x43&&
       j!=0x64&&j!=0x65&&j!=0x66&&j!=0x67&&object[j]!=original[j])return 2;
 }return 0;}
static int run(void){if(check(test_selected))return 1;
'''
for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
path=p/'native-sdk32.c';path.write_text(code)
profiles={}
for opt in ('-O0','-O2','-O3'):
    binary=p/('native-sdk32'+opt)
    build=subprocess.run(native_command(opt)+['-fno-builtin',str(path),'-o',str(binary)],cwd=root,capture_output=True,text=True)
    assert build.returncode==0 and not build.stdout and not build.stderr,(opt,build.stdout,build.stderr)
    run=subprocess.run([str(binary)],capture_output=True)
    assert run.returncode==0,(opt,run.returncode,run.stderr)
    profiles[opt]=dict(cases=len(cases),negative_controls=len(controls),UBSan=True)
report=dict(profiles=profiles,
            source_installed=match.body((root/match.MANIFEST['source']).read_text(),match.NAME)==function,
            helpers='modeled')
(p/'native.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
