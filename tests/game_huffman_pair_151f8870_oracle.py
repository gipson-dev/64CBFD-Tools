"""Independent fast-table/tree model for the original custom decoder protocol."""
from dataclasses import dataclass,replace
from pathlib import Path
import csv,itertools,json,os,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_phase_lookup_150a76f0_oracle import arithmetic,ArithmeticFault
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_point_transform_match import put
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments import game_huffman_pair_151f8870_restoration as source

u32=lambda n:n&0xffffffff
signed8=lambda n:((n&255)^128)-128
RETURN=0xdead0000
@dataclass(frozen=True)
class Case:
 counter:int=0
 bank:int=0
 cursor:int=0x30003
 table:int=0x60000
 tree:int=0x90001
 look:int=0
 length:int=1
 packed:int=0
 depth:int=0
 pattern:int=0
 first:int=127
 second:int=128
 phase:int=0

def fixture(c):
 m={c.cursor+i:(i*37+0xa5)&255 for i in range(16)}
 shift=8-(c.counter&7);word=(c.look<<shift)|((0xaaaa^c.packed)&((1<<shift)-1))
 m[c.cursor]=(word>>8)&255;m[c.cursor+1]=word&255
 if c.depth:
  for i in range(c.depth):
   offset=(c.counter&7)+i;at=c.cursor+offset//8;bit=(c.pattern>>(i%16))&1
   m[at]=(m[at]&~(0x80>>(offset&7)))|(bit<<(7-(offset&7)))
 index=(((m[c.cursor]<<8)|m[c.cursor+1])>>shift)&255
 m[u32(c.table+0x2200+u32(c.bank<<8)+index)]=0 if c.depth else c.length
 m[u32(c.table+u32(c.bank<<8)+index)]=c.packed
 if c.depth:
  node=c.tree
  for i in range(c.depth):
   bit=(c.pattern>>(i%16))&1;m[node]=1;m[node+1]=2;node+=4*(bit+1)
   m[node+2]=255 if i+1<c.depth else c.first&255;m[node+3]=c.second&255
 return m

