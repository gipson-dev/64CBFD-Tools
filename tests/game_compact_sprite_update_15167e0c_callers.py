"""Actual three descriptor registrations and complete 74-word update dispatcher."""
from pathlib import Path
from dataclasses import replace
import itertools,json,struct,sys
from tools.experiments import game_compact_sprite_update_15167e0c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_compact_sprite_update_15167e0c_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
PARENT=0x151670C0;TABLE=0x8008B4A8;LISTS=0x800DCE50;DEPTH=0x800DD190;SLOTS=0x800DD198;SECOND=g.STATE+0x400;THIRD=g.STATE+0x800
REGISTRATIONS=((5,0x23006C),(59,0x230B64),(66,0x230CD0))
def fixture(c,shape):
 m=g.fixture(c)
 for rec in(SECOND,THIRD):
  for i in range(-16,g.SIZE+16):m[rec+i]=m[g.STATE+i]
 for i in range(101*52):m[TABLE+i]=0
 for i in range(208):g.put(m,LISTS+4*i,0)
 for i in range(6):g.put(m,SLOTS+4*i,0)
 m[DEPTH]=1
 for col,rom in REGISTRATIONS:g.put(m,TABLE+52*col,g.ENTRY)
 for rec in(g.STATE,SECOND,THIRD):g.put(m,rec+8,0)
 if shape:
  g.put(m,LISTS+5*4,g.STATE)
  if shape>=2:g.put(m,g.STATE+8,SECOND);g.put(m,LISTS+416+59*4,THIRD)
  if shape==3:g.put(m,LISTS+66*4,THIRD);g.put(m,THIRD+8,SECOND)
 return m
def reference(initial,c):
 m=dict(initial);calls=[];obs=[];h=g.STACK+c.phase-64
 for row in range(2):
  for col in range(101):
   target=g.read(m,TABLE+52*col)
   if not target:continue
   node=g.read(m,LISTS+416*row+4*col);m[DEPTH]=(m[DEPTH]+1)&255
   while node:
    g.put(m,SLOTS+4*g.s8(m[DEPTH]),g.read(m,node+8));assert target==g.ENTRY
    calls.append((target,(node,)));obs.append(g.observation(m,target,node))
    m,cc,oo=g.reference(m,c,home=h,record=node);calls+=cc;obs+=oo;node=g.read(m,SLOTS+4*g.s8(m[DEPTH]))
   m[DEPTH]=(m[DEPTH]-1)&255
 return m,calls,obs
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:
   node=self.arguments(1)[0];self.calls.append((t,(node,)));self.observations.append(g.observation(self.memory,t,node));self.target_home=self.r[29]
  else:super().record_call(t)
def main():
 old=(out/'baseline/conker/build/conker.us.elf').read_bytes();private=(out/'image-qualification/linked.elf').read_bytes();current=(root/'conker/build/conker.us.elf').read_bytes();rom=(root/'conker/conker.us.bin').read_bytes();parent_bytes=rom[0x194570:0x194698];assert len(parent_bytes)==296
 for image in(old,private,current):
  at=elf_slot_offset(image,PARENT,296);assert image[at:at+296]==parent_bytes
  for col,where in REGISTRATIONS:
   at=elf_slot_offset(image,TABLE+52*col,4);assert image[at:at+4]==rom[where:where+4]==struct.pack('>I',g.ENTRY)
 symbols={n:v[1]for _,n,v,_ in symbol_rows(old)if n}
 assert symbols['D_8008CA20']-symbols['D_8008C9C8']==22*4 and symbols['D_8008CA4C']-symbols['D_8008CA20']==11*4
 parent=list(struct.unpack('>74I',parent_bytes));count=0
 corpus=[g.Case(remaining=r,speed=v,mode=mode,frames=1,flags=2,index=3,completion=3)for r,v,mode in itertools.product((0,1,32767),(-1,0,1),(0,2,16,32,64,96,128,256,512))]
 for path in g.paths().values():
  connected=dict(zip(range(g.ENTRY,g.ENTRY+780,4),g.words(path)))
  for c in corpus:
   for shape in(0,1,2,3):
    initial=fixture(c,shape);m=Caller(parent,initial,c,connected=connected,entry=PARENT,arguments=());m.run();want,calls,obs=reference(initial,c)
    assert(g.public(m.memory),m.calls,m.observations)==(g.public(want),calls,obs),(c,shape)
    assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];count+=1
 controls=[];c=g.Case(remaining=0,mode=64);initial=fixture(c,2);expected=reference(initial,c)
 for label in('wrong-registration','missing-node-argument'):
  memory=dict(initial);code=list(parent)
  if label=='wrong-registration':
   for col,at in REGISTRATIONS:g.put(memory,TABLE+52*col,0)
  else:
   i=next(i for i,w in enumerate(code)if w==0x02002025);code[i]=0x00002025
  m=Caller(code,memory,c,connected=dict(zip(range(g.ENTRY,g.ENTRY+780,4),g.words(g.paths()['raw']))),entry=PARENT,arguments=())
  try:m.run();assert(g.public(m.memory),m.calls,m.observations)==(g.public(expected[0]),expected[1],expected[2])
  except(AssertionError,KeyError):controls.append(label)
  else:raise AssertionError('Ineffective caller control: '+label)
 r=dict(cases_per_stream=count//3,streams=3,complete_parent_words=74,parent_frame=64,registration_columns=[5,59,66],registration_offset=0,registration_ROM=[hex(at)for col,at in REGISTRATIONS],
  original_current_private_parent_and_registrations_equal=True,update_table_words=22,completion_table_words=11,effective_controls=controls,saved_next_survives_cleanup_and_argument_home_retargets=True,
  limits='Complete registered dispatcher and complete callee; callback, completion and cleanup internals remain bounded contracts. Other registered functions are absent from the fixture.',source_installed=packet.installed(),matching_credit=0)
 (out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
