"""Independent action model with exact table/packet accesses and incidental V0 state."""
import itertools,json,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
import os
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-event-dispatch-1509D780-match'
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY,TABLE,FLAG,PACKET,ACTOR,MARK=0x1509D780,0x8009F1AC,0x800D9920,0x30000,0x50000,0x70000
u32=lambda v:v&0xFFFFFFFF
signed16=lambda v:((v&65535)^32768)-32768
HELPERS={41:0x150EB8C4,39:0x150F9720,38:0x151616D0,36:0x150F6DB0,26:0x151616D0,18:0x151CD394,4:0x150E35DC,5:0x150E35DC,6:0x150E35DC,8:0x150B3DD0,9:0x150C5C9C,10:0x150C522C,19:0x151D2718,21:0x151616D0,22:0x151616D0}
LOOKUP=0x1505EEF4
COUNTS={0x150EB8C4:0,0x150F9720:1,0x151616D0:3,LOOKUP:1,0x150F6DB0:1,0x151CD394:1,0x150E35DC:1,0x150B3DD0:0,0x150C5C9C:1,0x150C522C:0,0x151D2718:1}
@dataclass(frozen=True)
class Case:
 command:int=22
 word:int=0xABCD0801
 half:int=0x8001
 byte:int=0xE1
 found:int=1
 result:int=0x12345678
 incoming:int=0x87654321
 mutation:int=0
 packet_mode:int=0
 phase:int=0
 seed:int=0
def symbols():return {'.rodata':TABLE,'jtbl_8009F1AC_game':TABLE,'jtbl_8009F1AC':TABLE,'D_800D9920':FLAG,**{'func_%08X'%a:a for a in COUNTS}}
def packet(c,s=None):
 s=s or symbols();return(PACKET,0,s['D_800D9920']-4,STACK+c.phase+8)[c.packet_mode]
def table_offsets():return[184,364,196,196,196,364,212,228,276,364,364,364,364,364,364,364,168,292,364,308,332,364,364,364,144,364,364,364,364,364,364,364,364,364,104,364,80,64,364,48]
def fixture(c,s=None,entry=ENTRY):
 s=s or symbols();m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-256,512)}
 for base,n in((PACKET,16),(ACTOR,32),(MARK,32),(s['D_800D9920']-8,24)):m.update({base+i:(i*29+c.seed*11+90)&255 for i in range(n)})
 for i,delta in enumerate(table_offsets()):put(m,s['.rodata']+4*i,entry+delta)
 p=packet(c,s)
 if p:
  for i in range(16):m.setdefault(p+i,(i*29+c.seed*11+90)&255)
  put(m,p+4,c.word)
  if c.command==19:put(m,p+6,c.half,2)
  if c.command==39:put(m,p+7,c.byte,1)
 for i in range(8):put(m,MARK+4*i,0)
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-256<=a<STACK+512}
def effect(m,c,target,args,ordinal,s=None):
 s=s or symbols();put(m,MARK,ordinal);put(m,MARK+4,target);put(m,MARK+8,args[0]if args else 0)
 if c.mutation&1 and packet(c,s):p=packet(c,s);put(m,p,read(m,p,1)^0x55,1)
 if c.mutation&2:put(m,s['D_800D9920'],0xAB,1)
 if c.mutation&4:put(m,ACTOR+4,read(m,ACTOR+4)^0x12345678)
 return ACTOR if target==s['func_1505EEF4']and c.found else 0 if target==s['func_1505EEF4']else u32(c.result+ordinal*0x10203)
