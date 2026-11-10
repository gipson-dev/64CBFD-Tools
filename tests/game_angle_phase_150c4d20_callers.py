"""Actual callback registration and both invocation sites, including repeats."""
import itertools,json,struct
from tools.tests import game_angle_phase_150c4d20_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
TABLE=0x80088C90;SCRIPT=0x50000
def original(rom,a,n):return struct.unpack_from('>%dI'%(n//4),rom,a-0x15000000+0x2D4B0)
def stop(m,ends):
 m.code=WindowCode(m.code,m);m.code.ends=ends
 try:m.run()
 except WindowBoundary:pass
 else:raise AssertionError('Missing original window boundary')
def registration(rom,elf,c,kind):
 memory=g.fixture(c);at=elf_slot_offset(elf,TABLE,37*12);memory.update({TABLE+i:b for i,b in enumerate(elf[at:at+37*12])});assert g.read(memory,TABLE+36*12)==g.ENTRY
 if kind==0:start,size,ends=0x1509EBBC,0x58,(0x1509ED5C,);g.put(memory,SCRIPT+8,36)
 else:start,size,ends=0x15003C94,0x54,(0x15003CE8,);g.put(memory,SCRIPT+0x14,36)
 code={a:0 for a in ends};m=g.Oracle(original(rom,start,size),memory,c,entry=start,connected=code);m.r[16]=SCRIPT if kind==0 else g.record(c);m.r[2]=g.record(c)if kind==0 else 36;m.r[8]=SCRIPT;m.r[4]=12;before=dict(m.memory);stop(m,ends)
 expected=dict(before);g.put(expected,g.record(c)+0x38,g.read(before,TABLE+36*12));g.put(expected,g.record(c)+0x78,g.read(before,TABLE+36*12+4));g.put(expected,g.record(c)+0x92,g.read(before,TABLE+36*12+8),1);assert g.public(m.memory)==g.public(expected);assert not m.calls;return m
def invoke(rom,ws,c,memory,kind):
 p=g.record(c);expected=dict(memory)
 if kind==0:start,size,end=0x15113EE0,16,0x15113EF0
 else:start,size,end=0x15113FA0,40,0x15113FC8
 code=dict(zip(range(g.ENTRY,g.ENTRY+380,4),ws));code[end]=0;m=g.Oracle(original(rom,start,size),memory,c,entry=start,connected=code);m.r[16]=p;m.r[17]=int(kind==2)
 for reg,value in((19,0xFFFF8001),(20,0x7FFF),(21,0xFFFFFFFF),(22,0xABCDEF01)):m.r[reg]=value
 if kind==2:
  for at,value,n in((0x5A,m.r[19],2),(0x5C,m.r[20],2),(0x5E,m.r[21],2),(0x80,m.r[22],4)):g.put(expected,p+at,value,n)
 before=m.r[:];expected,calls,normal=g.reference(expected,c);stop(m,(end,));assert m.calls==[(g.ENTRY,(p,))]+calls,(kind,c,m.calls,calls)
 actual=g.public(m.memory);wanted=g.public(expected)
 for a in(p,p+0x60):
  assert g.canonical(g.read(actual,a))==g.canonical(g.read(wanted,a))
  for j in range(4):actual.pop(a+j);wanted.pop(a+j)
 assert actual==wanted,(kind,c,'callback-public');assert m.r[16:24]==before[16:24]and m.r[29]==before[29]and m.r[31]==end,(kind,c,'callback-ABI');return m
def census(rom):
 pointers=[];direct=[]
 for at in range(0,len(rom)-3,4):
  w=struct.unpack_from('>I',rom,at)[0]
  if w==g.ENTRY:pointers.append(at)
  if w>>26 in(2,3)and(w&0x03FFFFFF)<<2==g.ENTRY&0x0FFFFFFF:direct.append(at)
 assert pointers==[0x22D900]and not direct
 # Both original continuations ignore V0 until a dominating new definition.
 assert original(rom,0x15113EF0,24)==(0x27DE0001,0x17D2FFEF,0x263100A0,0x0000F025,0x3C028008,0x8C427380)
 tail=original(rom,0x15113FC8,0x44);assert tail[-2:]==(0x3C028008,0x8C427380)
 assert all(not(w>>21&31==2 or w>>16&31==2)for w in tail[:-2]),'V0 consumed before overwrite'
 return dict(direct_J_JAL=0,literal_ROM_pointers=pointers,table=TABLE,entry=36,record_stride=160,callback_field=56,distinct_invocation_sites=[0x15113EE8,0x15113FC0],return_value_ignored=True,original_C_return_type_proven=False)
class TrigOracle(g.Oracle):
 def record_call(self,t):
  if t==0x150489B0:
   args=(self.r[4],);self.calls.append((t,args));self.events.append(('CALL',t,args))
  else:super().record_call(t)
def real_trig(rom,elf,programs):
 code={};seen=set();pairs=0
 for a,n in((0x150489B0,144),(g.TRIG,48)):
  data=original(rom,a,n);code.update(zip(range(a,a+n,4),data));at=elf_slot_offset(elf,a,n);assert elf[at:at+n]==struct.pack('>%dI'%len(data),*data)
 table=0x8009A220;at=elf_slot_offset(elf,table,260);pool=elf[at:at+260]
 for phase,flag in itertools.product(range(256),(0,4)):
  q=(phase-64)&255;address=0x8009A620-q*4 if q>=193 else 0x8009A020+q*4 if q>=129 else 0x8009A420-q*4 if q>=65 else table+q*4;value=struct.unpack_from('>I',pool,address-table)[0]
  if 65<=q<193:value^=0x80000000
  c=g.Case(timer=phase,ticks=0,flags=flag,result=value);memory=g.fixture(c);memory.update({table+i:b for i,b in enumerate(pool)});models=[]
  expected,calls,valid=g.reference(memory,c)
  for ws in programs:
   m=TrigOracle(ws,memory,c,connected=code);m.run();assert g.public(m.memory)==g.public(expected),(phase,flag,'real-lookup');assert m.calls==calls+[(0x150489B0,(q,))];models.append(m);seen.update(pc for pc in m.visits if 0x150489B0<=pc<0x15048A70)
  a,b=models;assert(a.memory,a.r,a.f,a.trace,a.calls)==(b.memory,b.r,b.f,b.trace,b.calls);pairs+=1
 return dict(pairs=pairs,all_256_phase_bytes=True,helper_covered_words=len(seen),actual_helper_and_65_float_pool_checked=True,audio_is_opaque_ABI_model=True)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();elf=(g.out/'frozen/conker/build/conker.us.elf').read_bytes();programs=(g.words(g.out/'selected.o',True),original(rom,g.ENTRY,380));registrations=0;pairs=0;seen=set()
 cs=[g.Case(angle=g.bits(a),timer=t,mutation=mu,flags=f)for a,t,mu,f in itertools.product((-1.,180.,400.),(0,255),(0,3),(0,4))]
 for c,reg in itertools.product(cs,(0,1)):
  registered=registration(rom,elf,c,reg);registrations+=1
  for kind in range(3):
   a,b=[invoke(rom,ws,c,dict(registered.memory),kind)for ws in programs];assert(a.memory,a.r,a.f,a.trace,a.calls)==(b.memory,b.r,b.f,b.trace,b.calls);pairs+=1;seen.update(pc for pc in a.visits if 0x15113EE0<=pc<0x15113EF0 or 0x15113FA0<=pc<0x15113FC8)
 result=dict(census=census(rom),registration_windows=registrations,callback_pairs=pairs,callback_window_covered_words=len(seen),real_trig=real_trig(rom,elf,programs),both_setters_and_both_calls_and_repeated_group_path=True,current_parent_placeholders_unchanged=True,full_parent_or_gameplay_qualified=False);(g.out/'callers.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
