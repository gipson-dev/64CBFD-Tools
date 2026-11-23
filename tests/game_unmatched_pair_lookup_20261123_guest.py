"""Private semantic audit only: no instruction matching credit or installation."""
from dataclasses import dataclass
from pathlib import Path
import json,random,struct,sys
from tools.experiments import game_unmatched_recovery_20261123 as packet
r=packet.ROOT;o=packet.OUT/'func_15022024'
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import floating
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_texture_registration_15195dd4_objects import assemble
ELF=(r/'conker/build/conker.us.elf').read_bytes();S={n:v[1]for _,n,v,_ in symbol_rows(ELF)if n};ENTRY=0x15022024;ACTIVE=0x30000;TAGS=0x45000;RECORDS=0x50000;OUT=0x60000;MISSING=struct.unpack_from('>I',ELF,elf_slot_offset(ELF,S['D_80096A14'],4))[0]
@dataclass(frozen=True)
class Case:
 seed:int=0
 group:int=0
 actor:int=0
 gate:int=1
 count:int=3
 match:int=1
 alias:int=0
 primary:int=0x3F800000
 secondary:int=0x40000000
 phase:int=0
def cases():
 rng=random.Random(0x15022024);values=(0,0x80000000,0x3F800000,0xBF800000,0x7FC12345,0x7F800000,0xFF800000,MISSING)
 for seed in range(640):yield Case(seed=seed,group=seed&1,actor=rng.randrange(3),gate=rng.choice((0,1,1,1,2,255)),count=rng.choice((0,1,3,4)),match=rng.choice((-1,0,1,3)),alias=seed%10,primary=values[seed%8],secondary=values[seed//8%8],phase=8*(seed&1))
 for alias in range(10):
  for x,y in((MISSING,MISSING),(MISSING,0x3F800000),(0x40000000,MISSING),(0x7FC12345,0x80000000)):
   yield Case(alias=alias,primary=x,secondary=y)
def outputs(c):
 pair=(OUT,OUT+16)
 if c.alias==1:pair=(OUT,OUT)
 elif c.alias==2:pair=(OUT,OUT+4)
 elif c.alias==3:pair=(OUT+4,OUT)
 elif c.alias==4:pair=(RECORDS+max(c.match,0)*68+0x3C,OUT+16)
 elif c.alias==5:pair=(OUT,RECORDS+max(c.match,0)*68+0x3C)
 elif c.alias==6:pair=(S['D_80096A14'],OUT+16)
 elif c.alias==7:pair=(OUT,S['D_80096A14'])
 elif c.alias==8:pair=(STACK+c.phase+0xD0,STACK+c.phase+0xC8)
 elif c.alias==9:pair=(OUT,RECORDS+max(c.match,0)*68+0x40)
 return pair
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,2304)}
 for base,n in((ACTIVE,16),(TAGS,64),(RECORDS,400),(OUT-16,64),(S['D_800CC2D0'],3*0x32C),(S['D_80096A14'],8)):
  m.update({base+i:(i*29+c.seed*11+0x51)&255 for i in range(n)})
 put(m,S['D_80096A14'],MISSING)
 for group in range(2):
  m[S['D_800C35EA']+group]=c.gate;m[S['D_800C363A']+group]=c.count
  for name,value in(('D_800C35C8',ACTIVE),('D_800C35F0',TAGS),('D_800C3958',RECORDS)):put(m,S[name]+group*4,value)
 for actor in range(3):m[S['D_800CC2D0']+actor*0x32C+0x3B]=0x48+actor
 for i in range(4):
  put(m,ACTIVE+i*2,1 if i==c.match else(c.seed+i)%3,2);put(m,TAGS+i*8,2 if i==c.match else(c.seed+i)%3,2);m[TAGS+i*8+2]=0x48+c.actor if i==c.match else 0xE0+i
  put(m,RECORDS+i*68+0x3C,c.primary+i if i!=c.match else c.primary);put(m,RECORDS+i*68+0x40,c.secondary+i if i!=c.match else c.secondary)
 return m
def reference(initial,c):
 m=initial.copy();first,second=outputs(c)
 if m[S['D_800C35EA']+c.group]!=1:return m,0
 count=m[S['D_800C363A']+c.group]
 if not count:return m,0
 active=read(m,S['D_800C35C8']+c.group*4)
 for index in range(count):
  if not read(m,active+2*index,2):continue
  tag=read(m,S['D_800C35F0']+c.group*4)+index*8
  if read(m,tag,2)!=2 or m[S['D_800CC2D0']+c.actor*0x32C+0x3B]!=m[tag+2]:continue
  missing=read(m,S['D_80096A14'])
  for at in(first+4,second+4,first,second):put(m,at,0)
  record=read(m,S['D_800C3958']+c.group*4)+index*68;value=read(m,record+0x3C)
  if floating(value)!=floating(missing):
   put(m,second,value);put(m,second+4,read(m,second));record=read(m,S['D_800C3958']+c.group*4)+index*68
  value=read(m,record+0x40)
  if floating(value)!=floating(missing):put(m,first,value);put(m,first+4,read(m,first))
  return m,1
 return m,0
