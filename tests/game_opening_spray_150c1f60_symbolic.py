"""Independent symbolic byte-memory proof; never imports the normalizer."""
from collections import Counter
import struct

def split(v,n=4):
 if isinstance(v,int):return tuple((v>>(8*(n-i-1)))&255 for i in range(n))
 if v[0]=='WORD':return v[1][-n:]
 return tuple(('BYTE',v,4-n+i)for i in range(n))
def evaluate(words,refs,start,end):
 r=[('R',i)for i in range(32)];r[0]=0;r[29]=('STACK',0);f=[('F',i)for i in range(32)];memory={};trace=[]
 def addr(base,offset):assert base[0]=='STACK';return('STACK',base[1]+offset)
 def access(address,width,value=None):
  key=lambda i:('STACK',address[1]+i)if address[0]=='STACK'else(*address,i)
  if value is None:
   data=tuple(memory.get(key(i),('ENTRY',*key(i)))for i in range(width));trace.append(('R',address,width,data));return('WORD',data)if width==4 else data[0]
  data=split(value,width)
  for i,v in enumerate(data):memory[key(i)]=v
  trace.append(('W',address,width,data))
 for i in range(start,end):
  w=words[i];op,rs,rt,rd=w>>26,w>>21&31,w>>16&31,w>>11&31;imm=(w&65535)^32768;imm-=32768;bindings=refs.get(i*4,[])
  if op==15:r[rt]=('HI',bindings[0][1])if bindings else(w&65535)<<16
  elif op==9:r[rt]=imm&0xffffffff if rs==0 else addr(r[rs],imm)
  elif op==0:assert w&63==37 and rt==0;r[rd]=r[rs]
  elif op==17:assert rs==4 and w&0x7ff==0;f[rd]=r[rt]
  elif op in [35,36,49]:
   width=1 if op==36 else 4
   if bindings:
    assert bindings==[('R_MIPS_LO16',r[rs][1])]and r[rs][0]=='HI';address=('GLOBAL',r[rs][1])
   else:address=addr(r[rs],imm)
   value=access(address,width)
   if op==49:f[rt]=value
   else:r[rt]=value
  else:
   assert op in [40,41,43,57]and not bindings;access(addr(r[rs],imm),{40:1,41:2,43:4,57:4}[op],f[rt]if op==57 else r[rt])
 return r,f,memory,trace
def prove(raw,truth):
 a,b=[list(struct.unpack('>204I',v[0]))for v in [raw,truth]]
 blocks=[]
 for start,end in [(40,48),(139,198)]:
  left=evaluate(a,raw[1],start,end);right=evaluate(b,truth[1],start,end);assert left[:3]==right[:3],(start,'state');x,y=left[3],right[3];assert Counter(x)==Counter(y)and len(x)==len(set(x));at={v:i for i,v in enumerate(y)};inversions=[]
  for i,u in enumerate(x):
   for v in x[i+1:]:
    if at[u]<at[v]:continue
    assert u[1][0]==v[1][0]=='STACK';u0,v0=u[1][1],v[1][1];assert set(range(u0,u0+u[2])).isdisjoint(range(v0,v0+v[2]));inversions.append((u[:3],v[:3]))
  blocks.append(dict(start_word=start,end_word=end,complete_GPR_FPR_and_private_state_join=True,accesses=len(x),independent_private_access_inversions=inversions,FP_arithmetic_instructions=0))
 changed=set(range(40,48))|set(range(139,198));assert all(a[i]==b[i]and raw[1].get(i*4,[])==truth[1].get(i*4,[])for i in range(204)if i not in changed)
 q=dict(blocks=blocks,outside_blocks_words_and_bindings_identical=True,normal_mapped_aligned_stack_and_enabled_FPU=True,private_and_global_objects_disjoint=True,globals_stable_within_provider_free_blocks=True,arbitrary_entry_GPR_FPR_and_private_bytes=True,FCSR_preserved_no_FP_arithmetic=True,raw_fault_or_interrupt_prefix_identity_claim=False,normalizer_imported=False)
 return q
