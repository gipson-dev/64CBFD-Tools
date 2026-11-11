"""Typed SDK32 effect callback cases with effective incorrect-C controls."""
import itertools,json,subprocess
from tools.experiments import game_effect_callback_150ddfac_match as p
from tools.tests import game_effect_callback_150ddfac_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=(p.out/'selected-source.c').read_text(encoding='utf-8');head=selected[:selected.index('/* Non-matching placeholders')];body=p.body(selected,p.NAME)
 controls={'wrong_range':('70.0f','71.0f'),'wrong_base':(' + 10.0f',' + 11.0f'),'wrong_payload':('payload[0x20] = 4','payload[0x20] = 5'),'wrong_kind':('descriptor.kind = 29','descriptor.kind = 28'),'wrong_flags':('descriptor.flags = 17','descriptor.flags = 18'),'wrong_position':(')].x, height,',')].z, height,'),'wrong_mask':('first & 255','first & 127'),'wrong_sum':('(third & 1) + (second & 1)','(third & 1) ^ (second & 1)')}
 rows=[]
 for choice,index,mutation,rng,parity in itertools.product((0,1),(-1,0,1),(0,1,2,3,8,11),(0,g.bits(.5),g.bits(1.)),(0,1)):
  c=g.Case(choice=choice,index=index,mutation=mutation,random_float=rng,first=0x123456F8,second=parity,third=1);initial=g.fixture(c);want,args=g.reference(initial,c);rows.append((c,args,want[g.PAYLOAD+0x20],want[g.ACTOR+0x0C],want[g.ACTOR+1]))
 code=head+r'''
_Static_assert(sizeof(void*)==4,"SDK32");
_Static_assert(sizeof(EffectPosition108E90)==20 && __builtin_offsetof(EffectDescriptor108E90,kind)==6 && __builtin_offsetof(EffectDescriptor108E90,resource)==24,"effect layout");
typedef struct {u8 pad0[1],tag1,pad2[10],tagC,padD[32];s8 index;u8 pad2E[0x66];EffectPosition108E90 *positions;u8 *payload;} TestOwner;
_Static_assert(__builtin_offsetof(TestOwner,index)==0x2D && __builtin_offsetof(TestOwner,positions)==0x94 && __builtin_offsetof(TestOwner,payload)==0x98,"actor layout");
typedef struct {u32 choice;int index;u32 mutation,rng,first,second,third,args[13],payload,tagC,tag1;} Fixture;
static TestOwner actor;static EffectPosition108E90 positions[3],altPositions[3];static u8 payload[128],altPayload[128],parameter[16];static const Fixture *current;static u32 calls,bad;
static f32 asfloat(u32 n){union{u32 u;f32 f;}v;v.u=n;return v.f;}
static u32 asbits(f32 n){union{u32 u;f32 f;}v;v.f=n;return v.u;}
f32 func_150ADA68(void){if(calls++!=0)bad=1;if(current->mutation&1){actor.payload=altPayload;actor.positions=&altPositions[1];}return asfloat(current->rng);}
s32 func_150ADA20(void){u32 stage=calls++;if(stage<1||stage>4){bad=1;return 0;}if((current->mutation&2)&&stage==3){actor.index=-1;positions[0].x=42.f;positions[0].z=-17.f;}if((current->mutation&8)&&stage==4){actor.tagC=0xC3;actor.tag1=0xD4;}return (s32)(stage==1?current->choice:stage==2?current->first:stage==3?current->second:current->third);}
struct210 *func_1513C73C(s32 a,u8 b,u8 c,s32 d,f32 x,f32 y,f32 z,f32 r1,f32 r2,u8 i,u8 j,s32 k,u8 l,s32 n){EffectDescriptor108E90 *v=(EffectDescriptor108E90*)a;u32 got[]={b,c,(u32)d,asbits(x),asbits(y),asbits(z),asbits(r1),asbits(r2),i,j,(u32)k,l,(u32)n};u32 t;
 if(calls++!=5)bad=1;for(t=0;t<13;t++)if(got[t]!=current->args[t])bad=1;
 if(v->flags!=17||v->lifetime!=100||v->kind!=((current->choice&1)?30:29)||v->value8||v->valueC||v->value10!=255||v->value11!=255||v->value12||v->value13||v->value14||v->value15!=255||v->resource!=0x30002)bad=1;return 0;}
'''
 for name,changed in {'selected':body,**{n:body.replace(old,new,1)for n,(old,new)in controls.items()}}.items():
  if name!='selected':assert changed!=body,name
  code+='\n'+changed.replace(p.NAME,'test_'+name,1)+'\n'
 code+='\nstatic const Fixture fixtures[]={\n'
 for c,args,payload0,tagc,tag1 in rows:
  arglist=list(args);arglist[2]=0
  code+='{%du,%d,%du,%du,%du,%du,%du,{%s},%du,%du,%du},\n'%(c.choice,c.index,c.mutation,c.random_float,c.first,c.second,c.third,','.join(str(x)+'u'for x in arglist),payload0,tagc,tag1)
 code+='};\n'
 code+=r'''
typedef s32(*Update)(u8*,f32,f32,f32,f32,void*);
static int check(Update fn){u32 n,i;for(n=0;n<CASE_COUNT;n++){Fixture local;current=fixtures+n;local=*current;local.args[2]=(u32)parameter;current=&local;calls=bad=0;for(i=0;i<sizeof(actor);i++)((u8*)&actor)[i]=0;for(i=0;i<128;i++)payload[i]=altPayload[i]=0;
 for(i=0;i<3;i++){positions[i].x=9.f+(f32)i;positions[i].y=0;positions[i].z=-19.f-(f32)i;}actor.positions=&positions[1];actor.payload=payload;actor.index=(s8)current->index;actor.tagC=0xA1;actor.tag1=0xB2;
 if(fn((u8*)&actor,1.f,2.f,3.f,100.f,parameter)!=1||bad||calls!=6||payload[0x20]!=current->payload||actor.tagC!=current->tagC||actor.tag1!=current->tag1)return 1;}return 0;}
static int run(void){if(check(test_selected))return 10;
'''.replace('CASE_COUNT',str(len(rows)))
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=p.out/'native.c';src.write_text(code);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=p.out/('native'+opt);v=subprocess.run(native_command(opt)+[str(src),'-o',str(exe)],cwd=p.root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr);v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(rows),controls=len(controls),UBSan=True,typed_layout_asserted=True)
 r=dict(profiles=reports,argument_home_mutation_excluded_from_native=True,modeled_helpers_only=True,source_installed=False);(p.out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
