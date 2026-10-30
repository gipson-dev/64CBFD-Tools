from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/'conker/build/game-accelerated-motion-update-match';F='func_150CCCB4';ENTRY=0x150CCCB4;TIME=0x800BE9A4
@dataclass(frozen=True)
class Case:
 time:int=0x3F800000
 pattern:int=0
 alias:int=-1
 phase:int=0
 @property
 def record(self):return 0x30000 if self.alias==-1 else TIME-self.alias

def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)};p=c.record;assert not(p<STACK+1024 and p+128>STACK-1024);m.update({p+i:(i*13+0x59)&255 for i in range(128)})
 patterns=[(0x3F800000,0xBF000000,0x40000000),(0x80000000,0,0x80000000),(1,0x007FFFFF,0x80000001),(0x7F7FFFFF,0xFF7FFFFF,0x3F800000),(0x7FC12345,0x3F800000,0xBF800000),(0x7FC12345,0x7FC54321,0x3F800000)]
 for i,off in enumerate((0x20,0x24,0x28,0x38,0x3C,0x40,0x44,0x48,0x4C,0x50,0x54,0x58,0x5C)):put(m,p+off,patterns[c.pattern][i%3])
 put(m,TIME,c.time);return m
mul=lambda a,b:bits(floating(a)*floating(b))
add=lambda a,b:bits(floating(a)+floating(b))
def reference(initial,c):
 m=dict(initial);p=c.record;acc=read(m,p+0x5C);vy=read(m,p+0x48)
 put(m,p+0x38,add(read(m,p+0x38),mul(read(m,p+0x44),read(m,TIME))))
 dt=read(m,TIME);put(m,p+0x3C,add(read(m,p+0x3C),add(mul(vy,dt),mul(mul(mul(acc,dt),dt),0x3F000000))))
 put(m,p+0x40,add(read(m,p+0x40),mul(read(m,p+0x4C),read(m,TIME))))
 put(m,p+0x48,add(vy,mul(acc,read(m,TIME))))
 for off,velocity in ((0x20,0x50),(0x24,0x54),(0x28,0x58)):put(m,p+off,add(read(m,p+off),mul(read(m,p+velocity),read(m,TIME))))
 return m
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c):super().__init__(words,memory,c,entry=ENTRY,s=dict(D_800BE9A4=TIME),arguments=(c.record,))
 def record_call(self,t):raise AssertionError(('Unexpected call',hex(t)))
 def hook(self,t):raise AssertionError(('Unexpected hook',hex(t)))
def linked(obj,label):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,dict(D_800BE9A4=TIME));assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\nD_800BE9A4 = 0x%X;\n'%(ENTRY,TIME));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))

