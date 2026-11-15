"""Closed straight-line address/register schedule proof for the private prefix.

This proves the raw and retail first 34 instructions agree in memory accesses,
stores, FPRs and every GPR except A2. The 48-word suffix is identical. The
remaining A2 value is dead: the suffix's first call is bzero with two arguments,
and the next explicit A2 use follows a constant overwrite. Providers observe
their declared arguments and public memory, not unpassed register junk.
No normalization is installed by this certificate.
"""
from pathlib import Path
import json,os
from tools.experiments import game_view_reset_15017640_candidates as source

def signed16(n):return ((n&65535)^32768)-32768
def add(a,b):
 if isinstance(a,int):return (a+b)&0xffffffff
 assert a[0]=='SP',a
 return ('SP',a[1]+b)

def prefix(words):
 r=[('R',i) for i in range(32)];r[0]=0;r[29]=('SP',0)
 f=[('F',i) for i in range(32)];memory={};trace=[]
 for w in words[:34]:
  op,rs,rt,rd,imm,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&65535,w&63
  if op==15:r[rt]=imm<<16
  elif op==9:r[rt]=add(r[rs],signed16(imm))
  elif op in (33,37):
   address=add(r[rs],signed16(imm));r[rt]=('S16' if op==33 else 'U16',address);trace.append(('R',address,2))
  elif op in (40,43,57):
   address=add(r[rs],signed16(imm));value=f[rt] if op==57 else r[rt];width=1 if op==40 else 4
   memory[address,width]=value;trace.append(('W',address,width,value))
  elif op==17 and rs==4:f[rd]=r[rt]
  elif op==17 and rs==20 and fn==32:f[w>>6&31]=('F32ofS32',f[rd])
  else:raise AssertionError(('Unmodeled prefix word',hex(w)))
  r[0]=0
 return r,f,memory,trace

def reads(w):
 op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63
 if not w:return set()
 if op==0:
  if fn in (0,2,3):return {rt}
  if fn in (33,35,36,37,42,43):return {rs,rt}
  if fn==8:return {rs}
 if op==15:return set()
 if op in (9,12,13,35,36,49):return {rs}
 if op in (40,41,43):return {rs,rt}
 if op==57:return {rs}
 if op in (4,5):return {rs,rt}
 if op==17 and rs==4:return {rt}
 if op==17:return set()
 if op==3:return set()
 raise AssertionError(('Unmodeled suffix word',hex(w)))

def certify(retail,raw):
 assert len(retail)==len(raw)==82 and retail[34:]==raw[34:]
 left,right=prefix(retail),prefix(raw)
 assert left[1:]==right[1:],'Prefix memory/FPR/trace differs'
 differences=[i for i,(a,b) in enumerate(zip(left[0],right[0])) if a!=b]
 assert differences==[6] and left[0][6]==0x800d2438 and right[0][6]==('R',6)
 killed=False;calls=[]
 for index,w in enumerate(retail[34:],34):
  # LUI A2 is the first explicit definition, before the seven-argument call.
  if w>>26==15 and w>>16&31==6:killed=True;break
  assert 6 not in reads(w),('A2 is observed before its kill',index)
  if w>>26==3:calls.append(((w&0x3ffffff)<<2)|((source.ENTRY+index*4+4)&0xf0000000))
 assert killed and calls==[0x100226f0]
 return dict(prefix_words=34,identical_suffix_words=48,arbitrary_symbolic_input=True,fixed_retail_addresses=True,
             public_memory_trace_equal=True,all_fprs_equal=True,dead_input_register='A2',
             unpassed_registers_not_provider_inputs=True,normalization_installed=False)

def main():
 root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();programs=source.programs(root)
 retail=programs[0][0];raw=programs[2][0];report=certify(retail,raw)
 killed=[]
 for label,index,word in (('wrong_motion_destination',7,raw[7]+4),('wrong_default_sign',14,raw[14]+0x10000000),('wrong_motion_store',20,raw[20]+4)):
  changed=raw[:];changed[index]=word
  try:certify(retail,changed)
  except AssertionError:killed.append(label)
  else:raise AssertionError('Ineffective prefix control: '+label)
 report.update(negative_controls=killed,private=True,c_match_credit=0)
 (root/source.BUILD/'prefix-proof.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
