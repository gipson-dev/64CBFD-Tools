"""Literal actor-descriptor instructions and bounded RNG/constructor contracts."""
from pathlib import Path
from dataclasses import dataclass,replace
import hashlib,itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-actor-yellow-effect-match';F='func_150E67D0';ENTRY=0x150E67D0;ACTOR=0x30000;OTHER=0x40000;MARK=0x50000;TABLE=0x80088A10
SYMS=dict(func_150ADA20=0x150ADA20,func_1513C73C=0x1513C73C)
PATTERNS=((0,0x80000000,bits(1.0)),(bits(-17.25),bits(325.75),bits(0.125)),(1,0x80000001,0x007FFFFF),(0x7F7FFFFF,0xFF7FFFFF,bits(-65536.5)),(0x7F800000,0xFF800000,0x7FC12345),(0x7F812345,0xFF812345,0x7FFFFFFF))
RANDOMS=(0,1,127,128,255,256,0x80000000,0xFFFFFFFF)
def rng_contract(raw=None):
 raw=(r/'conker/conker.us.bin').read_bytes()[0xDAED0:0xDAF18]if raw is None else raw
 expected=(0x3C048009,0xDC8485B0,0x000437FC,0x000637FA,0x00042FF8,0x0005283E,0x00C53025,0x0004233C,0x0004203E,0x00C43026,0x0006253A,0x30840FFF,0x00862026,0x3C018009,0xFC2485B0,0x0004103C,0x03E00008,0x0002103F)
 if len(raw)!=72 or struct.unpack('>18I',raw)!=expected:raise ValueError('Original RNG write contract changed')
 return dict(original_RNG_words=18,ROM='0xDAED0',VA='0x150ADA20',SHA256=hashlib.sha256(raw).hexdigest(),only_store_offset=56,only_store='sd a0,D_800885B0',seed='0x800885B0',seed_bytes=8,actor_argument_not_used=True,other_calls=False,original_instructions_executed=False,native_actor_disjoint_from_seed=True,actor_mutations_guest_stress_only=True)
@dataclass(frozen=True)
class Case:
 random:int=0
 tag:int=255
 pattern:int=0
 mutation:int=0
 phase:int=0
 actor:int=ACTOR
 result:int=0xDEADBEEF
def initialize(m,p,pattern,tag):
 for i,v in enumerate(PATTERNS[pattern]):put(m,p+0x114+4*i,v)
 m[p+12]=tag&255;m[p+1]=(tag^0x55)&255
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for p in(ACTOR,OTHER):m.update({p+i:(i*29+0x59)&255 for i in range(384)})
 initialize(m,c.actor,c.pattern,c.tag);initialize(m,OTHER,1,128);put(m,MARK,0);put(m,TABLE,ENTRY);return m
def mutate(m,c,home):
 if c.mutation&1:initialize(m,c.actor,1,c.tag^0xA5)
 if c.mutation&2:put(m,home,OTHER)
