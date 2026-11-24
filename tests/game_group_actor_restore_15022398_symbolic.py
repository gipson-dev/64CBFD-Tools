"""Independent instruction-isomorphism audit for one unexposed private word."""
from pathlib import Path
import json,struct,sys
from tools.experiments import game_group_actor_restore_15022398_match as p
r,o=p.ROOT,p.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
ARITY={'func_15083E0C':1,'func_1505EEF4':1,'func_15082A44':5,'func_1505E650':7,'func_1502225C':2}
MEM={35:4,36:1,37:2,40:1,41:2,43:4,49:4,57:4}
def proof(raw,retail):
 a,b=[tuple(w[0]for w in struct.iter_unpack('>I',v[0]))for v in(raw,retail)];assert len(a)==len(b)==100 and raw[1]==retail[1]
 assert a[0]==b[0]==0x27bdffc0 and a[-3:]==b[-3:]==(0x27bd0040,0x03e00008,0)
 different=[i for i,(x,y)in enumerate(zip(a,b))if x!=y];assert len(different)==4
 pairs=set();accesses=[];private=[];calls=[]
 for i,(x,y)in enumerate(zip(a,b)):
  op=x>>26;rs=x>>21&31;rt=x>>16&31
  if x!=y:
   assert op in(35,43)and rs==29 and(x&0xffff0000)==(y&0xffff0000),(i,'Non-private semantic instruction changed');pairs.add((x&65535,y&65535));accesses.append(dict(word=i,operation='load'if op==35 else'store',role=rt))
  if op in MEM and rs==29:private.append((i,x&65535,MEM[op],op))
  if op==3:
   refs=raw[1].get(4*i);assert refs and len(refs)==1 and refs[0][0]=='R_MIPS_26';name=refs[0][1];assert name in ARITY;calls.append((i,name,ARITY[name]))
  # SP is used only as the unchanged frame pointer and a direct memory base.
  # No pointer to a local word or other private range is constructed or escaped.
  if op==0 and x:
   if x&63==8:assert rs==31
   else:assert rs!=29 and rt!=29 and(x>>11&31)!=29,(i,'Private address escapes through R operation')
  elif op==9:
   if rs==29 or rt==29:assert rs==rt==29 and i in(0,97)
  elif op in(4,5,6,7,20,21,22,23):assert rs!=29 and rt!=29
  elif op in(12,13,14,15):assert rs!=29 and rt!=29
  elif op==17 and rs in(0,4):assert rt!=29
  if op in(35,36,37)or op in(40,41,43):assert rt!=29
 assert len(pairs)==1;p,q=next(iter(pairs));assert p!=q and p%4==q%4==0 and 28<=min(p,q)and max(p,q)+4<=64
 assert [v['operation']for v in accesses]==['store','load','store','load'];assert all(v['role']==6 for v in accesses)
 for i,off,n,op in private:
  if i in different:assert off==p and n==4
  else:assert not(set(range(off,off+n))&(set(range(p,p+4))|set(range(q,q+4)))),(i,'Private permutation overlaps another live access')
 # Every original branch target and delay instruction is literal identical;
 # pair-renamed loads/stores have no instruction or data binding of their own.
 assert all(4*i not in raw[1]for i in different)
 assert max(4*max(4,n)for _,_,n in calls)==28 and len(calls)==6
 pending=[(0,False)];seen=set();reloads=set();returns=0
 def transfer(i,defined):
  w=a[i];op=w>>26
  if op in(35,43)and w>>21&31==29 and w&65535==p:
   if op==35:assert defined,(i,'Private reload precedes its definition');reloads.add(i)
   else:defined=True
  return defined
 while pending:
  i,defined=pending.pop();assert 0<=i<100
  if(i,defined)in seen:continue
  seen.add((i,defined));w=a[i];op=w>>26
  if w==0x03e00008:transfer(i+1,defined);returns+=1;continue
  if op==3:pending.append((i+2,transfer(i+1,defined)));continue
  if op in(4,5,6,7,20,21,22,23):
   target=i+1+(((w&65535)^32768)-32768);assert target>i,'Unexpected loop';equal_registers=(w>>21&31)==(w>>16&31);answers=(op in(4,20),)if equal_registers and op in(4,5,20,21)else(False,True)
   for take in answers:pending.append((target if take else i+2,transfer(i+1,defined)if take or op not in(20,21,22,23)else defined))
  else:pending.append((i+1,transfer(i,defined)))
 assert reloads=={30,37}and returns
 return dict(induction='Identical instructions preserve equal registers and coupled public memory; only the four equal-width SP accesses rename a private word. Every branch/delay word and binding is unchanged. The complete literal CFG verifies that stores dominate both reloads. Providers preserve unexposed private locals; all caller homes end below offset28. Return restores the same frame and RA. Thus the relation holds instruction-by-instruction over every compatible provider return/effect.',raw_home=p,retail_home=q,word_count=100,frame=64,changed_home_words=accesses,CFG_states_checked=len(seen),private_reloads_dominated_by_stores=True,private_addresses_escape=False,maximum_provider_argument_home_extent=28,provider_sites=calls,projection_imported=False,scope='Mapped public objects disjoint from the private frame; compatible o32 providers may arbitrarily mutate public RAM and caller argument homes below28. Raw physical private/fault-state identity and provider private-frame/code-address reflection are excluded; no semantic provider implementation, full-caller, native C or whole-image matching credit yet.')
def main():
 raw=payload(o/'selected-final/candidate.o','func_15022398');truth=payload(o/'original-target.o','func_15022398');q=proof(raw,truth);words=list(struct.unpack('>100I',raw[0]));changed=words[:]
 for i,w in enumerate(words):
  if i in(24,30,34,37):changed[i]=(w&0xffff0000)|48
 positive=proof((struct.pack('>100I',*changed),raw[1]),truth);assert positive['raw_home']==48
 controls=[]
 for label,i,w in [('wrong-public-state-byte',38,words[38]+1),('lost-pointer-save',24,words[24]+8),('wrong-key-home',32,words[32]+4)]:
  bad=words[:];bad[i]=w
  try:proof((struct.pack('>100I',*bad),raw[1]),truth)
  except AssertionError:controls.append(label)
  else:raise AssertionError(('Ineffective isomorphism control',label))
 q.update(controls=controls,independent_unused_home_move_accepted=True,source_installed=p.installed(),matching_credit=0);(o/'private-home-proof.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True)
if __name__=='__main__':main()
