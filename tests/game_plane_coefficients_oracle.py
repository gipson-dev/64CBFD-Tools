"""Plane aggregate ABI and bounded binary32 instruction evidence, without FCSR claims."""
from pathlib import Path
from dataclasses import dataclass
import json,random,re,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_actor_classifier_candidates import sections

ENTRY=0x15049350
NAMES=('D_800CC210','D_800CC214','D_800CC218','D_800CC21C')
ADDRESSES=(0x800CC210,0x800CC214,0x800CC218,0x800CC21C)
@dataclass(frozen=True)
class Case:
 phase:int=0

def corpus():
 result=[tuple(map(bits,v)) for v in (
  (0,0,0,1,0,0,0,1,0),(1,2,3,4,5,6,7,8,9),
  (3,-7,11,-5,13,2,17,19,-23),(1,1,1,1,1,1,1,1,1),
  (1000,-2000,3000,1001,-1999,3001,1002,-1998,3002))]
 result.extend(tuple((0x80000000 if (i+pattern)%3==0 else 0) for i in range(9)) for pattern in range(3))
 rng=random.Random(0x15049350)
 for _ in range(1024):result.append(tuple((rng.getrandbits(1)<<31)|(rng.randrange(110,141)<<23)|rng.getrandbits(23) for i in range(9)))
 return result

def reference(words):
 a,b,c=[list(map(floating,words[i:i+3])) for i in (0,3,6)]
 f=lambda x:floating(bits(x))
 u=[f(a[i]-b[i]) for i in range(3)];v=[f(a[i]-c[i]) for i in range(3)]
 n=[f(f(u[1]*v[2])-f(u[2]*v[1])),f(f(-u[0]*v[2])+f(u[2]*v[0])),f(f(u[0]*v[1])-f(u[1]*v[0]))]
 d=f(f(a[2]*n[2])+f(f(n[0]*a[0])+f(n[1]*a[1])))
 return tuple(map(bits,(*n,d)))

def fixture(words,phase=0,addresses=ADDRESSES):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,768)}
 for a in addresses:
  for i in range(-4,8):m[a+i]=0xA5
 return m

class Oracle(FactoryOracle):
 def __init__(self,program,initial,args,phase=0,entry=ENTRY,connected=None):
  super().__init__(program,initial,Case(phase),entry=entry,s={},connected=connected,arguments=args)
 def execute(self,word):
  if word>>26==17 and word>>21&31==16 and word&63==7:
   self.f[word>>6&31]=self.f[word>>11&31]^0x80000000
  else:super().execute(word)
 def record_call(self,target):
  assert target==ENTRY,hex(target);self.calls.append((target,tuple(self.arguments(9))))
 def hook(self,target):raise AssertionError(('Unexpected helper',hex(target)))

def linked(obj,entry,addresses,path):
 script=path.with_suffix('.ld');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,a)for n,a in zip(NAMES,addresses)))
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_15049350','-o',str(path.with_suffix('.elf')),str(obj)],capture_output=True,check=True)
 return list(struct.unpack('>57I',sections(path.with_suffix('.elf'))['.text'][1][:228]))

def configure(root,output,obj):
 global r,o,rom,truth,raw,raw_object
 r,o,raw_object=root,output,obj;rom=(r/'conker/conker.us.bin').read_bytes()
 truth=list(struct.unpack_from('>57I',rom,0x76800));raw=linked(obj,ENTRY,ADDRESSES,o/'raw-linked');assert truth==raw

