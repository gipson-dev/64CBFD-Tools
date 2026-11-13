from pathlib import Path
import itertools,struct,sys
from tools.experiments.game_slot_notification_15156028_match import ROOT as root, OUT as out
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case,STACK,put,read
from tools.tests.game_node_range_walker_15169070_oracle import clamp
TARGET=0x15156028;PARENT=0x15169070;WRAPPER=0x15169040;SWAP=0x15146508;LIST=0x15169260;DIRECT=0x1516944C;CLAMP=0x15143D18;PRE=0x1516968C;RELEASE=0x1516972C;BOOK=0x151696DC;DESTROY=0x15155EF8
BASE=0x800CC2D0;DESCRIPTORS=0x8008B4A8;ROWS=0x800DCE50;DEPTH=0x800DD190;SUCCESSORS=0x800DD198;RECORDS=(0x70000,0x70200)
rom=(root/'conker/conker.us.bin').read_bytes();elf=(root/'conker/build/conker.us.elf').read_bytes()
assert struct.unpack_from('>I',rom,0x230fc4)[0]==TARGET and DESCRIPTORS+80*52+28==0x8008c504
def program(entry,n):
 data=rom[entry-0x15000000+0x2d4b0:entry-0x15000000+0x2d4b0+n*4];at=elf_slot_offset(elf,entry,n*4);assert entry in (TARGET,LIST,DIRECT) or elf[at:at+n*4]==data,hex(entry);return list(struct.unpack('>%dI'%n,data))
original={entry:program(entry,n) for entry,n in ((SWAP,17),(WRAPPER,12),(PARENT,124),(TARGET,88))}
lookup={v[1]:v[2][1]for v in symbol_rows(elf)};raw,refs=payload(out/'durable-after.o','func_15156028');draft=bound_blob(raw,refs,{n:lookup[n] for rows in refs.values() for _,n in rows});assert len(draft)==88
raw,refs=payload(out/'durable-generated.o','func_15156028');guarded=bound_blob(raw,refs,{n:lookup[n] for rows in refs.values() for _,n in rows});assert guarded==original[TARGET]
def fixture(i,j,tag,phase):
 m={STACK+k:(k*17+0xa5)&255 for k in range(-4096,1024)}
 for k in range(208):put(m,ROWS+4*k,0)
 for k in range(104):put(m,DESCRIPTORS+k*52+28,TARGET if k==80 else 0)
 for k in range(-4,8):put(m,SUCCESSORS+4*k,0)
 m[DEPTH]=255
 for row,record in enumerate(RECORDS):
  m.update({record+k:(k*13+row+3)&255 for k in range(0x40)});put(m,record+8,0);m[record+16]=tag;put(m,ROWS+row*0x1a0+80*4,record)
 for n,idx in enumerate((i,j)):
  ptr=BASE+idx*812;m.update({ptr+k:(k*7+n)&255 for k in range(0x40)});m[ptr+0x3b]=n+3
 return m,(BASE+i*812,BASE+j*812)
