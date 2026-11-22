"""Actual descriptor registration and complete original/current update dispatcher."""
from pathlib import Path
from dataclasses import replace
import itertools,json,struct,sys
from tools.experiments import game_sprite_frame_update_15168870_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_sprite_frame_update_15168870_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
PARENT=0x151670C0;TABLE=0x8008B4A8;LISTS=0x800DCE50;DEPTH=0x800DD190;SLOTS=0x800DD198;SECOND=g.STATE+0x400;THIRD=g.STATE+0x800
def fixture(c,shape):
 m=g.fixture(c)
 for rec in(SECOND,THIRD):
  for i in range(-16,g.SIZE+16):m[rec+i]=m[g.STATE+i]
 for i in range(101*52):m[TABLE+i]=0
 for i in range(208):g.put(m,LISTS+4*i,0)
 for i in range(-128,128):g.put(m,g.u32(SLOTS+4*i),0)
 m[DEPTH]=2;g.put(m,TABLE+14*52,g.ENTRY)
 for rec in(g.STATE,SECOND,THIRD):g.put(m,rec+8,0)
 if shape:
  g.put(m,LISTS+14*4,g.STATE)
  if shape>=2:g.put(m,g.STATE+8,SECOND);g.put(m,LISTS+416+14*4,THIRD)
  if shape==3:g.put(m,THIRD+8,SECOND)
 return m
def reference(initial,c):
 m=dict(initial);calls=[];observations=[];h=g.STACK+c.phase-64
 for row in range(2):
  for col in range(101):
   if not g.read(m,TABLE+col*52):continue
   node=g.read(m,LISTS+416*row+4*col);m[DEPTH]=(m[DEPTH]+1)&255
   while node:
    g.put(m,SLOTS+4*((m[DEPTH]^128)-128),g.read(m,node+8));target=g.read(m,TABLE+52*col);assert target==g.ENTRY
    calls.append((target,(node,)));observations.append(g.observation(m,node))
    m,child_calls,child_observations=g.reference(m,c,home=h,record=node);calls+=child_calls;observations+=child_observations
    node=g.read(m,SLOTS+4*((m[DEPTH]^128)-128))
   m[DEPTH]=(m[DEPTH]-1)&255
 return m,calls,observations
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:
   record=self.arguments(1)[0];self.calls.append((t,(record,)));self.observations.append(g.observation(self.memory,record));self.target_home=self.r[29]
  else:super().record_call(t)
def main():
 base=out/'baseline/conker/build/conker.us.elf';old=base.read_bytes();rom=(root/'conker/conker.us.bin').read_bytes();private=(out/'image-qualification/linked.elf').read_bytes();current=(root/'conker/build/conker.us.elf').read_bytes()
 parent_bytes=rom[0x194570:0x194698];assert len(parent_bytes)==296
 for image in(old,current,private):
  at=elf_slot_offset(image,PARENT,296);assert image[at:at+296]==parent_bytes
  at=elf_slot_offset(image,TABLE+14*52,4);assert image[at:at+4]==struct.pack('>I',g.ENTRY)
 assert rom[0x230240:0x230244]==struct.pack('>I',g.ENTRY)
 symbols={n:r[1]for _,n,r,_ in symbol_rows(old)if n}
 assert symbols['D_8008CA20']-symbols['D_8008C9C8']==22*4 and symbols['D_8008CB64']-symbols['D_8008CA4C']==70*4
 parent=list(struct.unpack('>74I',parent_bytes));paths=[out/'frames-mod32/candidate.o',out/'qualified-owner/game_1944C0.c.o',out/'original-target.o'];count=0
 cases=[g.Case(position=p,speed=v,flags=f,mode=m,index=i,phase=phase)for p,v,f,m,i,phase in itertools.product((-1,256),(-1,0,1),(0,4,64),(0,1,2,8,16,32,64,65),(-1,2),(0,8))]
 for path in paths:
  connected=dict(zip(range(g.ENTRY,g.ENTRY+444,4),g.words(path)))
  for c in cases:
   for shape in(0,1,2,3):
    initial=fixture(c,shape);m=Caller(parent,initial,c,connected=connected,entry=PARENT,arguments=());m.run();want,calls,observations=reference(initial,c)
    assert(g.public(m.memory),m.calls,m.observations)==(g.public(want),calls,observations),(c,shape)
    assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:];count+=1
 controls=[];c=g.Case(mode=1);initial=fixture(c,2);expected=reference(initial,c)
 for label,modify in(('wrong-registration',lambda m:g.put(m,TABLE+14*52,0)),('missing-node-argument',lambda m:m.update({g.OTHER+8:0}))):
  memory=dict(initial)
  if label=='wrong-registration':modify(memory);words=parent
  else:
   words=list(parent);idx=next(i for i,w in enumerate(words)if w==0x02002025);words[idx]=0x00002025
  m=Caller(words,memory,c,connected=dict(zip(range(g.ENTRY,g.ENTRY+444,4),g.words(paths[0]))),entry=PARENT,arguments=())
  try:m.run();assert(m.calls,m.observations)==(expected[1],expected[2])
  except(AssertionError,KeyError):controls.append(label)
  else:raise AssertionError('Ineffective caller control: '+label)
 r=dict(cases_per_stream=count//3,streams=3,complete_parent_words=74,parent_frame=64,registration_column=14,registration_offset=0,
  actual_descriptor_pointer_ROM='0x230240',original_current_private_parent_equal=True,callback_table_words=22,texture_table_words=70,effective_controls=controls,
  saved_next_survives_contracted_cleanup=True,limits='The full update dispatcher and sprite routine are executed; callback and cleanup internals are bounded contracts, not full gameplay acceptance.',source_installed=packet.installed(),matching_credit=0)
 (out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
