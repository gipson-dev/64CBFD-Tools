"""25 actor slots, original type callback dispatcher and opaque update effects."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_active_record_lookup_match import compile_owner
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-active-actor-update-1502378C-match'
F='func_1502378C';ENTRY=0x1502378C;ROM=0x50C3C;BODY=216;STRIDE=0x32C
MODE,POOL,INDEX,TABLE=0x800C3654,0x800CC2D0,0x800C3E78,0x80086014
FIRST,UPDATE,QUERY,RESET,MOVE,FINISH,END,ALTERNATE=0x15022998,0x1507E73C,0x150229E4,0x1502178C,0x150627D4,0x1507FEA0,0x15061B4C,0x1504A730
CALLBACK4,CALLBACK27=0x15100000,0x15100010
SYMS=dict(D_800C3654=MODE,D_800CC2D0=POOL,D_800C3E78=INDEX,D_80086014=TABLE,func_15022998=FIRST,func_1507E73C=UPDATE,func_150229E4=QUERY,func_1502178C=RESET,func_150627D4=MOVE,func_1507FEA0=FINISH,func_15061B4C=END,func_1504A730=ALTERNATE)
@dataclass(frozen=True)
class Case:
 pattern:int=3
 result:int=1
 effect:int=0
 callbacks:int=1
 mode:int=0
 phase:int=0
 seed:int=0
 onehot:int=-1

def kinds(c):
 if c.onehot>=0:return tuple((4 if c.seed&1 else 27)if i==c.onehot else 0 for i in range(26))
 options=((0,)*26,(1,)+(0,)*25,(0,)*24+(27,0),tuple(4 if i&1 else 27 for i in range(26)),tuple(0 if i%3==0 else 4 for i in range(26)),tuple((0,1,4,27,0x80000000)[i%5]for i in range(26)),tuple(0xFFFFFFFF for _ in range(26)),tuple(1 if i==24 else 0 for i in range(26)))
 return options[c.pattern]
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-512,256)}
 for base,n in ((s['D_800CC2D0'],26*STRIDE),(s['D_80086014'],128)):
  m.update({base+i:(i*29+c.seed*11+0x59)&255 for i in range(n)})
 for i,v in enumerate(kinds(c)):put(m,s['D_800CC2D0']+i*STRIDE,v)
 put(m,s['D_80086014']+16,CALLBACK4 if c.callbacks else 0);put(m,s['D_80086014']+108,CALLBACK27 if c.callbacks else 0)
 put(m,s['D_800C3E78'],0xA7,1);put(m,s['D_800C3654'],c.mode,1)
 return m
def effect(m,c,s,target,args,last):
 base=s['D_800CC2D0'];p=last if not args else args[0];slot=(p-base)//STRIDE
 if target in (CALLBACK4,CALLBACK27) and c.effect&1:
  put(m,last,0)
  if slot<24:put(m,base+(slot+1)*STRIDE,0 if read(m,base+(slot+1)*STRIDE)else 4)
 if target==s['func_1507E73C'] and c.effect&2:put(m,s['D_800C3E78'],0x80+(slot&7),1)
 if target==s['func_150229E4'] and c.effect&4:put(m,p+0x2FF,0x77,1);put(m,s['D_800C3654'],0xFF,1)
 if target==s['func_1507FEA0'] and c.effect&8:put(m,p+0x2FF,0x99,1);put(m,s['D_800C3E78'],0xFF,1)
 if target==s['func_1504A730']:put(m,s['D_800C3E78'],0xE1,1);put(m,s['D_800C3654'],0,1)
 return (0,1,0x80000000)[c.result]if target==s['func_150229E4']else 0xA5000000|(target&0xFFFF)
def observation(m,s):return(m[s['D_800C3E78']],m[s['D_800C3654']])
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];observations=[];last=s['D_800CC2D0']
 def call(t,*args):
  nonlocal last
  calls.append((t,args));observations.append(observation(m,s))
  if t==s['func_15022998']:
   last=args[0];tag=read(m,last)
   if tag in (4,27):
    cb=read(m,s['D_80086014']+4*tag)
    if cb:call(cb)
   return 0
  return effect(m,c,s,t,args,last)
 if m[s['D_800C3654']]:call(s['func_1504A730'])
 else:
  for i in range(25):
   p=s['D_800CC2D0']+i*STRIDE
   if not read(m,p):continue
   put(m,s['D_800C3E78'],i,1);call(s['func_15022998'],p);call(s['func_1507E73C'],p)
   if call(s['func_150229E4'],p):
    call(s['func_1502178C'],p,0,0xFFFFFFFF);call(s['func_150627D4'],p);call(s['func_1507FEA0'],p);put(m,p+0x2FF,1,1)
  call(s['func_15061B4C'])
 return m,calls,observations
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+256}
def linked(obj,label,function=F,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[function];asm,unknown=emit_function(text,f,rs,function,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm)
 p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',function,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def helper_object():
 text=(r/'conker/asm/49D30.s').read_text();name='func_15022998';part=text[text.index('glabel '+name):text.index('endlabel '+name)+len('endlabel '+name)].replace('glabel '+name,'.globl '+name+'\n.type '+name+',@function\n'+name+':').replace('endlabel '+name,'.size '+name+',.-'+name)
 p=o/'original-type-dispatch.s';p.write_text('.include "asm_processor_prelude.inc"\n.text\n'+part+'\n');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I',str(r/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);return p.with_suffix('.o')
def codes(label='guest',entry=ENTRY,s=SYMS):
 ps=[linked(o/n,label+'-'+str(i),entry=entry,s=s)for i,n in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))]
 assert ps[0]==ps[2] and sum(a!=b for a,b in zip(ps[0],ps[1]))==2
 helper=linked(helper_object(),label+'-dispatcher','func_15022998',s['func_15022998'],s);assert len(helper)==19
 return ps,dict(zip(range(s['func_15022998'],s['func_15022998']+76,4),helper))
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  self.observations=[];self.last_actor=s['D_800CC2D0']
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=())
  self.before=self.r[:];self.before_f=self.f[:];self.code=faults.TrackedCode(dict(self.code),self)
 def record_call(self,t):
  counts={self.syms[n]:k for n,k in [('func_15022998',1),('func_1507E73C',1),('func_150229E4',1),('func_1502178C',3),('func_150627D4',1),('func_1507FEA0',1),('func_15061B4C',0),('func_1504A730',0)]};counts.update({CALLBACK4:0,CALLBACK27:0,ENTRY:0})
  assert t in counts,hex(t);a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a));self.observations.append(observation(self.memory,self.syms))
  if t==self.syms['func_15022998']:self.last_actor=a[0]
 def hook(self,t):
  result=effect(self.memory,self.case,self.syms,t,self.calls[-1][1],self.last_actor)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0xA5000010,0xA5000011,True;self.r[2]=result&0xFFFFFFFF
def state(m):return(m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.calls,m.observations,m.events,m.trace)
def verify(m,initial,c,s=SYMS):
 want,calls,observations=reference(initial,c,s)
 assert(public(m.memory),m.calls,m.observations)==(public(want),calls,observations),(c,m.calls,calls,m.observations,observations)
 assert m.r[29]==m.before[29] and m.r[16:24]==m.before[16:24] and m.r[28]==m.before[28] and m.r[31]==m.before[31] and m.f[20:]==m.before_f[20:]
def cases():
 rows=[Case(p,v,e,cb,0,ph)for p,v,e,cb,ph in itertools.product(range(8),range(3),(0,1,2,4,8,15),(0,1),(0,8))]
 rows.extend(Case(result=v,phase=ph,seed=seed,onehot=i)for i,v,ph,seed in itertools.product(range(25),(0,2),(0,8),(0,1)))
 rows.extend(Case(mode=mode,effect=e,phase=ph)for mode,e,ph in itertools.product((1,255),(0,1,8,15),(0,8)))
 return tuple(rows)
def guest_suite():
 ps,helper=codes();visited=set();count=0
 for c in cases():
  initial=fixture(c);ms=[]
  for ws in ps:m=Oracle(ws,initial,c,connected=helper);m.run();verify(m,initial,c);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);visited.update(ms[0].visits);count+=1
 assert set(range(ENTRY,ENTRY+BODY,4))<=visited and set(helper)<=visited
 cuts=delays=0
 for c in (Case(mode=1),Case(pattern=0),Case(onehot=24,effect=15)):
  initial=fixture(c);full=Oracle(ps[0],initial,c,connected=helper);full.run()
  for cut in range(full.all_accesses):
   ms=[]
   for ws in ps:
    m=Oracle(ws,initial,c,connected=helper);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Missing access prefix')
    ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]) and(ms[0].current_pc,ms[0].delay_of)==(ms[1].current_pc,ms[1].delay_of)==(ms[2].current_pc,ms[2].delay_of)
   cuts+=1;delays+=ms[0].delay_of is not None
 aliases=0
 for name,value in [('D_800C3E78',POOL+0x2FF),('D_800C3654',INDEX)]:
  s=dict(SYMS,**{name:value});aps,ah=codes('alias-'+name,s=s)
  for p,e in itertools.product((0,3,5),(0,2,15)):
   c=Case(pattern=p,effect=e);initial=fixture(c,s);ms=[]
   for ws in aps:m=Oracle(ws,initial,c,s,connected=ah);m.run();verify(m,initial,c,s);ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);aliases+=1
 rebases=0
 for j,entry in enumerate((0x17007FF0,0x1500FFF0,0x1F008000)):
  s={n:(entry+0x10000+i*0x1000 if n.startswith('func_')else 0x90007FF0+i*0x20000)for i,n in enumerate(SYMS)}
  rps,rh=codes('rebase-'+str(j),entry,s)
  for p,e,mode in itertools.product((0,3,5),(0,15),(0,1)):
   c=Case(pattern=p,effect=e,mode=mode);initial=fixture(c,s);ms=[]
   for ws in rps:m=Oracle(ws,initial,c,s,entry,connected=rh);m.run();verify(m,initial,c,s);ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);rebases+=1
 return dict(cases=count,executions=count*3,body_words=54,slot_words=57,alignment_words=3,frame=48,guards=2,bindings=14,helper_original_words=19,all_target_and_dispatcher_words_exercised=True,access_cuts=cuts,delay_cuts=delays,guest_alias_cases=aliases,rebase_cases=rebases,independent_public_RAM_calls_and_observations=True,complete_cross_image_RAM_and_ABI=True,helper_effects_opaque_except_original_type_dispatch=True,private_only=True,matching_credit=0)
def caller_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();call=0x0C000000|((ENTRY>>2)&0x3FFFFFF)
 assert[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==struct.pack('>I',call)]==[0x462F4]
 assert not any(rom[i:i+4]==struct.pack('>I',ENTRY)for i in range(0,len(rom)-3,4))
 ws=struct.unpack_from('>13I',rom,0x462D8);assert ws[7:9]==(call,0);ps,helper=codes('caller');count=0
 for gate,selector,mode,p,e,phase in itertools.product((0,1),(0,1,255),(0,1),(0,3,5),(0,15),(0,8)):
  c=Case(pattern=p,mode=mode,effect=e,phase=phase);initial=fixture(c);put(initial,0x800C35EA,selector,1);want,calls,observations=reference(initial,c)
  if gate:want,calls,observations=dict(initial),[],[]
  elif selector!=1:
   want=dict(initial);calls=[(ALTERNATE,())];observations=[observation(want,SYMS)];effect(want,c,SYMS,ALTERNATE,(),POOL)
  else:calls=[(ENTRY,())]+calls;observations=[observation(initial,SYMS)]+observations
  ms=[]
  for program in ps:
   connected=dict(helper);connected.update(zip(range(ENTRY,ENTRY+BODY,4),program));connected.update({0x15018E5C:0,0x15018E68:0});m=Oracle(ws,initial,c,entry=0x15018E28,connected=connected);m.r[14]=gate;m.code=WindowCode(m.code,m);m.code.ends=(0x15018E5C,0x15018E68)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing original caller boundary')
   assert(public(m.memory),m.calls,m.observations)==(public(want),calls,observations),(gate,selector,c,m.calls,calls)
   assert m.r[29]==m.before[29] and m.r[16:24]==m.before[16:24];ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);count+=1
 return dict(cases=count,parent='func_15018DFC',parent_source='conker/src/game_45B80.c',window_entry='0x15018E28',window_ROM='0x462D8',window_words=13,original_exits=['0x15018E5C','0x15018E68'],zero_arguments=True,return_ignored=True,parent_full_execution_claimed=False)
def controls(body):
 return dict(wrong_mode=body.replace('D_800C3654[0] != 0','D_800C3654[0] == 0'),short_scan=body.replace('limit = 25','limit = 24'),long_scan=body.replace('limit = 25','limit = 26'),wrong_stride=body.replace('actor++;','actor = (struct127 *)((u8 *)actor + 0x328);'),wrong_activity=body.replace('actor->interaction_state != 0','actor->interaction_state == 0'),missing_index=body.replace('D_800C3E78 = index;',';'),wrong_index=body.replace('D_800C3E78 = index;','D_800C3E78 = index + 1;'),wrong_gate=body.replace('func_150229E4(actor) != 0','func_150229E4(actor) == 0'),wrong_argument=body.replace('actor, 0, -1','actor, 0, 0'),wrong_mark=body.replace('actor->unk2FF = 1;','actor->unk2FF = 2;'),early_mark=body.replace('                    func_1502178C(actor, 0, -1);','                    actor->unk2FF = 1;\n                    func_1502178C(actor, 0, -1);').replace('                    actor->unk2FF = 1;\n                }','                }'),missing_finish=body.replace('        func_15061B4C();',';'),wrong_order=body.replace('func_15022998((s32 *)actor);\n                func_1507E73C(actor);','func_1507E73C(actor);\n                func_15022998((s32 *)actor);'))
def compiled_controls():
 selected=(o/'selected-semantic-input.c').read_text();ps,helper=codes('control');rows=[]
 for label,text in controls(selected).items():
  assert text!=selected;obj,diag=compile_owner(r,o,text,'negative-'+label);assert not diag;bad=linked(obj,'negative-linked-'+label)
  found=False
  for c in (Case(pattern=3,effect=15),Case(mode=1),Case(pattern=0),Case(pattern=2),Case(result=0),Case(result=2)):
   initial=fixture(c);good=Oracle(ps[0],initial,c,connected=helper);good.run();verify(good,initial,c);m=Oracle(bad,initial,c,connected=helper);m.run()
   if(public(m.memory),m.calls,m.observations)!=(public(good.memory),good.calls,good.observations):found=True;break
  assert found,('Ineffective semantic control',label);rows.append(label)
 return dict(count=len(rows),controls=rows,compiler_or_oracle_errors_accepted=False)

IDS={t:i for i,t in enumerate((FIRST,UPDATE,QUERY,RESET,MOVE,FINISH,END,ALTERNATE,CALLBACK4,CALLBACK27))}
def call_hash(calls,observations):
 h=2166136261
 for(t,args),obs in zip(calls,observations):
  values=[IDS[t],len(args),*([args[0]-POOL,*args[1:]]if args else []),*obs]
  for v in values:h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
 return h
def native_suite():
 selected=(o/'selected-semantic-input.c').read_text();head,body=selected.split('/* Update the 25',1);body='/* Update the 25'+body
 rows=[]
 for c in cases():
  if c.phase:continue
  initial=fixture(c);want,calls,obs=reference(initial,c)
  rows.append((c,kinds(c),tuple(read(want,POOL+i*STRIDE)for i in range(26)),tuple(want[POOL+i*STRIDE+0x2FF]for i in range(26)),want[INDEX],want[MODE],call_hash(calls,obs)))
 text=head+r'''
_Static_assert(sizeof(void*)==4,"native32");
_Static_assert(sizeof(struct127)==0x32C,"actor stride");
_Static_assert(__builtin_offsetof(struct127,unk2FF)==0x2FF,"update flag");
struct127 D_800CC2D0[26];u8 D_800C3654[4],D_800C3E78;
typedef struct{u32 result,effect,callbacks,mode,seed;u32 before[26],after[26];u8 marks[26];u32 indexOut,modeOut,hash;}Fixture;
static const Fixture*current;static u32 traceHash;static struct127*last;
static void word(u32 v){traceHash=(traceHash^v)*16777619u;}
static void record(u32 id,struct127*p,u32 count,u32 a,u32 b){word(id);word(count);if(count){word((u32)((u8*)p-(u8*)D_800CC2D0));if(count>1)word(a);if(count>2)word(b);}word(D_800C3E78);word(D_800C3654[0]);}
static void effect(u32 id,struct127*p){u32 slot=(u32)((u8*)p-(u8*)D_800CC2D0)/0x32C;
if(id>=8&&(current->effect&1)){p->interaction_state=0;if(slot<24)D_800CC2D0[slot+1].interaction_state=D_800CC2D0[slot+1].interaction_state?0:4;}
if(id==1&&(current->effect&2))D_800C3E78=(u8)(0x80+(slot&7));
if(id==2&&(current->effect&4)){p->unk2FF=0x77;D_800C3654[0]=255;}
if(id==5&&(current->effect&8)){p->unk2FF=0x99;D_800C3E78=255;}
if(id==7){D_800C3E78=0xE1;D_800C3654[0]=0;}}
void func_15022998(s32*p){record(0,(struct127*)p,1,0,0);last=(struct127*)p;if(current->callbacks&&(*p==4||*p==27)){u32 id=*p==4?8:9;record(id,0,0,0,0);effect(id,last);}}
void func_1507E73C(struct127*p){record(1,p,1,0,0);effect(1,p);}
s32 func_150229E4(struct127*p){record(2,p,1,0,0);effect(2,p);return current->result==2?(s32)0x80000000u:(s32)current->result;}
s32 func_1502178C(struct127*p,s32 a,s32 b){record(3,p,3,(u32)a,(u32)b);return 0;}
void func_150627D4(struct127*p){record(4,p,1,0,0);}
void func_1507FEA0(struct127*p){record(5,p,1,0,0);effect(5,p);}
void func_15061B4C(void){record(6,0,0,0,0);}
void func_1504A730(void){record(7,0,0,0,0);effect(7,D_800CC2D0);}
'''
 bad=controls(body);text+='\n'.join(v.replace(F,'test_'+k)for k,v in dict(selected=body,**bad).items())
 text+='\nstatic const Fixture fixtures[]={\n'
 for c,before,after,marks,index,mode,h in rows:
  array=lambda values:'{'+','.join(str(v)+'u'for v in values)+'}'
  text+='{'+','.join(str(v)+'u'for v in(c.result,c.effect,c.callbacks,c.mode,c.seed))+','+array(before)+','+array(after)+','+array(marks)+','+','.join(str(v)+'u'for v in(index,mode,h))+'},\n'
 text+='};\n'+r'''
static u8 expected[sizeof(D_800CC2D0)]__attribute__((aligned(16)));
static int check(void(*update)(void)){u32 n,i;u8*pool=(u8*)D_800CC2D0;
for(n=0;n<sizeof(fixtures)/sizeof(fixtures[0]);n++){current=fixtures+n;
for(i=0;i<sizeof(D_800CC2D0);i++)pool[i]=(u8)(i*29+current->seed*11+0x59);
for(i=0;i<26;i++)D_800CC2D0[i].interaction_state=(s32)current->before[i];
for(i=0;i<sizeof(D_800CC2D0);i++)expected[i]=pool[i];
for(i=0;i<26;i++){((struct127*)expected)[i].interaction_state=(s32)current->after[i];((struct127*)expected)[i].unk2FF=current->marks[i];}
D_800C3E78=0xA7;D_800C3654[0]=(u8)current->mode;for(i=1;i<4;i++)D_800C3654[i]=(u8)(90+i);traceHash=2166136261u;last=D_800CC2D0;update();
if(traceHash!=current->hash||D_800C3E78!=current->indexOut||D_800C3654[0]!=current->modeOut)return 1;
for(i=0;i<sizeof(D_800CC2D0);i++)if(pool[i]!=expected[i])return 2;
for(i=1;i<4;i++)if(D_800C3654[i]!=(u8)(90+i))return 3;
}return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,k in enumerate(bad):text+='if(!check(test_'+k+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 p=o/'native.c';p.write_text(text);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=o/('native'+opt);q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stderr);reports[opt]=dict(exit=0,cases=len(rows),UBSan=True,semantic_controls=len(bad))
 return dict(profiles=reports,cases=len(rows),semantic_controls=len(bad),all_pool_bytes_and_canary_slot_checked=True,call_arguments_order_and_live_global_index_checked=True,global_aliases_guest_only=True)