from tools.experiments.game_four_head_lookup_match import payload
G=TIME
def view(obj):
 raw,bindings=payload(obj,F);words=list(struct.unpack('>%dI'%(len(raw)//4),raw));g={4:('P',0),0:0};f={};memory={};stores=[];global_value=('initial_global',)
 def read(addr):
  if isinstance(addr,tuple):return memory.get(addr[1],('initial_record',addr[1]))
  assert addr==G;return global_value
 def address(base,off):
  if isinstance(base,tuple):assert base[0]=='P';return ('P',(base[1]+off)&0xFFFFFFFF)
  return (base+off)&0xFFFFFFFF
 for at,w in enumerate(words):
  rel=bindings.get(at*4,[])
  if rel:
   assert len(rel)==1 and rel[0][1]=='D_800BE9A4'
   kind=rel[0][0];w=(w&0xFFFF0000)|(((G+0x8000)>>16)&65535 if kind=='R_MIPS_HI16'else G&65535)
  op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;fd=w>>6&31;fn=w&63;imm=((w&65535)^32768)-32768
  if w==0 or w==0x03E00008:continue
  if op==15:g[rt]=(w&65535)<<16
  elif op==9:g[rt]=address(g[rs],imm)
  elif op==49:f[rt]=read(address(g[rs],imm))
  elif op==57:
   addr=address(g[rs],imm);assert isinstance(addr,tuple);value=f[rt];memory[addr[1]]=value;stores.append((addr[1],value));global_value=('if_global_aliases_record_offset',addr[1],value,global_value)
  elif op==17 and rs==4:f[rd]=('bits',g[rt])
  elif op==17 and rs==16 and fn in (0,2):f[fd]=('add'if fn==0 else'mul',f[rd],f[rt])
  else:raise AssertionError((at,hex(w)))
 return dict(stores=stores,return_value=g[2],record_pointer=g[4],global_value=global_value)


from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
TIMES=(0,0x80000000,0x3F800000,0xBF800000,0x3EAAAAAB,0x42C80000,1,0x007FFFFF,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345)
FIELDS=(0x20,0x24,0x28,0x38,0x3C,0x40,0x44,0x48,0x4C,0x50,0x54,0x58,0x5C)
ALIASES=(-1,*FIELDS)
def cases():
 for args in itertools.product(TIMES,range(6),ALIASES,(0,8)):yield Case(*args)
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo)
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}
def verify(m,initial,c):assert(m.memory,m.r[2],m.calls)==(reference(initial,c),1,[]),c
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected-final.o');programs=[linked(p,'semantic-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]==programs[2];views=[view(p)for p in objects];assert views[0]==views[1]==views[2];visited=set();count=0
 for c in cases():
  initial=fixture(c);machines=[]
  for words in programs:m=Oracle(words,initial,c).run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+212,4));prefixes=0
 for c in(Case(),Case(0xBF800000,0,0x38,0),Case(0x7FC12345,5,0x48,8)):
  initial=fixture(c);full=Oracle(programs[0],initial,c).run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in programs:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing access boundary',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);prefixes+=1
 sparse=0
 for c in(Case(),Case(0xBF800000,0,0x38),Case(0x7FC12345,5,0x48)):
  keep={c.record+at+i for at in FIELDS for i in range(4)}|set(range(TIME,TIME+4));initial={a:b for a,b in fixture(c).items()if a in keep}
  for words in programs:m=Oracle(words,initial,c).run();verify(m,initial,c);sparse+=1
 rebased=0;prior=(ENTRY,TIME)
 try:
  for k,(entry,time)in enumerate(((0x15001000,0x80007FF0),(0x1F008000,0x80008000),(0x1000FFF0,0x8000FFF0))):
   globals()['ENTRY'],globals()['TIME']=entry,time;ps=[linked(p,'rebase'+str(k)+'-'+str(i))for i,p in enumerate(objects)];assert ps[0]==ps[1]==ps[2]
   for dt,pattern,alias,phase in itertools.product((0x3EAAAAAB,0x7FC12345),(0,3,5),(-1,0x38,0x48),(0,8)):
    c=Case(dt,pattern,alias,phase);initial=fixture(c)
    for words in ps:m=Oracle(words,initial,c).run();verify(m,initial,c)
    rebased+=1
 finally:globals()['ENTRY'],globals()['TIME']=prior
 rom=(r/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x22E37C)[0]==ENTRY and rom[0xFA238:0xFA240]==bytes(8);window=list(struct.unpack_from('>13I',rom,0x15F6F4));caller_count=0;skipped=0
 class Caller(Oracle):
  def __init__(self,words,memory,c,code):FactoryOracle.__init__(self,words,memory,c,entry=0x15132244,s=dict(D_800BE9A4=TIME),connected=code,arguments=(c.record,))
  def record_call(self,t):
   assert t==ENTRY;args=tuple(self.arguments(1));assert args==(self.case.record,);self.calls.append((t,args));self.events.append(('CALL',t,args))
 for dt,pattern,index,flag,phase in itertools.product((0,0x3F800000,0xBF800000,0x7FC12345),(0,3,5),(0,3),(0,1),(0,8)):
  c=Case(dt,pattern,-1,phase);initial=fixture(c);initial[c.record+0x71]=index;put(initial,0x800898BC,ENTRY);want=reference(initial,c)if index else dict(initial)
  if index:want[STACK+phase+0x23]=flag
  calls=[(ENTRY,(c.record,))]if index else[]
  for words in programs:
   code=dict(zip(range(ENTRY,ENTRY+212,4),words));code[0x15132278]=0;m=Caller(window,initial,c,code);m.r[16]=c.record;m.r[5]=flag;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(0x15132278,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing movement-dispatch boundary')
   assert(m.memory,m.r[2],m.r[5],m.calls)==(want,1 if index else 0,flag,calls)
  caller_count+=1;skipped+=not index
 report=dict(private_only=True,installed=False,matching_credit=0,cases=count,executions=count*3,compiler_words=53,covered_words=53,slot_words=55,alignment_words=2,frame=0,guards=0,insertions=0,omissions=0,literal_full_state_equal=True,ordered_symbolic_graph_equal=True,global_alias_offsets=list(FIELDS),live_timestep_after_stores=True,access_prefix_pairs=prefixes,sparse_executions=sparse,rebase_layouts=3,rebase_cases=rebased,registration_table='D_800898B0',registration_index=3,registration_ROM='0x22E37C',original_caller_windows=[dict(entry='0x15132244',ROM='0x15F6F4',words=13,cases=caller_count,index_zero_skips=skipped,result_tests_nonzero=True,earlier_gate_precondition=True,complete_parent_claimed=False)],hardware_FCSR_or_NaN_payload_or_complete_parent_claimed=False)
 return report


import sys
from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 q=sys.modules[__name__]
 F='func_150CCCB4';head=selected[:selected.index('/* Advance')].replace('extern f32 D_800BE9A4;','static f32 *nativeTime;\n#define D_800BE9A4 (*nativeTime)');body=selected[selected.index('/* Advance'):]
 x='    object->position[0] += object->velocity[0] * D_800BE9A4;\n';y='    object->position[1] += object->velocity[1] * D_800BE9A4 +\n        object->verticalAcceleration * D_800BE9A4 * D_800BE9A4 * 0.5f;\n'
 assert x+y in body
 mutants=dict(wrong_half=body.replace('0.5f','1.0f'),cached_time=body.replace('D_800BE9A4','cachedTime').replace('{','{\n    f32 cachedTime = D_800BE9A4;',1),omit_vertical_velocity=body.replace('    object->velocity[1] += object->verticalAcceleration * D_800BE9A4;\n',''),wrong_rotation_rate=body.replace('object->angularVelocity[0]','object->angularVelocity[1]'),wrong_acceleration=body.replace('object->verticalAcceleration','object->angularVelocity[2]'),wrong_return=body.replace('return 1;','return 0;'),missing_timestep_factor=body.replace('object->verticalAcceleration * D_800BE9A4 * D_800BE9A4 * 0.5f','object->verticalAcceleration * D_800BE9A4 * 0.5f'),wrong_store_order=body.replace(x+y,y+x));assert all(v!=body for v in mutants.values())
 text=head+'\n'.join(src.replace(F,'test_'+name)for name,src in dict(selected=body,**mutants).items());rows=[]
 for c in q.cases():
  if c.phase:continue
  initial=q.fixture(c);want=q.reference(initial,c);before=[q.read(initial,c.record+i*4)for i in range(32)];after=[q.read(want,c.record+i*4)for i in range(32)]
  rows.append('{0x%08Xu,%d,{%s},{%s}}'%(c.time,c.alias,','.join('0x%08Xu'%x for x in before),','.join('0x%08Xu'%x for x in after)))
 text+='\ntypedef struct {u32 time;s32 alias;u32 before[32],after[32];} Fixture;\nstatic const Fixture fixtures[]={\n'+',\n'.join(rows)+'\n};\n'
 text+=r'''
 static f32 record[32],separateTime;
 static u32 asBits(f32 x){union{u32 u;f32 f;}v;v.f=x;return v.u;}
 static f32 asFloat(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}
 static s32 nanBits(u32 x){return(x&0x7F800000u)==0x7F800000u&&(x&0x7FFFFFu)!=0;}
 static s32 output(s32 i){return i==8||i==9||i==10||i==14||i==15||i==16||i==18;}
 typedef s32(*Fn)(GeneratedF9430KinematicObject*);
 static s32 check(Fn fn){s32 n,i;for(n=0;n<CASE_COUNT;n++){
  const Fixture*c=fixtures+n;for(i=0;i<32;i++)record[i]=asFloat(c->before[i]);separateTime=asFloat(c->time);nativeTime=c->alias<0?&separateTime:record+c->alias/4;
  if(fn((GeneratedF9430KinematicObject*)record)!=1)return 1;
  for(i=0;i<32;i++){u32 a=asBits(record[i]),e=c->after[i];if(a!=e&&!(output(i)&&nanBits(a)&&nanBits(e)))return 2;}
  if(c->alias<0&&asBits(separateTime)!=c->time)return 3;
 }return 0;}
 static int run(void){if(sizeof(void*)!=4)return 90;if(check(test_selected))return 10;
 '''.replace('CASE_COUNT',str(len(rows)))
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');return text,dict(cases=len(rows),negative_controls=len(mutants),native_NaN_payload_claimed=False,native_alias_offsets=list(q.FIELDS))
