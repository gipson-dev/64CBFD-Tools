"""All seven real call sites, branch gates, caller homes and the unused A1 float word."""
import json,struct,sys
from dataclasses import replace
from pathlib import Path
from tools.experiments.game_water_stun_150585f0_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_water_stun_150585f0_oracle as guest
from tools.experiments import game_water_stun_150585f0_match as qualify
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.match_progress import load_elf_functions
from tools.experiments.game_actor_state_tick_integration import symbol_rows
WINDOWS=(
 dict(parent='func_1504CB98',call=0x1504CE70,segments=((0x1504CE60,6),),stop=0x1504CE78,extra=0x3D4CCCCD),
 dict(parent='func_1504CB98',call=0x1504F068,segments=((0x1504F05C,5),),stop=0x1504F070,extra=0x3DCCCCCD),
 dict(parent='func_15052590',call=0x1505267C,segments=((0x1505266C,7),),stop=0x15052688,extra=0x3D4CCCCD,reject=0x15052688,gate='register12',post=13),
 dict(parent='func_150528C8',call=0x15052E18,segments=((0x15052E08,8),),stop=0x15052E34,extra=0x3D4CCCCD,reject=0x15052E28,gate='register24',restored_A0=True),
 dict(parent='func_150B1484',call=0x150B1738,segments=((0x150B14A4,5),(0x150B1738,3)),stop=0x150B1744,extra=0x3D4CCCCD,reject=0x150B14B8,gate='stun',post=14),
 dict(parent='func_150E0BE0',call=0x150E0D00,segments=((0x150E0CDC,5),(0x150E0D00,3)),stop=0x150E0D0C,extra=0x3D4CCCCD,reject=0x150E0CF0,gate='stun',post=9),
 dict(parent='func_150F34F4',call=0x150F3604,segments=((0x150F35F4,6),),stop=0x150F360C,extra=0x3E800000,reject=0x150F36AC,gate='stun'),
)
class CallerOracle(guest.Oracle):
 def record_call(self,t):
  if t==guest.ENTRY:
   assert self.r[4]==guest.ACTOR and self.r[5]==self.window['extra'],('original caller ABI',self.window,hex(self.r[4]),hex(self.r[5]));self.root_calls+=1;self.root_initial=dict(self.memory);self.root_case=replace(self.case,unused_argument=self.r[5]);return
  return super().record_call(t)
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();jal=0x0C000000|(guest.ENTRY>>2&0x3FFFFFF);jump=0x08000000|(guest.ENTRY>>2&0x3FFFFFF);census={n:[p for p in range(0,len(rom)-3,4)if int.from_bytes(rom[p:p+4],'big')==word]for n,word in(('JAL',jal),('J',jump),('pointer',guest.ENTRY))};assert census==dict(JAL=[0x7A320,0x7C518,0x7FB2C,0x802C8,0xDEBE8,0x10E1B0,0x120AB4],J=[],pointer=[])
 before=(out/'frozen'/qualify.ELF).read_bytes();after=(out/'qualified-image.elf').read_bytes();functions,_,addresses=load_elf_functions(str(out/'frozen'/qualify.ELF),'mips-linux-gnu-objdump');sizes={n:r[2]for _,n,r,_ in symbol_rows(before)}
 current=[(n,addresses[n]+i*4)for n,ws in functions.items()for i,v in enumerate(ws)if v==jal];assert current==[('func_150F34F4',0x150F3604)]
 absent={n:sizes[n]for n in sorted({w['parent']for w in WINDOWS}-{'func_150F34F4'})};assert all(n==12 for n in absent.values())
 at=qualify.elf_slot_offset(before,0x150F34F4,3836);offset=0x150F34F4-0x15000000+0x2D4B0;assert before[at:at+3836]==after[at:at+3836]==rom[offset:offset+3836]
 cases=[guest.Case(),replace(guest.Case(),stun=255),replace(guest.Case(),stun=254),replace(guest.Case(),stun=1,water=0),replace(guest.Case(),stun=1,timer=0),replace(guest.Case(),health=0,state=1),*[replace(guest.Case(),effects=e,stun=1,timer=0)for e in(1,2,4,8,15)],*[replace(guest.Case(),alias=a,stun=2,timer=0)for a in(1,2,3)]]
 runs=roots=rejections=0;seen=set();window_states=[];home_profiles=set()
 for index,w in enumerate(WINDOWS):
  code={};state=[]
  for entry,words in w['segments']:
   off=entry-0x15000000+0x2D4B0;raw=rom[off:off+words*4];code.update(zip(range(entry,entry+words*4,4),struct.unpack('>'+str(words)+'I',raw)));at=qualify.elf_slot_offset(before,entry,len(raw));assert before[at:at+len(raw)]==after[at:at+len(raw)];state.append(dict(entry=hex(entry),words=words,linked_window_retail=before[at:at+len(raw)]==raw))
  window_states.append(dict(parent=w['parent'],segments=state))
  configs=[(replace(c,phase=(j&1)*8),False)for j,c in enumerate(cases)]
  if 'gate'in w:configs.extend((replace(guest.Case(),stun=0 if w['gate']=='stun'else 2,phase=phase),True)for phase in(0,8))
  for path in(out/'selected.o',out/'qualified-padded/game_83300.c.o',out/'retail-linked.o'):
   target=guest.words(path)
   for c,skip in configs:
    connected={**dict(zip(range(guest.ENTRY,guest.ENTRY+len(target)*4,4),target)),**{end:0 for end in{w['stop'],w.get('reject',w['stop'])}}};m=CallerOracle(list(code.values())[:w['segments'][0][1]],guest.fixture(c),c,entry=w['segments'][0][0],connected=connected);m.code.update(code);m.code=WindowCode(m.code,m);m.code.ends=tuple({w['stop'],w.get('reject',w['stop'])});m.window=w;m.root_calls=0;m.root_initial=None;m.r[4]=guest.ACTOR;m.r[5]=w['extra']&0xFFFF0000;m.r[16]=guest.ACTOR;m.r[12]=1 if skip and w.get('gate')=='register12'else 0;m.r[24]=0 if skip and w.get('gate')=='register24'else 1;m.r[14]=1;m.r[11]=3;m.r[15]=10;m.before=m.r[:];m.before_f=m.f[:];m.argument_home_store=0xAFA5002C in target[:20];initial=dict(m.memory)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Original caller window did not reach its boundary')
    expected=0 if skip else 1;assert m.root_calls==expected,(index,c,skip,m.root_calls)
    if expected:
     m.initial=m.root_initial;m.before[31]=w['call']+8;guest.check(m,m.root_case)
     if w.get('post')is not None:assert m.r[w['post']]==guest.read(m.memory,guest.ACTOR+122,2)
     if w.get('restored_A0'):assert m.r[4]==guest.ACTOR
     home_profiles.add(('raw-home-store'if m.argument_home_store else'no-home-store',path.name));roots+=1
    else:
     want=dict(initial)
     if index==4:want[guest.ACTOR+128]=10
     if index==5:want[guest.ACTOR+135]=0
     assert m.memory==want and not m.calls;assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.f[20:]==m.before_f[20:];rejections+=1
    runs+=1;seen.update(m.visits&set(code))
 report=dict(executions=runs,target_invocations=roots,branch_rejections=rejections,ROM_census=census,original_call_sites=7,distinct_parents=6,original_window_states=window_states,visited_window_words=len(seen),current_stub_parents=absent,complete_unchanged_byte_exact_C_parent=dict(function='func_150F34F4',bytes=3836),current_linked_calls=[(n,hex(a))for n,a in current],unused_second_float_word=True,raw_argument_home_store_profile=True,normalized_and_retail_home_preservation=True,caller_store_reload_and_post_call_heading=True,full_parent_algorithm_replay=False,hardware_qualified=False)
 (out/'caller.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