def initialized(m,p):return tuple(m[p+i]for i in(*range(7),*range(8,22),*range(24,28)))
def reference(initial,c,s=SYMS,ra=0xDEAD0000,home=None):
 m=dict(initial);home=STACK+c.phase if home is None else home;frame=home-120;d=frame+72
 put(m,frame+60,ra);put(m,home,c.actor)
 for at,value,n in((6,58,1),(0,1,4),(4,100,2),(8,0,4),(12,0,4),(16,255,1),(17,255,1),(18,0,1),(19,0,1),(20,0,1),(21,255,1),(24,0x130001,4)):put(m,d+at,value,n)
 mutate(m,c,home)
 for i in range(4):put(m,frame+4*i,0xB5000000+i)
 actor=read(m,home);x=read(m,actor+0x114);put(m,frame+16,x);y=read(m,actor+0x118);put(m,frame+20,y);z=read(m,actor+0x11C)
 for at,v in((44,0),(40,0),(36,c.random&255),(32,bits(50.)),(28,bits(50.)),(24,z)):put(m,frame+at,v)
 tagC=m[actor+12];put(m,frame+48,tagC);tag1=m[actor+1];put(m,frame+52,tag1)
 a=(d,0,0,actor+0x124,*[read(m,frame+i*4)for i in range(4,14)])
 packet=bytes(m[d+i]for i in range(40));put(m,MARK,0xB16B00B5)
 for i in range(4):put(m,frame+4*i,0xB5000000+i)
 return m,[(s['func_150ADA20'],()),(s['func_1513C73C'],a)],packet
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  self.packets=[];super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(c.actor,))
 def record_call(self,t):
  assert t in(*self.syms.values(),ENTRY),hex(t);n=0 if t==self.syms['func_150ADA20']else 14 if t==self.syms['func_1513C73C']else 1;a=tuple(self.arguments(n));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if n==14:self.packets.append(bytes(self.memory[a[0]+i]for i in range(40)))
 def hook(self,t):
  c=self.case;assert self.r[29]==STACK+c.phase-120
  assert read(self.memory,self.r[29]+60)==getattr(self,'expected_target_ra',self.before[31])
  if t==self.syms['func_150ADA20']:mutate(self.memory,c,STACK+c.phase);value=c.random
  else:assert t==self.syms['func_1513C73C'];put(self.memory,MARK,0xB16B00B5);value=c.result
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def cases():
 for a in itertools.product(RANDOMS,(0,127,128,255),range(6),range(2),(0,8),(0,0xDEADBEEF)):yield Case(*a[:5],result=a[5])
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.packets)
def verify(m,initial,c,s=SYMS):
 want,calls,packet=reference(initial,c,s,ra=m.before[31]);assert(m.memory,m.calls,m.packets)==(want,calls,[packet]),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.saved_f and m.r[2]==0
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');programs=[linked(p,'semantic-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]==programs[2];count=0;visited=set()
 for c in cases():
  initial=fixture(c);ms=[]
  for words in programs:m=Oracle(words,initial,c).run();verify(m,initial,c);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);visited.update(ms[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+216,4));prefixes=0
 for c in(Case(),Case(pattern=5,mutation=1,phase=8),Case(random=0xFFFFFFFF,mutation=3)):
  initial=fixture(c);full=Oracle(programs[0],initial,c).run()
  for cut in range(full.all_accesses):
   ms=[]
   for words in programs:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing prefix',cut))
    ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);prefixes+=1
 private=0
 for actor,mu,phase in itertools.product((ACTOR,STACK-384,STACK-320,STACK-124,STACK),(0,1,2,3),(0,8)):
  if actor==STACK and mu==1:continue
  c=Case(random=0xFFFFFFFF,actor=actor+phase if actor!=ACTOR else actor,mutation=mu,phase=phase);initial=fixture(c);ms=[]
  for words in programs:m=Oracle(words,initial,c).run();verify(m,initial,c);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);private+=1
 rebased=0
 for k,(entry,random,submit)in enumerate(((0x15001000,0x10007FF0,0x10008000),(0x1F008000,0x1F108000,0x1000FFF0),(0x1000FFF0,0x10008000,0x10007FF0))):
  s=dict(func_150ADA20=random,func_1513C73C=submit);ps=[linked(p,'rebase'+str(k)+'-'+str(i),entry,s)for i,p in enumerate(objects)];assert ps[0]==ps[1]==ps[2]
  for rng,tag,pattern,mu,phase in itertools.product((0,255,256,0xFFFFFFFF),(0,255),(0,5),range(2),(0,8)):
   c=Case(random=rng,tag=tag,pattern=pattern,mutation=mu,phase=phase);initial=fixture(c);ms=[]
   for words in ps:m=Oracle(words,initial,c,s,entry).run();verify(m,initial,c,s);ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();jal=struct.pack('>I',0x0C000000|((ENTRY>>2)&0x3FFFFFF));assert not any(rom[at:at+4]==jal for at in range(0,len(rom),4));assert[at for at in range(0,len(rom),4)if rom[at:at+4]==struct.pack('>I',ENTRY)]==[0x22D4D0]
 window=list(struct.unpack_from('>12I',rom,0x1137AC));assert window==[0x3C198009,0x0338C821,0x8F398A10,0x00C02025,0xAFA60048,0x0320F809,0,0x00023E00,0x00074603,0x01003825,0x10000001,0x8FA60048];end=0x150E632C;total=0
 for rng,tag,pattern,mu,phase in itertools.product((0,255,256,0xFFFFFFFF),(0,255),(0,5),range(2),(0,8)):
  c=Case(random=rng,tag=tag,pattern=pattern,mutation=mu,phase=phase);initial=fixture(c);home=STACK+c.phase;put(initial,home+72,c.actor);want,calls,packet=reference(initial,c,ra=0x150E6318);ms=[]
  for words in programs:
   code=dict(zip(range(ENTRY,ENTRY+216,4),words));code[end]=0;m=Oracle(window,fixture(c),c,entry=0x150E62FC,connected=code);m.r[6]=c.actor;m.r[24]=0;m.before=m.r[:];m.expected_target_ra=0x150E6318;m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing callback boundary')
   assert(m.memory,m.calls,m.packets,m.r[2],m.r[6],m.r[7])==(want,[(ENTRY,(c.actor,))]+calls,[packet],0,c.actor,0),c;ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);total+=1
 return dict(private_only=True,installed=False,matching_credit=0,cases=count,executions=count*3,covered_words=54,alignment_words=2,frame=120,guards=0,literal_full_state_equal=True,descriptor_bytes=40,initialized_descriptor_bytes=25,uninitialized_bytes_portable_claimed=False,all_fourteen_arguments_checked=True,float_payloads_bitwise_guest_checked=True,access_prefix_pairs=prefixes,rebase_layouts=3,rebase_cases=rebased,private_home_and_alias_cases=private,original_callback_windows=[dict(entry='0x150E62FC',ROM='0x1137AC',words=12,cases=total,callback_table='0x80088A10',return_consumed_as_signed_byte=True,result_zero=True,actor_reloaded_from_caller_slot=True,complete_parent_claimed=False)],helper_models_bounded=True,hardware_or_complete_parent_claimed=False)
