"""Actual one-argument D_80089914[1] dispatch window and return-to-gate wiring."""
import itertools,json,struct
from tools.experiments import game_target_terminal_150b963c_screen as s
from tools.tests import game_target_terminal_150b963c_oracle as o
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
TABLE,START,END=0x80089914,0x15132278,0x151322b8

def run(state):
 elf=(s.FROZEN/'conker/build/conker.us.elf').read_bytes();assert struct.unpack_from('>I',elf,elf_slot_offset(elf,TABLE+4,4))[0]==o.ENTRY
 code=struct.unpack_from('>16I',state['rom'],0x15f728)
 class Connected(o.Oracle):
  def record_call(self,t):
   if t==o.ENTRY:self.calls.append((t,tuple(map(o.g.u32,self.arguments(1)))))
   else:super().record_call(t)
 count=0;seen=set()
 for i,(distance,speed,bit,query,success,mutation,selector,gate,phase)in enumerate(itertools.product((10.,50.,100.),(15.,20.),(0,1),(0,1),(0,1),(0,2,12,48,63),(0,1),(0,1),(0,8))):
  c=o.Case(distance=o.g.bits(distance),speed=o.g.bits(speed),random_bit=bit,query=query,success=success,mutation=mutation,phase=phase,first_mode=i%4,second_mode=(i//4)%4,resolve_first=(i//16)%2,resolve_second=(i//32)%2,flags=i%4);h=o.STACK+phase
  for kind in('retail','raw'):
   initial=o.fixture(c,kind,h);initial[o.ACTOR+0x72]=selector;o.put(initial,TABLE,0);o.put(initial,TABLE+4,o.ENTRY)
   words=state[kind+'_words'];machine=Connected(code,c,kind,initial,h,entry=START,connected=dict(zip(range(o.ENTRY,o.ENTRY+4*len(words),4),words)))
   machine.r[16]=o.ACTOR;machine.r[5]=gate;before,fp=machine.r[:],machine.f[:];machine.code[END]=0;machine.code=WindowCode(machine.code,machine);machine.code.ends=(END,)
   try:machine.run();raise AssertionError('caller window failed to stop')
   except WindowBoundary:pass
   if selector and not gate:
    public,calls,obs,answer=o.reference(initial,c,kind,h);expected=[(o.ENTRY,(o.ACTOR,))]+calls
    assert(o.public(machine.memory),machine.calls,machine.obs)==(public,expected,obs),(kind,c,machine.calls,expected)
    assert machine.r[5]==(0 if answer else 1)
   else:assert(o.public(machine.memory),machine.calls,machine.obs,machine.r[5])==(o.public(initial),[],[],gate)
   assert machine.r[14]==o.read(machine.memory,o.ACTOR+0x60)
   assert machine.r[29]==h and machine.r[16:24]==before[16:24]and machine.r[28:31]==before[28:31]and machine.f[20:]==fp[20:]
   seen.update(pc for pc in machine.visits if START<=pc<END)
  count+=1
 report=dict(passes=True,cases=count,programs=2,window_words=16,visited_window_words=len(seen),one_argument_and_return_gate=True,table_index=1,selector_zero_and_gate_skip=True,complete_parent_not_claimed=True,source_installed=False,c_match_credit=0)
 (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
