"""The genuine five-argument collision dispatch window, not its full parent."""
import itertools,json,struct
from tools.experiments import game_impact_terminal_150b8f44_screen as s
from tools.tests import game_impact_terminal_150b8f44_oracle as o
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
TABLE=0x80089974;START,POSITIVE,NEGATIVE=0x15133264,0x151332a8,0x151332c8

def run(state):
 elf=(s.FROZEN/'conker/build/conker.us.elf').read_bytes();assert struct.unpack_from('>I',elf,elf_slot_offset(elf,TABLE+4,4))[0]==o.ENTRY
 code=struct.unpack_from('>17I',state['rom'],0x160714)
 class Connected(o.Oracle):
  def record_call(self,t):
   if t==o.ENTRY:self.calls.append((t,tuple(map(o.g.u32,self.arguments(5)))))
   else:super().record_call(t)
 count=0;visited=set()
 for index,(amplitude,tile,query,classify,success,mutation,selector,phase)in enumerate(itertools.product((6.,6.000001,60.),(0,1),(0,1),(0,1),(0,1),(0,1,14,31),(0,1),(0,8))):
  flags=index%4;c=o.Case(amplitude=o.g.bits(amplitude),vertical=0,tile=tile,query=query,classify=classify,success=success,mutation=mutation,phase=phase,flags=flags,coordinate=index%3,randoms=(0xffffffff-flags,flags&1,flags>>1,0xffffff00|flags,flags&1));h=o.STACK+phase;surface=h+0x38
  for kind in('retail','raw'):
   initial=o.fixture(c,kind,h,surface);initial[o.ACTOR+0x75]=selector;o.put(initial,o.ACTOR+0x60,0x12345678);o.put(initial,TABLE,0);o.put(initial,TABLE+4,o.ENTRY)
   for off,value in((0x374,o.g.bits(2.25)),(0x378,o.g.bits(6.25)),(0x37c,o.g.bits(4.75))):o.put(initial,h+off,value)
   words=state[kind+'_words'];m=Connected(code,c,kind,initial,h,surface,entry=START,connected=dict(zip(range(o.ENTRY,o.ENTRY+4*len(words),4),words)))
   m.r[2]=selector;m.r[16]=o.ACTOR;before,fp=m.r[:],m.f[:];m.code[POSITIVE]=m.code[NEGATIVE]=0;m.code=WindowCode(m.code,m);m.code.ends=(POSITIVE,NEGATIVE)
   try:m.run();raise AssertionError('dispatch window did not stop')
   except WindowBoundary:pass
   if selector:
    public,calls,obs,answer=o.reference(initial,c,kind,h,surface)
    expected_calls=[(o.ENTRY,(o.ACTOR,surface,o.g.bits(2.25),o.g.bits(6.25),o.g.bits(4.75)))]+calls
    assert(o.public(m.memory),m.calls,m.obs,m.r[2])==(public,expected_calls,obs,answer),(kind,c,m.calls,expected_calls)
   else:assert(o.public(m.memory),m.calls,m.obs)==(o.public(initial),[],[])
   assert m.r[29]==h and m.r[16:24]==before[16:24]and m.r[28:31]==before[28:31]and m.f[20:]==fp[20:]
   visited.update(pc for pc in m.visits if START<=pc<POSITIVE)
  count+=1
 report=dict(passes=True,cases=count,programs=2,window_words=17,visited_window_words=len(visited),window='0x15133264..0x151332A8 / early return0x151332C8',table_index=1,all5_arguments_checked=True,complete_parent_not_claimed=True,providers_modeled=True,source_installed=False,c_match_credit=0)
 (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
