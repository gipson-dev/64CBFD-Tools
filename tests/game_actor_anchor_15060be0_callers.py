"""No invented caller windows: census and poisoned non-input ABI states."""
import json,struct
from dataclasses import replace
from tools.tests import game_actor_anchor_15060be0_oracle as g
def census():
 rom=(g.root/'conker/conker.us.bin').read_bytes();sites=[];pointers=[]
 for at in range(0,len(rom)-3,4):
  w=struct.unpack_from('>I',rom,at)[0]
  if w==g.ENTRY:pointers.append(at)
  if w>>26 in(2,3)and(w&0x03FFFFFF)<<2==g.ENTRY&0x0FFFFFFF:sites.append(at)
 assert not sites and not pointers;return dict(aligned_direct_J_or_JAL_sites=sites,aligned_literal_pointers=pointers,computed_indirect_calls_excluded=False,caller_windows_qualified=0,runtime_reachability_qualified=False)
def main():
 raw=g.words(g.out/'selected.o');normalized=g.words(g.out/'selected.o',True);rom=struct.unpack_from('>93I',(g.root/'conker/conker.us.bin').read_bytes(),0x8E090);runs=pairs=0
 for c in(g.Case(),g.Case(identity=255),g.Case(present=0),g.Case(disabled=1),g.Case(alias=2),g.Case(distance=0),g.Case(origin=(0x41240000,0x7F800000,0)),g.Case(identity=254)):
  for poison in(0,0xA5000000,0x7FC12345):
   ms=[]
   for ws in(raw,normalized,rom):
    m=g.Oracle(ws,g.fixture(c),c)
    for reg in(1,2,3,*range(5,16),24,25):m.r[reg]=g.u32(poison+reg)
    m.f[:20]=[g.u32(poison+i)for i in range(20)];m.before=m.r[:];m.before_f=m.f[:]
    try:m.run()
    except g.InvalidConversionPrefix:pass
    expected,normal,*_=g.reference(m.initial,c);assert g.public(m.memory)==g.public(expected)and normal==(m.prefix is None);assert m.r[16:24]==m.before[16:24]and m.f[20:]==m.before_f[20:]
    if normal:assert m.r[28:]==m.before[28:]
    ms.append(m);runs+=1
   a,b=ms[1:];assert(a.memory,a.r,a.f,a.trace,a.prefix)==(b.memory,b.r,b.f,b.trace,b.prefix);pairs+=1
 result=dict(census=census(),poisoned_non_input_executions=runs,complete_normalized_retail_pairs=pairs,one_pointer_argument_from_A0=True,saved_registers_preserved=True,semantic_C_interface_void=True,incidental_V0_flag_checked_by_guest=True,original_C_return_type_proven=False);(g.out/'callers.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
