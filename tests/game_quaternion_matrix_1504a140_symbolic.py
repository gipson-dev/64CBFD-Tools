"""Ordered IEEE expression and stack/public access audit; no commutative rewrites."""
from collections import Counter
import json
from tools.experiments import game_quaternion_matrix_1504a140_recovery as source

def plus(a,n):
 if isinstance(a,int):return(a+n)&0xffffffff
 assert a[0] in ('Q','M','SP'),a
 return a[0],a[1]+n

def execute(words):
 r=[('R',i) for i in range(32)];r[0]=0;r[4]=('Q',0);r[5]=('M',0);r[29]=('SP',0)
 f=[('F',i) for i in range(32)];memory={};trace=[];ops=[];public=[];inputs=[]
 for index,w in enumerate(words):
  op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;imm=((w&65535)^32768)-32768
  if not w:continue
  if op==9:r[rt]=plus(r[rs],imm)
  elif op==15:r[rt]=(w&65535)<<16
  elif op==17 and rs==4:f[rd]=r[rt]
  elif op==17 and rs==16 and fn in (0,1,2,3):
   value=({0:'add',1:'sub',2:'mul',3:'div'}[fn],f[rd],f[rt]);ops.append(value);f[sa]=value
  elif op==17 and rs==16 and fn==6:f[sa]=f[rd]
  elif op==49:
   address=plus(r[rs],imm);value=memory.get((address,4),('LOAD',address));f[rt]=value;trace.append(('R',address,4,value))
   if address[0]=='Q':inputs.append((index,address))
  elif op==57:
   address=plus(r[rs],imm);memory[address,4]=f[rt];trace.append(('W',address,4,f[rt]))
   if address[0]=='M':public.append((index,address,f[rt]))
  elif op==61:
   address=plus(r[rs],imm);memory[address,8]=(f[rt],f[rt+1]);trace.append(('W',address,8,memory[address,8]))
  elif op==53:
   address=plus(r[rs],imm);f[rt],f[rt+1]=memory[address,8];trace.append(('R',address,8,memory[address,8]))
  elif op==0 and fn==8:assert rs==31 and index==len(words)-2
  else:raise AssertionError(('Unsupported symbolic word',hex(w)))
  r[0]=0
 assert r[29]==('SP',0) and f[20:]==[('F',i) for i in range(20,32)]
 assert len(public)==13 and {a[1] for _,a,_ in public}=={i*4 for i in (0,1,2,3,4,5,6,7,8,9,10,11,15)}
 assert max(i for i,_ in inputs)<min(i for i,_,_ in public),'Input reload follows an output store'
 return dict(registers=r,fprs=f,memory=memory,trace=trace,ops=ops,public=public,inputs=inputs)

def compare(a,b):
 ra,rb=execute(a),execute(b)
 result=dict(public_expressions_equal={p:v for _,p,v in ra['public']}=={p:v for _,p,v in rb['public']},ordered_arithmetic_multiset_equal=Counter(ra['ops'])==Counter(rb['ops']),private_memory_equal=ra['memory']==rb['memory'],ordered_accesses_equal=ra['trace']==rb['trace'],input_reads=[len(ra['inputs']),len(rb['inputs'])],inputs_before_output=True,commutative_rewrites=0)
 if not result['public_expressions_equal']:
  result['different_output_offsets']=[p[1] for _,p,v in ra['public'] if dict((p2,v2) for _,p2,v2 in rb['public']).get(p)!=v]
 return result

def main():
 truth,raw=[v[0] for v in source.programs()];report=compare(truth,raw)
 assert all(report[k] for k in ('public_expressions_equal','ordered_arithmetic_multiset_equal','private_memory_equal','ordered_accesses_equal'))
 assert truth==raw
 controls=0
 for index in (16,54,88):
  changed=raw[:];changed[index]^=1
  try:
   result=compare(truth,changed)
   assert all(result[k] for k in ('public_expressions_equal','ordered_arithmetic_multiset_equal','private_memory_equal','ordered_accesses_equal'))
  except (AssertionError,KeyError):controls+=1
  else:raise AssertionError('Changed symbolic schedule was accepted')
 report.update(body_words=89,guards=0,effective_controls=controls)
 (source.OUT/'symbolic-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
