"""Compare concrete private frames and ordered FP instructions diagnostically."""
from pathlib import Path
import difflib,json,struct,sys
from tools.experiments import game_strip_update_151ad174_private_recovery as source
from tools.tests import game_strip_update_151ad174_private_oracle as o
p=source.OUT
class Observe(o.Oracle):
 def __init__(self,w,m,c):super().__init__(w,m,c);self.fp=[];self.boundaries=[]
 def execute(self,w):
  op,fmt,ft,fs,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
  if op==17 and fmt in(16,17,20)and fn!=6:
   a=self.f[fs]if fmt!=17 else self.f[fs+1]<<32|self.f[fs]
   args=(a,)
   if fn in(0,1,2,3,50,60,62):args+=(self.f[ft]if fmt!=17 else self.f[ft+1]<<32|self.f[ft],)
   self.fp.append((fmt,fn,args))
  return super().execute(w)
 def record_call(self,t):
  super().record_call(t);self.boundaries.append((t,bytes(self.memory[o.STACK+i]for i in range(-776,16)),tuple(self.fp)))
def run(label,c):
 out=p;raw,refs=o.payload(out/'owner.o','func_151AD174');w=o.bound_blob(raw,refs,o.SYMS)
 truth=list(struct.unpack('>494I',(p/'retail.bin').read_bytes()));initial=o.fixture(c)
 a=Observe(truth,initial,c).run();b=Observe(w,initial,c).run();assert o.public(a.memory)==o.public(b.memory)and a.service.calls==b.service.calls
 rows=[]
 for ordinal,((ta,aa,fa),(tb,bb,fb))in enumerate(zip(a.boundaries,b.boundaries)):
  assert ta==tb;diff=[i-776 for i,(x,y)in enumerate(zip(aa,bb))if x!=y]
  rows.append(dict(ordinal=ordinal,target=hex(ta),private_different_bytes=len(diff),different_words=sorted(set(i&~3 for i in diff)),fp_operations=(len(fa),len(fb)),ordered_FP_equal=fa==fb))
 diff=[i for i in range(-776,16)if a.memory[o.STACK+i]!=b.memory[o.STACK+i]]
 edits=[]
 for tag,al,ar,bl,br in difflib.SequenceMatcher(None,a.fp,b.fp,autojunk=False).get_opcodes():
  if tag!='equal':edits.append(dict(kind=tag,retail_range=(al,ar),candidate_range=(bl,br),retail=a.fp[al:min(ar,al+5)],candidate=b.fp[bl:min(br,bl+5)]))
 return dict(label=label,case=o.asdict(c),boundaries=rows,return_private_different_bytes=len(diff),return_different_words=sorted(set(i&~3 for i in diff)),retail_FP=len(a.fp),candidate_FP=len(b.fp),ordered_FP_equal=a.fp==b.fp,fp_sequence_edits=edits)
def main():
 label="v20";results=[run(label,o.Case(seed=7,owner=1,impulse=1,pattern=1,handle=0)),run(label,o.Case(count=0))]
 (p/'private-observation.json').write_text(json.dumps(results,indent=2)+'\n')
 for v in results:
  brief={k:v[k]for k in('label','case','return_private_different_bytes','return_different_words','retail_FP','candidate_FP','ordered_FP_equal')}
  brief['fp_edit_count']=len(v['fp_sequence_edits']);brief['first_fp_edits']=v['fp_sequence_edits'][:4];print(json.dumps(brief),flush=True)
if __name__=="__main__":main()