def reference(initial,c,s=None):
 s=s or symbols();m=dict(initial);calls=[];value=u32(c.incoming);p=packet(c,s);cmd=u32(c.command)
 def call(address,args=()):
  nonlocal value
  target=s['func_%08X'%address];args=tuple(map(u32,args));calls.append((target,args));value=effect(m,c,target,args,len(calls),s);return value
 if cmd==2:put(m,s['D_800D9920'],0,1)
 elif cmd in(4,5,6):call(0x150E35DC,(0,))
 elif cmd in(8,10,41):call(HELPERS[cmd])
 elif cmd in(9,36):
  actor=call(LOOKUP,(read(m,p+4)&4095,))
  if actor:call(HELPERS[cmd],(actor,))
  elif cmd==9:value=0
 elif cmd==18:call(HELPERS[cmd],(read(m,p+4),))
 elif cmd==19:call(HELPERS[cmd],(signed16(read(m,p+6,2)),))
 elif cmd==39:call(HELPERS[cmd],(read(m,p+7,1),))
 elif cmd in(21,22,26,38):
  for sound in((0x23,0x24)if cmd==22 else {21:(0x20,),26:(0x26,),38:(0x29,)}[cmd]):call(0x151616D0,(sound,0x28 if cmd==22 else 0x18,0))
 return m,calls,value
class Oracle(FactoryOracle):
 def __init__(self,ws,memory,c,entry=ENTRY,s=None,connected=None):
  self.c=c;self.s=s or symbols();super().__init__(ws,memory,c,entry=entry,arguments=(u32(c.command),packet(c,self.s)),connected=connected);self.r[2]=u32(c.incoming);self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  counts={self.s['func_%08X'%a]:n for a,n in COUNTS.items()};counts[ENTRY]=2;assert t in counts,hex(t);args=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  args=self.calls[-1][1];helper_set={self.s['func_%08X'%a]for a in COUNTS};ordinal=sum(v[0]in helper_set for v in self.calls);value=effect(self.memory,self.c,t,args,ordinal,self.s)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.r[2]=value;self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def words(path,s=None):
 text,fs,rs=parse_object(path);a,n=fs['func_1509D780']['value'],fs['func_1509D780']['size'];return bound_blob(text[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n},s or symbols())
def check(m,c,s=None):
 expected,calls,value=reference(m.initial,c,s);assert m.calls==calls,(c,'calls',m.calls,calls);assert public(m.memory)==public(expected),(c,'public');assert m.r[2]==value,(c,'incidental-V0',hex(m.r[2]),hex(value));assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:],(c,'saved-ABI')
def cases():
 cs=[Case(command=cmd,found=found,mutation=mu,incoming=inc)for cmd,found,mu,inc in itertools.product(range(-2,45),(0,1),(0,7),(0,0x80000000,0xFFFFFFFF))]
 for cmd,v in itertools.product((9,18,19,36,39),(0,1,127,128,255,256,4095,4096,0x7FFF,0x8000,0xFFFF,0x7FFFFFFF,0x80000000,0xFFFFFFFF)):cs.append(Case(command=cmd,word=v,half=v,byte=v))
 for cmd in(0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x10002,0x10009,0xFFFF0029):cs.append(Case(command=cmd))
 cs.extend(Case(command=cmd,packet_mode=0 if cmd in(9,18,19,36,39)else 1)for cmd in range(2,42))
 cs.extend(Case(command=cmd,packet_mode=mode,mutation=mu)for cmd,mode,mu in itertools.product((2,9,18,19,36,39),(2,3),(0,7)))
 return[replace(c,phase=(i&1)*8,seed=i%7)for i,c in enumerate(cs)]
def main():
 cs=cases();rom=(root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>95I',rom,0xCAC30);raw=words(out/'selected.o');assert list(retail)==raw;seen=set()
 for c in cs:
  a,b=[Oracle(ws,fixture(c),c)for ws in(raw,retail)]
  for m in(a,b):m.run();check(m,c);seen.update((pc-ENTRY)//4 for pc in m.visits if ENTRY<=pc<ENTRY+380)
  assert(a.memory,a.r,a.f,a.trace,a.calls)==(b.memory,b.r,b.f,b.trace,b.calls),(c,'complete-machine')
 result=dict(cases=len(cs),executions=2*len(cs),coverage=len(seen),missing=[i for i in range(95)if i not in seen],complete_machine_and_trace_pairs=len(cs),all_40_table_slots=True,incidental_MIPS_V0_checked=True,portable_C_fallthrough_results_qualified=False,opaque_helper_effects=True);(out/'guest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
