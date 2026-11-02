"""Random positional sound: independent guest reference, wrapper and caller windows."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY,RNG,AUDIO,LOWER=0x151618BC,0x150ADA20,0x10010F88,0x10010E78
POSITION,SECOND=0x30000,0x30100
u32=lambda v:v&0xFFFFFFFF
half=lambda v:((v&65535)^32768)-32768
bits=lambda v:struct.unpack('>I',struct.pack('>f',v))[0]
floating=lambda v:struct.unpack('>f',struct.pack('>I',v))[0]
RANDOMS=tuple(range(20))+(0x7FFFFFFF,0x80000000,0x80000001,0xFFFFFFF9,0xFFFFFFFE,0xFFFFFFFF)
@dataclass(frozen=True)
class Case:
 rng:int=0
 mutation:int=0
 profile:int=0
 phase:int=0
 answer:int=0xA5B6C7D8
def cases():return [Case(*a)for a in itertools.product(RANDOMS,range(4),range(4),(0,8))]
def arguments(c,s):
 profiles=((25000,0,0,0,500,1500),(0xABCDFFFF,0x12348000,0x876543FF,0x80000001,0x87658000,0x12347FFF),(0xFFFF0000,0xFEDC7FFF,0x12340100,0xFFFFFFFF,0x7FFFFFFF,0x80000000),(0xFFFF8001,0x8000FFFF,0xFFFF0080,0x12345678,0xFFFF0001,0xFFFF8001))
 a,b,d,e,f,g=profiles[c.profile];return tuple(map(u32,(a,b,d,e,s['table']if c.profile==3 else POSITION,f,g)))
def coords(c):return ((1.75,-2.5,0.0),(32768.75,-32769.5,65535.75),(-2147483648.0,2147483520.0,-0.75),(123.5,-456.75,789.25))[c.profile]
def fixture(c,s,args=None):
 m={STACK+c.phase+i:(i*17+165)&255 for i in range(-1024,1024)}
 for base,size in ((POSITION-16,64),(SECOND-16,64),(s['table']-16,72)):m.update({base+i:(i*29+90)&255 for i in range(size)})
 for j in range(10):put(m,s['table']+4*j,u32((0x13579BDF*(j+1))^(c.rng*17)))
 for j,x in enumerate(coords(c)):put(m,POSITION+4*j,bits(x));put(m,SECOND+4*j,bits(-3.25+j*100.5))
 if c.profile==3:
  for j,x in enumerate(coords(c)):put(m,s['table']+4*j,bits(x))
 for j,a in enumerate(arguments(c,s)if args is None else args):put(m,STACK+c.phase+4*j,a)
 return m
def effect(m,c,s,home):
 if c.mutation&1:
  for j in range(10):put(m,s['table']+4*j,bits(100.25+j*7.5))
  for j in range(3):put(m,POSITION+4*j,bits(-321.75+j*700.25));put(m,SECOND+4*j,bits(65536.5+j*12.25))
 if c.mutation&2:
  for j,v in enumerate((0xFEDC8001,0x1234FFFF,0xABCD0080,0x87654321,SECOND,0xABCD8001,0xFEDC7FFF)):put(m,home+4*j,v)
def public(m,c):return{p:v for p,v in m.items()if not STACK+c.phase-1024<=p<STACK+c.phase+1024}
def reference(initial,c,s,args=None,connected=False):
 m=dict(initial);home=STACK+c.phase;a=arguments(c,s)if args is None else args
 for j,v in enumerate(a[:4]):put(m,home+j*4,v)
 choices=[read(m,s['table']+j*4)for j in range(10)]
 effect(m,c,s,home);a=[read(m,home+4*j)for j in range(7)];position=a[4]
 xyz=[u32(math.trunc(floating(read(m,position+4*j))))for j in range(3)]
 sound=(choices[c.rng%10],a[0]&65535,u32(half(a[1])),a[2]&255,a[3],*xyz,u32(half(a[5])),u32(half(a[6])))
 calls=[(s['rng'],()),(s['audio'],sound)]
 if connected:calls.append((LOWER,(0,sound[0],*sound[1:5],*(u32(half(v))for v in sound[5:]))))
 return public(m,c),calls
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None,args=None):
  self.c,self.s=c,s
  super().__init__(words,memory,c,entry=entry,s={},connected=connected,arguments=arguments(c,s)if args is None else args)
 def execute(self,word):
  op,rs,fn=word>>26,word>>21&31,word&63
  if op==17 and rs in (16,20) and fn in (13,32):
   source=word>>11&31;dest=word>>6&31
   if rs==16 and fn==13:
    v=floating(self.f[source]);assert math.isfinite(v)and -2147483648<=math.trunc(v)<=2147483647
    self.f[dest]=u32(math.trunc(v))
   elif rs==20 and fn==32:self.f[dest]=bits(float((self.f[source]^0x80000000)-0x80000000))
   else:raise AssertionError(hex(word))
   return
  return super().execute(word)
 def record_call(self,t):
  counts={self.s['rng']:0,self.s['audio']:10,LOWER:11,ENTRY:7};assert t in counts,hex(t)
  self.calls.append((t,tuple(map(u32,self.arguments(counts[t])))))
 def hook(self,t):
  if t==self.s['rng']:effect(self.memory,self.c,self.s,STACK+self.c.phase);value=self.c.rng
  else:assert t in(self.s['audio'],LOWER);value=self.c.answer
  for j in range(4):self.put(self.r[29]+4*j,0xB5000000+j,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def programs(root,output,layout,obj=None):
 o=Path(output);entry=ENTRY+layout*0x1000000;s=dict(table=(0x800A66E4,0x80107FFC,0x8020FFFC)[layout],rng=RNG,audio=AUDIO);result=[]
 for name,object_path in(('original',o/'original-func_151618BC.o'),('C',obj or o/'selected-final.o')):
  p=o/('public-layout-%d-%s'%(layout,name));p.with_suffix('.ld').write_text('SECTIONS{.text 0x%X:SUBALIGN(4){*(.text)}}\n'%entry)
  subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_151618BC','--defsym=D_800A66E4=0x%X'%s['table'],'--defsym=func_150ADA20=0x%X'%s['rng'],'--defsym=func_10010F88=0x%X'%s['audio'],'-o',str(p.with_suffix('.elf')),str(object_path)],capture_output=True,check=True)
  image=p.with_suffix('.elf').read_bytes();at=elf_slot_offset(image,entry,228);result.append(struct.unpack_from('>57I',image,at))
 assert result[0]==result[1];return entry,s,result
def state(m):return m.r,m.f,m.memory,m.trace,m.hi,m.lo,m.calls
def qualify(root,output,obj=None):
 root,output=Path(root),Path(output);seen=set();count=0
 for layout in range(3):
  entry,s,roots=programs(root,output,layout,obj)
  for c in cases():
   initial=fixture(c,s);expected,calls=reference(initial,c,s);models=[]
   for words in roots:
    m=Oracle(words,initial,c,s,entry);m.run();assert public(m.memory,c)==expected and m.calls==calls,(layout,c,m.calls,calls)
    assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24];models.append(m);seen.update(pc-layout*0x1000000 for pc in m.visits);count+=1
   assert state(models[0])==state(models[1])
 assert set(range(ENTRY,ENTRY+228,4))<=seen
 entry,s,roots=programs(root,output,0,obj);prefixes=0
 for c in (Case(),Case(rng=0xFFFFFFFF,mutation=3,profile=1),Case(rng=19,mutation=1,profile=3)):
  m=Oracle(roots[0],fixture(c,s),c,s,entry);m.run()
  for cut in range(m.all_accesses):
   pair=[]
   for words in roots:
    x=Oracle(words,fixture(c,s),c,s,entry);x.cut=cut
    try:x.run()
    except AccessBoundary:pass
    else:raise AssertionError('Ineffective access cut')
    pair.append(x)
   assert state(pair[0])==state(pair[1]);prefixes+=1
 return dict(success=True,cases=len(cases())*3,executions=count,layouts=3,covered_words=57,access_prefix_pairs=prefixes,complete_bounded_machine_and_access_state_equal=True,table_position_alias=True,copy_before_rng_and_live_position=True,all_seven_live_argument_homes=True,finite_representable_float_domain=True,portable_fault_claim=False)
def helpers(root,output,obj=None):
 root,output=Path(root),Path(output);rom=(root/'conker/conker.us.bin').read_bytes();before=(output/'before-conker_build_conker.us.elf').read_bytes();data=rom[0x10F88:0x10FFC];at=elf_slot_offset(before,AUDIO,len(data));assert before[at:at+len(data)]==data
 code=dict(zip(range(AUDIO,AUDIO+len(data),4),struct.unpack('>29I',data)));entry,s,roots=programs(root,output,0,obj);seen=set();count=0
 for c in cases()[::3]:
  initial=fixture(c,s);expected,calls=reference(initial,c,s,connected=True);pair=[]
  for words in roots:
   m=Oracle(words,initial,c,s,entry,code);m.run();assert public(m.memory,c)==expected and m.calls==calls,(c,m.calls,calls);seen.update(m.visits);pair.append(m);count+=1
  assert state(pair[0])==state(pair[1])
 assert set(code)<=seen
 return dict(success=True,cases=len(cases()[::3]),executions=count,original_wrapper_words=29,all_wrapper_words_executed=True,retained_wrapper_equals_original=True,lower_provider_stubbed=True,signed_halfword_coordinate_consumption=True)
def callers(root,output,obj=None):
 from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
 root,output=Path(root),Path(output);rom=(root/'conker/conker.us.bin').read_bytes();entry,s,roots=programs(root,output,0,obj);reports=[]
 for window,end,n in ((0x15160580,0x151605F0,9),(0x15160A38,0x15160A4C,5)):
  words=struct.unpack_from('>%dI'%n,rom,window-0x15000000+0x2D4B0);seen=set();count=0
  for c in cases()[::11]:
   home=STACK+c.phase;pos=home+0x34 if window==0x15160580 else home+0x30
   args=(16000 if window==0x15160580 else 25000,0,0,0,pos,500,1000 if window==0x15160580 else 1500)
   initial=fixture(c,s,args)
   for j,v in enumerate(coords(c)):put(initial,pos+j*4,bits(v))
   # First caller's last integer Z conversion is in this window.
   if window==0x15160580:put(initial,pos+8,bits(float(-12345)))
   expected,calls=reference(initial,c,s,args);calls=[(ENTRY,args),*calls];pair=[]
   for body in roots:
    code=dict(zip(range(ENTRY,ENTRY+228,4),body));code[end]=0;m=Oracle(words,initial,c,s,window,code,args=args)
    if window==0x15160580:m.r[10]=1000;m.r[9]=500;m.r[8]=pos;m.r[25]=u32(-12345)
    else:m.r[14]=pos;m.r[15]=500;m.r[24]=1500
    m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller endpoint not reached')
    assert m.calls==calls and public(m.memory,c)==expected,(hex(window),c,m.calls,calls);assert m.r[29]==m.before[29];pair.append(m);seen.update(m.visits);count+=1
   assert state(pair[0])==state(pair[1])
  assert set(range(window,window+n*4,4))<=seen
  reports.append(dict(window=hex(window),words=n,executions=count,cases=len(cases()[::11]),all_window_words_executed=True))
 return dict(success=True,windows=reports,original_callers=2,full_parent_claim=False,return_not_consumed_in_windows=True,actual_outgoing_stack_stores=True)
