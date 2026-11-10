"""Original caller argument windows, F0 liveness and complete water/stun integration."""
import json,struct,sys
from dataclasses import replace
from pathlib import Path
from tools.experiments.game_motion_approach_1505a3a8_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_motion_approach_1505a3a8_oracle as guest
from tools.experiments import game_motion_approach_1505a3a8_match as qualify
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests import game_water_stun_150585f0_oracle as water
from tools.match_progress import load_elf_functions
WINDOWS=((0x1504EF18,4,0x1504EF20),(0x150545FC,4,0x15054604),(0x150582DC,4,0x150582E4),(0x15058630,6,0x15058640),(0x150C3600,6,0x150C3610),(0x150D7C10,4,0x150D7C18),(0x150F3C34,5,0x150F3C40))
def original(rom,entry,count):return list(struct.unpack_from('>%dI'%count,rom,entry-0x15000000+0x2D4B0))
def f0_role(w):
 op,rs,rt,fs,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
 if op in(57,61)and rt==0:return'read'
 if op in(49,53)and rt==0:return'kill'
 if op==17:
  if rs==0 and fs==0:return'read'
  if rs==4 and fs==0:return'kill'
  if rs in(16,17,20,21):
   if fs==0 or fn in(0,1,2,3,0x30,0x31,0x32,0x33,0x34,0x35,0x36,0x37,0x38,0x39,0x3A,0x3B,0x3C,0x3D,0x3E,0x3F)and rt==0:return'read'
   if w>>6&31==0 and fn<0x30:return'kill'
 return None