def native_harness(selected):
 head,body=selected.split('/* Submit',1);body='/* Submit'+body
 mutants=dict(flags=body.replace('descriptor.flags = 1','descriptor.flags = 2'),kind=body.replace('descriptor.kind = 0x3A','descriptor.kind = 0x3B'),lifetime=body.replace('descriptor.lifetime = 100','descriptor.lifetime = 101'),colour=body.replace('descriptor.value10 = 255','descriptor.value10 = 254'),resource=body.replace('descriptor.resource = 0x130001','descriptor.resource = 0x130002'),axis=body.replace('position[1], position[2]','position[2], position[2]'),range=body.replace('range = 50.0f','range = 51.0f'),mask=body.replace('func_150ADA20() & 255','func_150ADA20() & 127'),result=body.replace('return 0;','return 1;'),payload=body.replace('position + 5','position + 4'),tag=body.replace('actor[0xC], actor[1]','actor[1], actor[1]'))
 assert all(v!=body for v in mutants.values())
 text=head+r'''
 typedef struct {u32 random,tag,pattern,mutation,x,y,z,outx,outy,outz,tagC,tag1;} Fixture;
 static const Fixture *current; static union{u32 words[96];u8 bytes[384];} storage;
 static u8 *actorData=storage.bytes;static s32 draws,submits,badArgs;
 static f32 asFloat(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
 static u32 asBits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
 s32 func_150ADA20(void){draws++;if(current->mutation){((f32*)(actorData+0x114))[0]=-17.25f;((f32*)(actorData+0x114))[1]=325.75f;((f32*)(actorData+0x114))[2]=0.125f;actorData[12]=(u8)(current->tag^0xA5);actorData[1]=(u8)(current->tag^0xA5^0x55);}return(s32)current->random;}
 struct210 *func_1513C73C(s32 p,u8 a,u8 b,s32 payload,f32 x,f32 y,f32 z,f32 range0,f32 range1,u8 random,u8 zeroA,s32 zeroB,u8 tagC,s32 tag1){ActorEffectDescriptor*d=(ActorEffectDescriptor*)p;submits++;
 if(d->flags!=1||d->lifetime!=100||d->kind!=58||d->value8||d->valueC||d->value10!=255||d->value11!=255||d->value12||d->value13||d->value14||d->value15!=255||d->resource!=0x130001)badArgs=1;
 if(a||b||(u8*)payload!=actorData+0x124||asBits(x)!=current->outx||asBits(y)!=current->outy||asBits(z)!=current->outz||range0!=50.f||range1!=50.f||random!=(current->random&255)||zeroA||zeroB||tagC!=current->tagC||(u32)tag1!=current->tag1)badArgs=1;
 return(struct210*)0xDEADBEEF;}
 '''
 text+='\n'.join(v.replace(F,'test_'+name)for name,v in dict(selected=body,**mutants).items());rows=[]
 # Native C argument evaluation order is unspecified. The original RNG's only
 # write is its disjoint seed; actor-mutating RNG stress stays guest-only.
 for rng,tag,pattern,mu in itertools.product(RANDOMS,(0,127,128,255),range(4),(0,)):
  c=Case(random=rng,tag=tag,pattern=pattern,mutation=mu);initial=fixture(c);want,calls,packet=reference(initial,c);a=calls[-1][1];rows.append((rng,tag,pattern,mu,*PATTERNS[pattern],*a[4:7],a[12],a[13]))
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join('{'+','.join('0x%08Xu'%x for x in row)+'}'for row in rows)+'\n};\n'
 text+=r'''
 typedef s32(*Fn)(u8*);
 static s32 check(Fn fn){s32 i,j;for(i=0;i<CASE_COUNT;i++){const Fixture*c=fixtures+i;current=c;for(j=0;j<384;j++)actorData[j]=(u8)(j*29+0x59);((f32*)(actorData+0x114))[0]=asFloat(c->x);((f32*)(actorData+0x114))[1]=asFloat(c->y);((f32*)(actorData+0x114))[2]=asFloat(c->z);actorData[12]=(u8)c->tag;actorData[1]=(u8)(c->tag^0x55);draws=submits=badArgs=0;
 if(fn(actorData)||draws!=1||submits!=1||badArgs)return 1;
 if(asBits(((f32*)(actorData+0x114))[0])!=c->outx||asBits(((f32*)(actorData+0x114))[1])!=c->outy||asBits(((f32*)(actorData+0x114))[2])!=c->outz||actorData[12]!=c->tagC||actorData[1]!=c->tag1)return 2;
 }return 0;}
 static int run(void){if(sizeof(void*)!=4||sizeof(ActorEffectDescriptor)!=40)return 90;if(check(test_selected))return 10;
 '''.replace('CASE_COUNT',str(len(rows)))
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');return text,len(rows),len(mutants)
def run_native(selected):
 text,count,controls=native_harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,cases=count,negative_controls=controls,UBSan=True)
 return dict(profiles=reports,cases=count,negative_controls=controls,signature='s32(u8*)',all_initialized_descriptor_fields_and_fourteen_arguments_checked=True,original_RNG_disjoint_seed_contract=True,actor_mutating_RNG_native_order_claimed=False,uninitialized_descriptor_bytes_claimed=False,nonfinite_float_native_claimed=False,private_home_mutations_portable_claimed=False)