def run_suite():
 rows=corpus();seen=set();count=0
 for phase in (0,8):
  for words in rows:
   initial=fixture(words,phase);want=reference(words);pair=[]
   for program in (truth,raw):
    m=Oracle(program,initial,words,phase);m.run();pair.append(m);seen.update(m.visits)
    assert tuple(read(m.memory,a)for a in ADDRESSES)==want,(words,want,[read(m.memory,a)for a in ADDRESSES])
    assert m.r[29]==STACK+phase and not m.calls
    assert all(m.r[k]==m.before[k]for k in (*range(16,24),28,30,31))
    assert m.f[20:]==m.saved_f
    assert [t[1]for t in m.trace if t[0]=='W'and t[1]in ADDRESSES]==list(ADDRESSES)
    assert all(v==initial[a]for a,v in m.memory.items()if not STACK-256<=a<STACK+768 and not any(p<=a<p+4 for p in ADDRESSES))
   assert pair[0].trace==pair[1].trace and pair[0].memory==pair[1].memory
   count+=1
 # Special values establish class behavior in this bounded model, not hardware NaN payloads.
 special=0
 for value in (1,0x80000001,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345):
  args=list(rows[2]);args[0]=value;pair=[]
  for program in (truth,raw):
   m=Oracle(program,fixture(args),args);m.run();pair.append(tuple(read(m.memory,a)for a in ADDRESSES))
  assert pair[0]==pair[1];special+=1
 return dict(root_cases=count,root_executions=count*2,retail_reachable_words=len(seen&set(range(ENTRY,ENTRY+228,4))),all_public_stores_ordered=True,frame=56,alignment_words_not_executed=3,callee_saved_GPR_FPR_and_SP_preserved=True,special_value_model_cases=special,hardware_FCSR_denormal_trap_and_NaN_payload_claimed=False)

def run_callers():
 windows=[];count=0
 files=[('conker/asm/nonmatchings/game_36680/func_1500B3B0.s',0x1500B558),('conker/asm/nonmatchings/game_83300/func_15059C84.s',0x1505A02C),('conker/asm/111670.s',0x150E4F78),('conker/asm/111670.s',0x150E5958)]
 for filename,jal in files:
  text=(r/filename).read_text();entries={int(a,16):int(w,16)for a,w in re.findall(r'/\*\s*\w+\s+([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{8})\s*\*/',text)}
  entry=jal-60;program=[entries[a]for a in range(entry,jal+8,4)]
  assert program[0]>>26==9 and program[0]>>21&31==29
  offset=program[0]&65535;offset=offset if offset<32768 else offset-65536
  windows.append(dict(entry=hex(entry),JAL=hex(jal),source_stack_offset=offset,static_words=len(program)))
  for phase in (0,8):
   for args in corpus()[:8]:
    initial=fixture(args,phase);home=STACK+phase
    for i,value in enumerate(args):put(initial,home+offset+i*4,value)
    pair=[]
    for code in (truth,raw):
     connected=dict(zip(range(ENTRY,ENTRY+228,4),code));connected[jal+8]=0;m=Oracle(program,initial,(0xBAD00000,),phase,entry,connected)
     m.f[:20]=[0x3F000000+i for i in range(20)]
     m.code=WindowCode(m.code,m);m.code.ends=(jal+8,)
     try:m.run()
     except WindowBoundary:pass
     else:raise AssertionError('Caller boundary failed')
     assert m.calls==[(ENTRY,args)],m.calls
     assert tuple(read(m.memory,a)for a in ADDRESSES)==reference(args)
     assert tuple(read(m.memory,home+offset+i*4)for i in range(9))==args
     pair.append((m.memory,m.calls))
    assert pair[0]==pair[1];count+=1
 return dict(caller_windows=windows,caller_cases=count,caller_executions=count*2,by_value_aggregate_bytes=36,first_four_words_GPR_remaining_five_stack=True,FPR_argument_poison_ignored=True,caller_scope='original copy loop, argument loads, JAL delay slot and entire plane helper; stops on helper return')

