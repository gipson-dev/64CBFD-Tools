"""Private expiry-callback route through the complete original 45-word parent."""
from dataclasses import replace
import csv,io,itertools,json,struct
from tools.experiments import game_radial_effect_150c29f0_recovery as s
from tools.tests import game_radial_effect_150c29f0_oracle as g
from tools.tests.test_game_point_transform_match import put
TABLE=0x8008a4c0

def main():
 rom=g.rom();parent=list(struct.unpack_from('>45I',rom,g.PARENT_ROM));assert parent[0]==0x27bdffe8 and parent[33]==0x0320f809
 programs=s.programs();cases=0;seen=set()
 def run(words,c,slot=5):
  initial=g.fixture(c);initial[g.OWNER+16]=slot
  for i in range(10):put(initial,TABLE+i*4,struct.unpack_from('>I',rom,0x22ef80+i*4)[0])
  connected=dict(zip(range(s.ENTRY,s.ENTRY+len(words)*4,4),words))
  m=g.Oracle(parent,initial,c,entry=g.PARENT,connected=connected);m.run();g.verify(m,initial,c)
  assert m.target_entries==[s.ENTRY] and g.read(m.memory,g.OWNER+14,2)==c.randoms[5]%51+25
  seen.update(m.visits)
 for angle,phase,mutation in itertools.product((0,63,64,127,128,191,192,255),(0,8),(0,1)):
  c=replace(g.Case(),randoms=(angle,*g.Case().randoms[1:]),phase=phase,mutation=mutation)
  for words in programs:run(words,c)
  cases+=1
 controls=0
 for slot,changed in ((4,False),(5,True)):
  words=programs[0][:]
  if changed:
   at=words.index(0xa528000e);words[at]=0xa528000c
  try:run(words,g.Case(),slot)
  except AssertionError:controls+=1
  else:raise AssertionError('Caller control was ineffective')
 rows=list(csv.DictReader(io.StringIO((s.ROOT/'conker/retail_layout.us.txt').read_text())));end=max(int(r['end'],16) for r in rows if r['section']=='game')
 jal=0x0c000000|((s.ENTRY>>2)&0x3ffffff)
 calls=[i for i in range(0x2d4b0,0x2d4b0+end-0x15000000,4) if struct.unpack_from('>I',rom,i)[0]==jal]
 pointers=[i for i in range(0,len(rom)-3,4) if struct.unpack_from('>I',rom,i)[0]==s.ENTRY]
 assert not calls and pointers==[0x22ef94]
 report=dict(caller_words=45,caller_cases=cases,streams=2,table='D_8008A4C0[5]',indirect_jalr_va='0x151492E8',observed_parent_words=len(seen&set(range(g.PARENT,g.PARENT+180,4))),controls=controls,direct_jals=0,aligned_entry_pointers=1,expiry_route_and_post_callback_lifetime_gate=True,other_lifecycle_routes_not_claimed=True,physical_stack_match_not_claimed=True,private_uninstalled=True)
 (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