class Oracle(Base):
 def __init__(self,words,initial,c):super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=ENTRY,s={},arguments=(*outputs(c),c.actor,c.group))
 def record_call(self,t):
  assert t==ENTRY,('Unexpected leaf call',hex(t));a=tuple(self.arguments(4));self.calls.append((t,a));self.events.append(('CALL',t,a))
def public(m,c):return{a:b for a,b in m.items()if not STACK+c.phase-16<=a<STACK+c.phase}
def main():
 fragment=(o/'original-target-fragment.s').read_text();assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'\n.size func_15022024,.-func_15022024\n',o/'original-target.o')
 programs={label:bound_blob(*payload(o/path,'func_15022024'),S)for label,path in dict(raw='selected-final/candidate.o',retail='original-target.o').items()};visits=set();count=trace_diffs=public_trace_diffs=0
 for c in cases():
  initial=fixture(c);expected,answer=reference(initial,c);models=[]
  for label,words in programs.items():
   m=Oracle(words,initial,c);m.run();assert public(m.memory,c)==public(expected,c),(label,c,'public');assert m.r[2]==answer,(label,c,'return');assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:];assert not m.calls;models.append(m)
  visits.update(models[1].visits);trace_diffs+=models[0].trace!=models[1].trace;public_traces=[[row for row in m.trace if not STACK+c.phase-16<=row[1]<STACK+c.phase]for m in models];public_trace_diffs+=public_traces[0]!=public_traces[1];count+=1
 assert [i for i in range(91)if ENTRY+4*i not in visits]==[81]
 retail=programs['retail'];assert retail[79]>>16==0x1000
 for i,w in enumerate(retail):
  op=w>>26
  if op in(4,5,6,7,20,21,22,23)or(op==17 and(w>>21&31)==8):assert i+1+((w&65535)^32768)-32768!=81
  if op in(2,3):assert ((ENTRY+4*i+4)&0xF0000000)|(w&0x3FFFFFF)*4!=ENTRY+81*4
 assert public_trace_diffs==0
 q=dict(cases_per_stream=count,raw_and_retail_independent_public_memory_and_return_equal=True,ordered_public_access_trace_differences=public_trace_diffs,public_trace_excluded_region='incoming SP-16 through SP-1 only',retail_unexecuted_words=[81],unexecuted_word_81_statically_unreachable_from_normal_entry=True,raw_private_or_access_trace_differences=trace_diffs,sentinel_bits=f'{MISSING:08X}',source_installed=False,matching_credit=0,limits='Private semantic screen only. Raw word counts, frame and register/control schedules differ. Output overlaps, record-float aliases, guest-only sentinel-region aliases and actual caller-stack offsets are covered; no byte-exact, portable native alias, FCSR or gameplay claim.');(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
def callers():
 from dataclasses import replace
 rom=(r/'conker/conker.us.bin').read_bytes();start,end=0x1503B1F0,0x1503B22C;words=struct.unpack_from('>15I',rom,start-0x15000000+0x2D4B0);programs={label:bound_blob(*payload(o/path,'func_15022024'),S)for label,path in dict(raw='selected-final/candidate.o',retail='original-target.o').items()};count=0
 for c in list(cases())[::8]:
  c=replace(c,group=0,alias=8)
  for bypass in(0,1):
   initial=fixture(c);home=STACK+c.phase;put(initial,home+0x40,c.actor);expected,answer=reference(initial,c)if not bypass else(initial.copy(),0)
   if not bypass:put(expected,home+0xF4,0x13579BDF)
   if not bypass and answer:
    for at,value in((0x90,1),(0x94,0),(0x8C,0),(0xA0,8)):put(expected,home+at,value)
   for label,ws in programs.items():
    m=Oracle(ws,initial,c);m.code=dict(zip(range(start,end,4),words))|dict(zip(range(ENTRY,ENTRY+len(ws)*4,4),ws));m.code[end]=0;m.pc=start;m.entry=start;m.r[10]=bypass;m.r[8]=0x13579BDF;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller window did not reach its declared end')
    assert public(m.memory,c)==public(expected,c),(label,c,bypass,'caller memory');assert m.calls==([]if bypass else[(ENTRY,(*outputs(c),c.actor,0))]),(label,c,'caller arguments');assert m.r[8]==0x13579BDF
   count+=1
 q=dict(actual_caller_window_words=15,start=f'{start:08X}',end=f'{end:08X}',cases_per_stream=count,four_arguments_stack_output_pairs_skip_gate_and_boolean_result_branch=True,source_installed=False,matching_credit=0,limits='Actual bounded caller window; complete caller parent not executed.');(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
if __name__=='__main__':main();callers()