def return_liveness():
 """Explore original continuations until overwrite, next call or caller return."""
 files=[('conker/asm/nonmatchings/game_36680/func_1500B3B0.s',0x1500B558),('conker/asm/nonmatchings/game_83300/func_15059C84.s',0x1505A02C),('conker/asm/111670.s',0x150E4F78),('conker/asm/111670.s',0x150E5958)]
 reports=[]
 for filename,jal in files:
  records={int(a,16):(int(w,16),mnemonic,operands)for a,w,mnemonic,operands in re.findall(r'/\*\s*\w+\s+([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{8})\s*\*/[ \t]+(\S+)[ \t]*([^\n]*)',(r/filename).read_text())}
  def visit(pc,alive,table):
   word,mnemonic,operands=table[pc];regs=re.findall(r'\$(\w+)',operands)
   store=mnemonic in ('sw','sh','sb','swc1','sdc1','beq','bne','beql','bnel','bltz','bgez','bgtz','blez','bgezl','bltzl','jr','jalr') or mnemonic.startswith('c.')
   dest=regs[0] if regs and not store else None
   # These transfers write the first register operand, so source registers remain reads.
   reads=regs if store else regs[1:]
   assert not set(reads)&set(alive),('Plane return consumed',hex(pc),mnemonic,operands,alive)
   return tuple(x for x in alive if x!=dest)
  def explore(table):
   todo=[(jal+8,('v0','f0'))];seen=set();terminals=0
   while todo:
    pc,alive=todo.pop()
    if not alive or (pc,alive) in seen:continue
    seen.add((pc,alive));word,mnemonic,operands=table[pc];alive=visit(pc,alive,table)
    op=word>>26;fn=word&63
    if op==3 or op==0 and fn==9:
     visit(pc+4,alive,table);terminals+=1;continue
    if op==0 and fn==8:
     visit(pc+4,alive,table);terminals+=1;continue
    if op==2:
     alive=visit(pc+4,alive,table);todo.append((((pc+4)&0xF0000000)|((word&0x3FFFFFF)<<2),alive));continue
    if op in (1,4,5,6,7,20,21,22,23) or op==17 and word>>21&31==8:
     offset=((word&65535)^32768)-32768;delayed=visit(pc+4,alive,table)
     todo.append((pc+4+4*offset,delayed))
     likely=op in (20,21,22,23) or op==1 and word>>16&31 in (2,3) or op==17 and bool(word>>16&2)
     todo.append((pc+8,alive if likely else delayed));continue
    todo.append((pc+4,alive))
   return dict(explored_states=len(seen),call_or_return_boundaries=terminals)
  result=explore(records)
  for mnemonic,operands in [('sw','$v0, 0($sp)'),('swc1','$f0, 0($sp)')]:
   bad=dict(records);bad[jal+8]=(records[jal+8][0],mnemonic,operands)
   try:explore(bad)
   except AssertionError as error:assert 'Plane return consumed' in str(error)
   else:raise AssertionError('Ineffective return-liveness control')
  reports.append(dict(call=hex(jal),**result))
 return dict(callers=reports,no_V0_or_F0_read_before_overwrite_next_call_or_caller_return=True,effective_negative_controls=8,does_not_claim_complete_parent_runtime_execution=True)

def run_rebases_and_prefixes():
 executions=prefixes=aliases=0
 profiles=[(ENTRY,ADDRESSES),(0x1ABC0000,(0x31008000,0x41007FFC,0x5100FFFC,0x61000000)),(0x151FFFF0,(0x3200FFFC,0x42008000,0x52000000,0x62007FFC))]
 for number,(entry,addresses) in enumerate(profiles):
  pair=[linked(obj,entry,addresses,o/('rebase-%d-%s'%(number,label)))for label,obj in [('raw',raw_object),('retail',r/'conker/build/game-plane-coefficients-15049350-match/original-func_15049350.o')]]
  assert pair[0]==pair[1]
  for args in corpus()[:8]:
   for program in pair:
    m=Oracle(program,fixture(args,addresses=addresses),args,entry=entry);m.run();assert tuple(read(m.memory,a)for a in addresses)==reference(args);executions+=1
 for args in corpus()[:3]:
  complete=Oracle(truth,fixture(args),args);complete.run()
  for cut in range(len(complete.trace)):
   pair=[]
   for program in (truth,raw):
    m=Oracle(program,fixture(args),args);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Prefix cut did not fire')
    pair.append((m.trace,m.memory,m.r,m.f))
   assert pair[0]==pair[1];prefixes+=1
 # Guest-only coefficient aliases, including incoming homes and shared output address.
 for addresses in ((STACK,STACK+4,STACK+8,STACK+12),(0x30000,)*4):
  pair=[linked(obj,ENTRY,addresses,o/('alias-%d-%s'%(aliases,label)))for label,obj in [('raw',raw_object),('retail',r/'conker/build/game-plane-coefficients-15049350-match/original-func_15049350.o')]]
  args=corpus()[2];models=[]
  for program in pair:
   m=Oracle(program,fixture(args,addresses=addresses),args);m.run();models.append((m.memory,m.trace))
  assert models[0]==models[1];aliases+=1
 return dict(rebase_profiles=3,rebase_executions=executions,independent_signed_low16_carries=True,fired_prefix_cases=prefixes,guest_output_alias_cases=aliases,portable_C_fault_or_alias_claimed=False)