def reference(c,m):
 """Model table indexing, cursor consumption and signed leaf payloads."""
 offset=c.counter&7;word=(m[c.cursor]<<8)|m[c.cursor+1];index=(word>>(8-offset))&255
 bank=u32(c.bank<<8);slot=arithmetic(bank,index);table=arithmetic(c.table,0x2200)
 length=m[arithmetic(slot,table)]
 if length:
  count=arithmetic(c.counter,length);cursor=arithmetic(c.cursor,(offset+length)//8)
  packed=m[arithmetic(slot,c.table)]
  return packed&15,packed>>4,cursor,count
 cursor=c.cursor;count=c.counter;node=c.tree
 for _ in range(256):
  bit=(m[cursor]>>(7-(count&7)))&1
  node=arithmetic(node,m[node+bit]*4)
  if count&7==7:cursor=arithmetic(cursor,1);m[cursor] # Retail prefetches before leaf test.
  count=arithmetic(count,1);first=signed8(m[node+2])
  if first!=-1:return u32(first),u32(signed8(m[node+3])),cursor,count
 raise AssertionError('Independent tree depth exceeded')

class Oracle(FactoryOracle):
 def __init__(self,words,initial,c,entry=source.ENTRY,connected=None):
  super().__init__(words,initial,c,entry=entry,arguments=(),connected=connected)
  for i,v in {4:c.cursor,6:c.bank,8:c.counter,16:c.tree,21:c.table,31:RETURN}.items():self.r[i]=u32(v)
  self.before=self.r[:];self.saved_f=self.f[20:];self.initial_f=self.f[:]
 def execute(self,w):
  op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
  if op==0 and fn in (32,34):self.r[rd]=arithmetic(self.r[rs],self.r[rt],fn==34)
  elif op==0 and fn==6:self.r[rd]=self.r[rt]>>(self.r[rs]&31)
  elif op==8:self.r[rt]=arithmetic(self.r[rs],((w&65535)^32768)-32768)
  else:return super().execute(w)
  self.r[0]=0
 def record_call(self,target):
  assert target==source.ENTRY,hex(target);self.calls.append((target,()))
 def hook(self,target):raise AssertionError('No external providers')

def check(machine,initial,c,caller=0):
 expected=reference(c,initial)
 assert (machine.r[2],machine.r[9],machine.r[4],machine.r[8])==expected,c
 allowed={2,4,*range(8,16)};memory=dict(initial)
 if caller==1:allowed|={22,31};assert machine.r[22]==expected[1]
 if caller==2:
  allowed|={31};value=expected[0]
  for i in range(4):put(memory,0xb0000+i*2,(value>>(3-i))&1,2)
 assert machine.memory==memory and machine.f==machine.initial_f,c
 assert all(machine.r[i]==machine.before[i] for i in range(32) if i not in allowed),c
 assert len(machine.calls)==int(bool(caller))

def corpus():
 for offset,look,bank in itertools.product(range(8),range(256),(0,1,33)):
  yield Case(counter=0x100+offset,look=look,bank=bank,length=look%17+1,packed=look)
 for length in range(1,256):yield Case(counter=7,look=0x83,length=length,packed=(length*29)&255)
 for offset,depth,pattern in itertools.product(range(8),range(1,26),(0,0xffff,0xaaaa,0x593c)):
  yield Case(counter=offset,depth=depth,pattern=pattern,first=(127,128,0,254)[pattern%4],second=pattern&255)
 for first in range(255):yield Case(counter=7,depth=9,pattern=first,first=first,second=255-first)
 for table,counter,depth in itertools.product((0x80007ff0,0xffffdd00),(0,7,0xffffff00),(0,17)):
  yield Case(table=table,counter=counter,depth=depth,pattern=0x593c,look=255,packed=255)

def main():
 root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/source.BUILD
 programs=[list(struct.unpack('>47I',payload(out/f,source.FUNCTION)[0])) for f in ('retail.o','selected.o','guarded.o')]
 assert programs[0]==programs[1]==programs[2];seen=set();cases=0;sample=[]
 for c in corpus():
  initial=fixture(c)
  for words in programs:
   machine=Oracle(words,initial,c);machine.run();check(machine,initial,c);seen.update(machine.visits)
  if cases%509==0:sample.append(c)
  cases+=1
 assert len(seen)==47
 prefixes=0
 for c in (Case(counter=7,look=255,length=255,packed=0xb7),Case(counter=7,depth=25,pattern=0x593c)):
  initial=fixture(c);full=Oracle(programs[0],initial,c);full.run()
  for cut in range(full.all_accesses):
   states=[]
   for words in programs:
    machine=Oracle(words,initial,c);machine.cut=cut
    try:machine.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access cut did not fire')
    states.append((machine.r,machine.f,machine.memory,machine.trace,machine.current_pc,machine.delay_of))
   assert states[0]==states[1]==states[2];prefixes+=1
 faults=0
 for c in (Case(counter=0x7fffffff,length=1),Case(counter=0x7fffffff,depth=1),Case(table=0x7ffff000),Case(bank=0x7fffff),Case(cursor=0x7fffffff,counter=7)):
  initial=fixture(c)
  try:reference(c,initial)
  except ArithmeticFault:pass
  else:raise AssertionError(('Arithmetic control did not overflow',c))
  states=[]
  for words in programs:
   machine=Oracle(words,initial,c)
   try:machine.run()
   except ArithmeticFault:pass
   else:raise AssertionError('Retail overflow was lost')
   states.append((machine.r,machine.f,machine.memory,machine.trace))
  assert states[0]==states[1]==states[2];faults+=1
 rom=(root/'conker/conker.us.bin').read_bytes();callers=0
 windows=((0x151f8a14,4,0x151f8a3c,1),(0x151f8bd4,13,0x151f8c08,2))
 for (entry,n,end,kind),c in itertools.product(windows,sample+[Case(counter=7,depth=25,pattern=0xaaaa)]):
  initial=fixture(c)
  if kind==2:
   for i in range(8):initial[0xb0000+i]=0xa5
  window=struct.unpack_from('>%dI'%n,rom,entry-0x15000000+0x2d4b0)
  for words in programs:
   connected=dict(zip(range(source.ENTRY,source.ENTRY+188,4),words));connected[end]=0
   machine=Oracle(window,initial,c,entry=entry,connected=connected);machine.r[17]=0;machine.r[19]=0xb0000;machine.before=machine.r[:]
   machine.code=WindowCode(machine.code,machine);machine.code.ends=(end,)
   try:machine.run()
   except WindowBoundary:pass
   else:raise AssertionError('Caller boundary was not reached')
   check(machine,initial,c,kind)
  callers+=1
 # Census aligned retail JALs and literal code pointers, independent of text labels.
 rows=list(csv.DictReader((root/'conker/retail_layout.us.txt').open()))
 game_end=max(int(r['end'],16) for r in rows if r['section']=='game')
 code=rom[0x2d4b0:game_end-0x15000000+0x2d4b0];jal=0x0c000000|((source.ENTRY>>2)&0x3ffffff)
 jal_sites=[0x2d4b0+i for i in range(0,len(code)-3,4) if struct.unpack_from('>I',code,i)[0]==jal]
 assert jal_sites==[0x225ec4,0x226084],jal_sites
 pointers=[i for i in range(0,len(rom)-3,4) if struct.unpack_from('>I',rom,i)[0]==source.ENTRY]
 assert pointers==[],pointers
 controls={};base=programs[0]
 for label,index,word in (('wrong_lookahead_mask',8,base[8]-128),('wrong_cursor_stride',18,base[18]+64),('wrong_low_nibble',24,base[24]-8),('omit_slow_bit_update',43,0),('unsigned_tree_symbol',41,base[41]+0x10000000)):
  changed=base[:];changed[index]=word;controls[label]=changed
 killed=set()
 for c in (Case(counter=7,length=9,packed=0xff,look=255),Case(counter=7,depth=3,pattern=5,first=128)):
  initial=fixture(c)
  for label,words in controls.items():
   if label in killed:continue
   try:machine=Oracle(words,initial,c);machine.run();check(machine,initial,c)
   except (AssertionError,KeyError):killed.add(label)
 assert killed==set(controls),(killed,set(controls)-killed)
 report=dict(cases=cases,streams=3,observed_words=len(seen),full_state_access_prefixes=prefixes,arithmetic_faults=faults,caller_windows=2,caller_cases=callers,jal_rom_sites=jal_sites,literal_code_pointers=0,negative_controls=sorted(killed),native_c_not_applicable=True,full_parents_and_hardware_not_qualified=True)
 (out/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
