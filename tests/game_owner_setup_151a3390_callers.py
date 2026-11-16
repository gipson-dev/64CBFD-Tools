"""All three actual caller windows; preceding parent paths remain bounded."""
from dataclasses import replace
import csv,json,struct
from tools.experiments import game_owner_setup_151a3390_recovery as m
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests import game_owner_setup_151a3390_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
WINDOWS=((0x150272C8,0x54778,9,0x15029BA4),(0x1506D314,0x9A7C4,5,0x1506D328),(0x1507435C,0xA180C,5,0x15074370))

class Caller(g.Machine):
 def record_call(self,target):
  if target==g.ENTRY:
   args=tuple(self.arguments(2));self.child_calls.append(args);return
  return super().record_call(target)

def main():
 m.check_inputs();rom=(m.FROZEN/'conker/conker.us.bin').read_bytes();elf=(m.ROOT/'conker/build/conker.us.elf').read_bytes()
 providers=[]
 for row in csv.DictReader((m.FROZEN/'conker/progress.csv').open()):
  if row['version']=='us'and int(row['offset'])in g.TARGETS:
   va,n=int(row['offset']),int(row['length']);at=va-0x15000000+0x2D4B0 if va>=0x15000000 else va-0x10000000
   assert row['language']=='c'and elf[elf_slot_offset(elf,va,n):elf_slot_offset(elf,va,n)+n]==rom[at:at+n]
   providers.append(dict(name=row['function'],words=n//4,converted_and_byte_exact=True))
 assert len(providers)==5,providers
 frozen_elf=(m.FROZEN/'conker/build/conker.us.elf').read_bytes()
 streams=m.programs();visited={str(i):set()for i in range(3)};count=0;caller_status=[]
 for index,(entry,offset,n,end)in enumerate(WINDOWS):
  window=list(struct.unpack_from('>%dI'%n,rom,offset));current=elf[elf_slot_offset(elf,entry,n*4):elf_slot_offset(elf,entry,n*4)+n*4]
  assert current==frozen_elf[elf_slot_offset(frozen_elf,entry,n*4):elf_slot_offset(frozen_elf,entry,n*4)+n*4]
  caller_status.append(dict(entry=hex(entry),words=n,retail_window_matches_production=struct.pack('>%dI'%n,*window)==current,production_window_unchanged=True))
  for seed in range(128):
   c=g.Case(seed,seed&1,phase=(seed&1)*8,home_mutation=(seed>>1)&1,channel=seed if index==0 else 255)
   is_null=index==0 and seed%4==0;initial=g.fixture(c);home=g.STACK+c.phase
   for at in range(home+512,home+2048):initial[at]=(at*17+seed)&255
   g.put(initial,home+0x764,0 if is_null else g.OWNER);initial[home+0x773]=c.channel
   wanted_initial=dict(initial)
   if index==1:g.put(wanted_initial,home+0x2C,0)
   if index==2:g.put(wanted_initial,g.OWNER+0x3C,0);g.put(wanted_initial,home+0x84,0x12345678)
   if is_null:expected,calls,packets=wanted_initial,[],[]
   else:expected,calls,packets=g.reference(c,wanted_initial)
   baseline=None
   for label,words in streams.items():
    connected=dict(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words));q=Caller(window,c,entry=entry,connected=connected)
    q.memory=dict(initial);q.r[2]=g.OWNER;q.r[16]=g.OWNER;q.r[5]=c.channel;q.r[14]=0x12345678;q.child_calls=[]
    q.code[end]=0;q.code=WindowCode(q.code,q);q.code.ends=(end,)
    try:q.run()
    except WindowBoundary:pass
    else:raise AssertionError('caller window did not reach its boundary')
    assert q.child_calls==([]if is_null else[(g.OWNER,c.channel)]),(index,seed,'entry arguments',q.child_calls)
    assert(q.calls,q.packets)==(calls,packets),(index,seed,label,'provider observations')
    assert g.public(q.memory)==g.public(expected),(index,seed,label,'public memory')
    assert q.f[20:]==q.initial_fp[20:]and q.r[16]==g.OWNER
    if index==0:assert q.r[2]==1
    else:assert q.r[2]==(0x80000000+seed*0x10203+4)&0xFFFFFFFF
    state=g.signature(q)
    if baseline is None:baseline=state
    else:assert state==baseline,(index,seed,'complete caller state')
    visited[str(index)].update(pc for pc in q.visits if entry<=pc<entry+4*n)
   count+=1
 assert [len(visited[str(i)])for i in range(3)]==[9,5,5],visited
 report=dict(cases_per_stream=count,actual_caller_windows=3,window_words_visited={k:len(v)for k,v in visited.items()},caller_status=caller_status,null_owner_gate=True,byte_channel_and_ignored_return=True,full_connected_target=True,parent_paths_outside_windows_not_qualified=True,providers=providers,source_installed=m.installed(),c_match_credit=0)
 (m.OUT/'callers.json').write_text(json.dumps(report,indent=2)+'\n');m.check_inputs();return report
if __name__=='__main__':print(json.dumps(main()),flush=True)
