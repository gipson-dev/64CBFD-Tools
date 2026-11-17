"""Independent GNU carry links and the original bounded caller window."""
from pathlib import Path
from dataclasses import replace
import hashlib,importlib.util,json,re,struct,subprocess,sys
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments import game_effect_chain_151a6c90_recovery as source
from tools.tests import game_effect_chain_151a6c90_oracle as g
R,P,N,ENTRY=source.ROOT,source.OUT,source.NAME,source.ENTRY
CALLER=0x1507DADC;END=CALLER+16
def rebases():
 syms={r[1]:r[2][1]for r in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())};objects=[P/'q2-padded-strict.o',P/'q2-padded-layout.o',P/'q2-original-reference.o'];raw,refs=payload(objects[2],N);report=[]
 for i,start in enumerate((ENTRY,0x151B8000,0x151C8004,0x151DFFF0)):
  moved=dict(syms);moved['D_800A8DB0']=(0x800A8DB0,0x800A7FFC,0x800A8000,0x800AFFF0)[i];results=[]
  for j,obj in enumerate(objects):
   offset=parse_object(obj)[1][N]['value'];ld=P/('carry-%d-%d.ld'%(i,j));elf=ld.with_suffix('.elf');bin=ld.with_suffix('.bin')
   names=[line.split()[-1]for line in subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True).splitlines()]
   script='SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(start-offset)+'\n'.join('%s = 0x%X;'%(name,moved[name])for name in names)
   if ld.exists():
    assert ld.read_text()==script and elf.is_file()and bin.is_file()
    # The first run completed every link before its caller-window boundary
    # defect. Revalidate those retained outputs without replacing them.
    at=elf_slot_offset(elf.read_bytes(),start,616);assert elf.read_bytes()[at:at+616]==bin.read_bytes()[offset:offset+616]
   else:
    ld.write_text(script)
    q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',N,'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
    subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(bin)],capture_output=True,check=True)
   results.append(bin.read_bytes()[offset:offset+616])
  assert results[0]==results[1]==results[2]==struct.pack('>154I',*bound_blob(raw,refs,moved))
  report.append(dict(code_start=hex(start),coefficient=hex(moved['D_800A8DB0']),GNU_links=3))
 return report
class Caller(g.Oracle):
 def __init__(self,words,initial,c,window):
  connected=dict(zip(range(ENTRY,ENTRY+len(words)*4,4),words))
  # Ownership includes the exit boundary, whose fetch raises before execution.
  connected[END]=0
  FactoryOracle.__init__(self,window,initial,c,entry=CALLER,s={},arguments=(),connected=connected)
  self.r[16]=g.A;self.service=g.Service(self.memory,c,self.target_home);self.target_calls=[]
  self.code=WindowCode(self.code,self);self.code.ends={END}
 def record_call(self,t):
  if t==ENTRY:
   args=tuple(self.arguments(3));assert args==(g.A,255,1),('caller ABI',args);self.target_calls.append(args)
  else:super().record_call(t)
def callers():
 rom=(R/'conker/conker.us.bin').read_bytes();elf=(R/'conker/build/conker.us.elf').read_bytes();caller_text=(source.FROZEN/'conker/asm/nonmatchings/game_A9D90/func_1507D754.s').read_text()
 rows=[(int(a,16),int(v,16))for a,v in re.findall(r'/\* [0-9A-F]+ ([0-9A-F]{8}) ([0-9A-F]{8}) \*/',caller_text)]
 assert rows and rows[0][0]==0x1507D754 and all(a==rows[0][0]+4*i for i,(a,v)in enumerate(rows))
 original=struct.pack('>'+str(len(rows))+'I',*(v for a,v in rows));at=elf_slot_offset(elf,rows[0][0],len(original));assert elf[at:at+len(original)]==original
 window=list(struct.unpack_from('>4I',rom,CALLER-0x14FD2B50));assert window==[0x02002025,0x240500FF,0x0D469B24,0x24060001]
 counts={}
 for label,words in g.programs().items():
  n=0
  for seed,mutation,phase in __import__('itertools').product(range(4),range(16),(0,8)):
   c=g.Case(seed=seed,slot=255,context=1,mutation=mutation,phase=phase);initial=g.fixture(c);expected,calls=g.reference(initial,c);m=Caller(words,initial,c,window)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Caller boundary not reached')
   assert m.target_calls==[(g.A,255,1)]and m.service.calls==calls and g.public(m.memory)==g.public(expected);n+=1
  counts[label]=n
 controls=[]
 for label,index,value in(('slot',1,0x240500FE),('context',3,0x24060002)):
  bad=window[:];bad[index]=value;c=g.Case();m=Caller(g.programs()['raw'],g.fixture(c),c,bad)
  try:m.run()
  except AssertionError:controls.append(label)
  else:raise AssertionError(('ineffective caller control',label))
 return dict(complete_parent_words=len(rows),parent_production_literal=True,parent_sha256=hashlib.sha256(original).hexdigest(),window_words=4,window=hex(CALLER),boundary=hex(END),cases_per_stream=counts,effective_controls=controls,whole_parent_execution_claimed=False)
def main():
 report=dict(rebases=rebases(),callers=callers(),source_installed=source.installed(),c_match_credit=0)
 (P/'rebase-caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
