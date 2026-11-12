import itertools,json,struct
from tools.tests import game_scene_transition_dispatch_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
INNER=0x1501C17C; MAP=0x80084060; FLAGS=0x800BE93C; POINTER=0x800D212C
def fixture(c,mapping):
 m=g.fixture(c);m.update({g.STACK+i:(i*17+0xa5)&255 for i in range(-512,-256)})
 for base,n in ((MAP-4,12),(FLAGS-4,12),(POINTER-4,8)):m.update({base+i:(i*7+0xa3)&255 for i in range(n)})
 for i,v in enumerate(mapping):m[MAP+i]=v
 return m
class Oracle(FactoryOracle):
 def __init__(self,words,c,mapping,code):
  super().__init__(words,fixture(c,mapping),c,entry=g.ENTRY,arguments=(c.command,0xfedcba98,0xffffff80,0x13579bdf),connected=code)
  self.before_f=self.f[:]
 def record_call(self,t):
  assert t in(g.RESET,g.ADVANCE,INNER),hex(t)
  self.calls.append((t,self.r[4] if t==INNER else None))
 def hook(self,t):raise AssertionError(('unexpected helper provider',hex(t)))
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();elf=(g.root/'conker/build/conker.us.elf').read_bytes();code={}
 for addr,n in ((g.RESET,64),(INNER,52),(g.ADVANCE,16)):
  offset=addr-0x15000000+0x2d4b0;raw=rom[offset:offset+n];at=elf_slot_offset(elf,addr,n);assert elf[at:at+n]==raw,hex(addr)
  code.update(zip(range(addr,addr+n,4),struct.unpack('>%dI'%(n//4),raw)))
 words=struct.unpack_from('>74I',rom,0x49be0)
 data,fs,rs=parse_object(g.out/'candidate.o');a,n=fs['func_1501C730']['value'],fs['func_1501C730']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};lookup={v[1]:v[2][1] for v in symbol_rows(elf)};lookup['.rodata']=g.TABLE
 candidate=bound_blob(data[a:a+n],refs,{nm:lookup[nm] for es in refs.values() for _,nm in es});assert tuple(candidate)==words
 seen=set();count=0
 maps=((0,1,2,3),(3,2,1,0),(4,5,254,255),(0,0,1,255))
 for command,gate,phase,mapping in itertools.product((0,1,2,3,4,5,6,7),(0,1),(0,8),maps):
  c=g.Case(command,gate,0,phase);expected,calls=g.reference(c);initial=fixture(c,mapping)
  for addr,v in initial.items():
   if not g.STACK-512<=addr<g.STACK+256 and addr not in expected:expected[addr]=v
  for addr in range(POINTER-4,POINTER+4):expected[addr]=initial[addr]
  for x in mapping:
   if x<4:expected[FLAGS+x]=0
  if command==3 and gate==0:g.put(expected,POINTER,0)
  expected_calls=[(g.RESET,None)]+[(INNER,i) for i in range(4)]+([(g.ADVANCE,None)] if command==3 and gate==0 else [])
  for program in (words,candidate):
   m=Oracle(program,c,mapping,code).run();actual={a:v for a,v in m.memory.items() if not g.STACK-512<=a<g.STACK+256}
   assert (actual,m.calls)==(expected,expected_calls),(c,mapping,m.calls,expected_calls,[(hex(k),actual.get(k),expected.get(k)) for k in set(actual)|set(expected) if actual.get(k)!=expected.get(k)][:10])
   assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
   seen.update(m.visits)
  count+=1
 report=dict(cases=count,executions=count*2,original_helpers_bytes_equal_current_elf=True,reset_words_visited=sum(g.RESET+4*i in seen for i in range(16)),inner_words_visited=sum(INNER+4*i in seen for i in range(13)),advance_words_visited=sum(g.ADVANCE+4*i in seen for i in range(4)),all_three_helpers_executed=True,source_installed=False)
 (g.out/'connected_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