def return_liveness(rom,c):
 import csv
 layout=list(csv.DictReader((root/'conker/retail_layout.us.txt').open()));row=next(r for r in layout if r['function']==c['parent']);start,end=int(row['address'],16),int(row['end'],16);code=dict(zip(range(start,end,4),original(rom,start,(end-start)//4)))
 pending=[c['VA']+8];seen=set();kills=[]
 def consume(pc):
  assert pc in code,('F0 escaped parent',c['parent'],hex(pc));role=f0_role(code[pc]);assert role!='read',('original caller reads F0',c['parent'],hex(pc));return role=='kill'
 while pending:
  pc=pending.pop()
  if pc in seen:continue
  seen.add(pc)
  if consume(pc):kills.append((hex(pc),'definition'));continue
  w=code[pc];op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63
  if op in(2,3)or op==0 and fn in(8,9):
   if consume(pc+4):kills.append((hex(pc+4),'delay definition'));continue
   if op==3 or op==0 and fn==9:kills.append((hex(pc),'next call'));continue
   if op==0:
    signature=qualify.body((out/'frozen'/c['source']).read_text(),c['parent']).split('{',1)[0].strip();assert signature.startswith('void '),('F0 reaches unknown parent return',c['parent'],signature)
    kills.append((hex(pc),'known void parent return; incidental F0 remains unconsumed'));continue
   pending.append(((pc+4)&0xF0000000)|((w&0x3FFFFFF)<<2));continue
  if op in(1,4,5,6,7,20,21,22,23)or op==17 and rs==8:
   destination=pc+4+((((w&65535)^32768)-32768)*4);likely=op in(20,21,22,23)or op==1 and rt&2 or op==17 and rt&2
   delay_kill=consume(pc+4)
   if not delay_kill:pending.append(destination)
   else:kills.append((hex(pc+4),'taken-delay definition'))
   if not delay_kill or likely:pending.append(pc+8)
   else:kills.append((hex(pc+4),'fallthrough-delay definition'))
  else:pending.append(pc+4)
 assert kills
 return dict(parent=c['parent'],call=hex(c['VA']),visited_live_F0_words=len(seen),kills=kills,read_before_kill=False)
class CallerOracle(guest.Oracle):
 def record_call(self,t):
  assert t==guest.ENTRY
  actual=(self.f[12],self.r[5],self.r[6],self.r[7],self.get(self.r[29]+16,4)&255);c=self.case
  assert actual==(c.target,guest.ACTOR,c.acceleration,c.deceleration,c.magnitude),('caller ABI',self.index,actual,c)
  self.root_calls+=1;self.root_initial=dict(self.memory)
def windows(rom):
 cases=[guest.Case(),*[replace(guest.Case(),speed=speed,target=target,flags=flags,water=water)for speed,target,flags,water in ((0,0,0,0),(0xC1200000,0,0,0),(0x41200000,0xC1200000,0,0),(0x41200000,0x41A00000,1,1),(0x3F800001,0x40000000,96,0),(0x7FC12345,0,64,0),(0,0x7FC12345,0,0))]]
 runs=roots=0;seen=set()
 for index,(entry,count,call)in enumerate(WINDOWS):
  ws=original(rom,entry,count);code=dict(zip(range(entry,entry+count*4,4),ws));assert ws[(call-entry)//4]==0x0C000000|(guest.ENTRY>>2&0x3FFFFFF)
  for path in(out/'selected.o',out/'qualified-padded/game_83300.c.o',out/'retail-linked.o'):
   target=guest.words(path)
   for j,c in enumerate(cases):
    c=replace(c,phase=(j&1)*8)
    if index==1:c=replace(c,target=0,acceleration=0x3F800000,deceleration=0x3F800000,magnitude=0)
    if index==3:c=replace(c,target=0,acceleration=0x3F800000,deceleration=guest.bits(guest.rounded(7.*guest.floating(0x3DCCCCCD))),magnitude=0)
    if index==4:c=replace(c,target=0,acceleration=0x40000000,magnitude=0)
    if index==5:c=replace(c,acceleration=c.target,deceleration=0x3F000000,magnitude=1)
    if index==6:c=replace(c,magnitude=1)
    memory=guest.fixture(c);home=guest.STACK+c.phase;guest.put(memory,home+0x154,c.deceleration);memory[home+0x153]=c.magnitude;guest.put(memory,home+0x68,c.acceleration);guest.put(memory,guest.ACTOR+192,c.target)
    connected=dict(zip(range(guest.ENTRY,guest.ENTRY+548,4),target));connected[call+8]=0
    m=CallerOracle(ws,memory,c,entry=entry,connected=connected);m.code=WindowCode(m.code,m);m.code.ends=(call+8,);m.index=index;m.root_calls=0
    m.r[5]=guest.ACTOR;m.r[6]=c.acceleration;m.r[7]=c.deceleration;m.r[16]=guest.ACTOR;m.r[9]=c.magnitude;m.r[12]=c.magnitude;m.r[15]=0x9876;m.r[24]=1
    m.f[0]=c.acceleration if index==0 else c.deceleration;m.f[12]=c.target;m.f[14]=c.deceleration;m.f[6]=guest.bits(7.);m.f[10]=0x3DCCCCCD;m.before=m.r[:];m.before_f=m.f[:]
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller boundary missing')
    assert m.root_calls==1;m.initial=m.root_initial;m.before[31]=call+8;guest.check(m,c);roots+=1;runs+=1;seen.update(m.visits&set(code))
 return dict(executions=runs,target_invocations=roots,visited_original_window_words=len(seen),original_sites=7)
def integrated_water(rom):
 entry=0x150585F0;parent=original(rom,entry,170);before=(out/'frozen'/qualify.ELF).read_bytes();at=qualify.elf_slot_offset(before,entry,680);assert before[at:at+680]==struct.pack('>170I',*parent)
 original_effect=water.effect
 def effect(memory,c,kind,s):
  if kind!=0:return original_effect(memory,c,kind,s)
  scale=guest.bits(guest.rounded(memory[water.ACTOR+265]*guest.floating(water.read(memory,s['D_80099478']))))
  mc=guest.Case(target=0,acceleration=0x3F800000,deceleration=scale,magnitude=0)
  result=guest.reference(memory,mc,guest.SYMS);memory.clear();memory.update(result)
 cs=[replace(water.Case(),stun=stun,water=wet,scale_byte=scale,effects=0,timer=timer)for stun,wet,scale,timer in ((255,0,0,3),(255,1,255,3),(254,1,127,3),(2,9,64,3),(1,0,255,0),(1,1,1,0),(0,10,128,3),(2,255,7,3))]
 runs=0
 try:
  water.effect=effect
  for path in(out/'selected.o',out/'qualified-padded/game_83300.c.o',out/'retail-linked.o'):
   target=guest.words(path);connected=dict(zip(range(guest.ENTRY,guest.ENTRY+548,4),target))
   for j,c in enumerate(cs):
    c=replace(c,phase=(j&1)*8);initial=water.fixture(c)
    for n,v in zip(guest.FLOAT_GLOBALS,guest.DEFAULTS):guest.put(initial,guest.SYMS[n],v)
    initial[guest.SYMS['D_800CC27C']]=j&1
    m=water.Oracle(parent,initial,c,connected=connected);m.run();water.check(m,c);runs+=1
 finally:water.effect=original_effect
 return dict(complete_parent='func_150585F0',parent_words=170,executions=runs,actual_motion_child=True,other_providers_bounded=True)
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();audit=qualify.CALLER_AUDIT;liveness=[return_liveness(rom,c)for c in audit['callers']]
 jal=0x0C000000|(guest.ENTRY>>2&0x3FFFFFF);census={n:[p for p in range(0,len(rom)-3,4)if int.from_bytes(rom[p:p+4],'big')==word]for n,word in(('JAL',jal),('J',0x08000000|(guest.ENTRY>>2&0x3FFFFFF)),('pointer',guest.ENTRY))};assert census==audit['ROM_census']
 before=(out/'frozen'/qualify.ELF).read_bytes();after=(out/'qualified-image.elf').read_bytes()
 for entry,n in((0x150585F0,680),(0x150F34F4,3836)):
  at=qualify.elf_slot_offset(before,entry,n);assert before[at:at+n]==after[at:at+n]==rom[entry-0x15000000+0x2D4B0:entry-0x15000000+0x2D4B0+n]
 report=dict(ROM_census=census,return_liveness=liveness,caller_windows=windows(rom),integrated_water=integrated_water(rom),two_complete_C_parents_byte_exact=True,parent_declaration=qualify.caller_declaration(),full_other_parent_reconstruction=False,hardware_qualified=False)
 (out/'caller.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