class Walker(FactoryOracle):
 def __init__(self,root_words,m,args,phase,connected,entry=SWAP):
  super().__init__(root_words,m,Case(phase=phase),entry=entry,arguments=args,connected=connected);self.target_calls=[]
 def execute(self,word):
  if word>>26==0 and word&63==0x26:self.r[word>>11&31]=(self.r[word>>21&31]^self.r[word>>16&31])&0xffffffff;self.r[0]=0;return
  return super().execute(word)
 def record_call(self,t):
  count={WRAPPER:2,PARENT:4,CLAMP:4,PRE:3,TARGET:3,RELEASE:1,BOOK:1,DESTROY:1}.get(t);assert count is not None,hex(t)
  args=tuple(self.arguments(count));self.calls.append((t,args))
  if t==TARGET:self.target_calls.append(args)
 def hook(self,t):
  args=self.calls[-1][1]
  if t==CLAMP:clamp(self.memory,args)
  else:assert t in (PRE,RELEASE,BOOK,DESTROY),hex(t)
  for k in range(4):self.put(self.r[29]+4*k,0xb5000000+k,4)
  for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
  self.f[:20]=[0xa5000000+k for k in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
count=0;visits=set()
for i,j,tag,phase in itertools.product((0,1,24,25),(0,1,24,25),(0,1,24,25,255),(0,8)):
 initial,args=fixture(i,j,tag,phase);models=[]
 for target in (original[TARGET],draft,guarded):
  connected={entry+4*k:w for entry,words in ((WRAPPER,original[WRAPPER]),(PARENT,original[PARENT]),(TARGET,target)) for k,w in enumerate(words)}
  machine=Walker(original[SWAP],initial,args,phase,connected).run();models.append(machine)
  wanted=tag
  if i<25 and j<25:
   if tag==i:wanted=j
   elif tag==j:wanted=i
  assert all(machine.memory[r+16]==wanted for r in RECORDS),(i,j,tag,phase,wanted)
  assert len(machine.target_calls)==2 and all(a[0]==r and a[2]==45 for a,r in zip(machine.target_calls,RECORDS)),(i,j,tag,phase,machine.target_calls)
  assert all(t!=RELEASE for t,_ in machine.calls)
  visits.update(machine.visits)
 assert [(t,a[0] if a else None)for t,a in models[0].calls]==[(t,a[0] if a else None)for t,a in models[1].calls]
 count+=1
print(count,'real swap -> wrapper -> complete dispatcher -> callback guest cases per body; descriptor 80 in both rows',flush=True)
REMOVE=0x151695F0;remove=program(REMOVE,15);removals=0
for index,tag,phase in itertools.product((0,1,24,25),(0,1,24,25,255),(0,8)):
 initial,args=fixture(index,0,tag,phase)
 for target in (original[TARGET],draft,guarded):
  connected={entry+4*k:w for entry,words in ((WRAPPER,original[WRAPPER]),(PARENT,original[PARENT]),(TARGET,target)) for k,w in enumerate(words)}
  machine=Walker(remove,initial,(args[0],0),phase,connected,entry=REMOVE).run()
  assert len(machine.target_calls)==2 and all(a[0]==r and a[2]==0 for a,r in zip(machine.target_calls,RECORDS))
  releases=[a for t,a in machine.calls if t==RELEASE];assert releases==([(r,) for r in RECORDS] if index<25 and tag==index else []),(index,tag,phase,releases)
 removals+=1
print(removals,'real removal-packet -> wrapper -> complete dispatcher -> callback guest cases per body',flush=True)
release=program(RELEASE,28);linked=0
for index,tag,phase in itertools.product((0,1,24,25),(0,1,24,25,255),(0,8)):
 initial,args=fixture(index,0,tag,phase)
 for record in RECORDS:initial[record]=80
 put(initial,0x8008B4D0+80*52,DESTROY)
 for target in (original[TARGET],draft,guarded):
  connected={entry+4*k:w for entry,words in ((WRAPPER,original[WRAPPER]),(PARENT,original[PARENT]),(TARGET,target),(RELEASE,release)) for k,w in enumerate(words)}
  machine=Walker(remove,initial,(args[0],0),phase,connected,entry=REMOVE).run()
  expected=[(r,) for r in RECORDS] if index<25 and tag==index else []
  for service in (RELEASE,BOOK,DESTROY):assert [a for t,a in machine.calls if t==service]==expected,(index,tag,phase,hex(service),machine.calls)
 linked+=1
print(linked,'real removal path with connected retail release helper and bounded bookkeeping/destructor per body',flush=True)
event=0x90000;index_list=0x91000;more=0
for i,j,tag,phase in itertools.product((0,24,25),(0,24,25),(0,24,255),(0,8)):
 initial,args=fixture(i,j,tag,phase);put(initial,event,args[0]);put(initial,event+4,args[1]);put(initial,index_list,80)
 for entry,words,root_args in ((LIST,program(LIST,123),(index_list,1,event,45)),(DIRECT,program(DIRECT,105),(80,event,45))):
  for target in (original[TARGET],draft,guarded):
   connected={TARGET+4*k:w for k,w in enumerate(target)};machine=Walker(words,initial,root_args,phase,connected,entry=entry).run()
   wanted=tag
   if i<25 and j<25:
    if tag==i:wanted=j
    elif tag==j:wanted=i
   assert all(machine.memory[r+16]==wanted for r in RECORDS),(hex(entry),i,j,tag,phase,wanted)
   assert len(machine.target_calls)==2 and all(a[0]==r and a[1]==event and a[2]==45 for a,r in zip(machine.target_calls,RECORDS))
  more+=1
print(more,'original list/direct dispatch cases per body; dispatchers remain uncredited placeholders',flush=True)
