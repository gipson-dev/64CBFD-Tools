"""Source fields only: allocation, quiet-epoch scheduling and one retained-Z reload.

No retail instruction array is read or embedded. Verify the complete source and
bindings before deriving the separate guarded fit. The source relation has an
explicit finite-value domain; raw FP exception/NaN/fault identity is unclaimed.
"""
import hashlib,json,struct
from pathlib import Path
from tools.experiments import game_impact_terminal_150b8f44_screen as s
PIN=json.loads((Path(__file__).parents[1]/'experiments/game_impact_terminal_150b8f44_fit_manifest.json').read_text())

def verify(words,refs):
 assert len(words)==390 and hashlib.sha256(struct.pack('>390I',*words)).hexdigest()==s.PIN['raw_sha256']
 assert refs=={int(k):[tuple(v)for v in rows]for k,rows in s.PIN['refs'].items()}

def fields(w,i):
 op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
 gp=lambda n:33-n if n in(16,17)and i not in(1,2,386,387)else n
 if i<18:mp={4:6,6:4,2:8,8:2}
 elif i<39 or i>=333:mp={6:10,10:8,8:6}
 elif i<69:mp={2:16,16:18,18:10,10:8,8:6,6:2}
 else:mp={4:6,6:4}
 fp=lambda n:mp.get(n,n)
 def f(at,value):
  nonlocal w;w=(w&~(31<<at))|(value<<at)
 if op==0:
  f(21,gp(rs));f(16,gp(rt));f(11,gp(rd))
 elif op in(2,3):pass
 elif op==17:
  if rs in(0,4):f(16,gp(rt));f(11,fp(rd))
  elif rs in(16,20):f(16,fp(rt));f(11,fp(rd));f(6,fp(fd))
 else:
  f(21,gp(rs));f(16,fp(rt)if op in(49,53,57,61)else gp(rt))
 if op in(9,32,33,35,36,37,40,41,42,43,46,49,53,57,61)and rs==29 and 100<=w&65535<416:w-=4
 if i in(17,333):f(11,2)
 if i==334:w=0
 if i==335:f(11,2)
 if i==57:f(16,4)
 if i==341:
  fs,ft=w>>11&31,w>>16&31;f(11,ft);f(16,fs)
 return w

def derive(words,refs=None):
 assert len(words)==390
 if refs is not None:verify(words,refs)
 values=[fields(w,i)for i,w in enumerate(words)]
 order=list(range(390));order.insert(52,194)
 for lo,hi,indices in PIN['schedule']:
  assert len(indices)==hi-lo;order[lo:hi]=indices
 from collections import Counter
 assert len(order)==391 and Counter(order)==Counter(range(390))+Counter([194])
 inserted=fields(words[194],194);assert inserted>>26==49 and inserted>>21&31==29 and inserted&65535==408
 inserted=(inserted&~(31<<16))|(4<<16)
 inverse={old:new for new,old in enumerate(order)if not(new==52 and old==194)};inverse[190]=191
 result=[];bindings={}
 for new,index in enumerate(order):
  w=inserted if new==52 else values[index];op,rs=w>>26,w>>21&31
  if op in(4,5,6,7,20,21,22,23)or op==17 and rs==8:
   dest=index+1+((words[index]&65535)^32768)-32768;off=inverse[dest]-new-1;assert -32768<=off<32768;w=(w&0xffff0000)|(off&65535)
  result.append(w)
  if refs is not None and index*4 in refs:bindings[new*4]=refs[index*4]
 if refs is None:return result
 return result,bindings
