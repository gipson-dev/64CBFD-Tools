"""Pure source-word normalization: schedule, closed roles, copies and zero transfers.

The plan contains source ranges and register permutations, never replacement
instruction arrays. All 480 retained operations have matching logical operand
sets in the complete source/retail relation. Full path proof remains separate.
"""
from pathlib import Path
import hashlib,json,struct
PLAN=json.loads((Path(__file__).parents[1]/'experiments/game_actor_bound_burst_150b7b40_match_manifest.json').read_text())['normalization']
def fields(w):
 op,rs,fn=w>>26,w>>21&31,w&63
 if not w:return[]
 if op==0:
  if fn in(0,2,3):return[('g',16),('g',11)]
  if fn in(8,9):return[('g',21)]+([('g',11)]if fn==9 else[])
  if fn in(16,18):return[('g',11)]
  if fn in(24,25,26,27):return[('g',21),('g',16)]
  return[('g',21),('g',16),('g',11)]
 if op==17:
  if rs==8:return[]
  if rs in(0,4):return[('g',16),('f',11)]
  if rs in(16,20):return[('f',11)]+([('f',16)]if rs==16 and fn in(0,1,2,3,50,60)else[])+([('f',6)]if fn not in(50,60)else[])
 if op in(2,3):return[]
 if op in(49,53,57,61):return[('g',21),('f',16)]
 if op in(6,7,22,23):return[('g',21)]
 return[('g',21),('g',16)]
def permutation(cycles):
 result=list(range(32));used=set()
 for chain in cycles:
  assert len(chain)>1 and not used.intersection(chain)and len(chain)==len(set(chain));used.update(chain)
  for a,b in zip(chain,chain[1:]+chain[:1]):result[a]=b
 assert set(result)==set(range(32));return result

def derive(raw,refs):
 assert len(raw)==1932 and hashlib.sha256(raw).hexdigest()==PLAN['source_sha256'],'stale compiler payload'
 expected={int(k):[tuple(v)for v in rows]for k,rows in PLAN['source_refs'].items()};assert refs==expected,'stale source bindings'
 words=list(struct.unpack('>483I',raw));order=[]
 for part in PLAN['order']:
  if 'source'in part:order.extend(range(*part['source']))
  else:order.append(part['emit'])
 assert len(order)==484;inverse={i:j for j,i in enumerate(order)if isinstance(i,int)}
 assert len(inverse)==480 and set(range(483))-inverse.keys()==set(PLAN['dropped_source'])
 # A source label names the whole block. Its first scheduled instruction can
 # precede the mapped original leader (the joined radius load is one example).
 leaders={0,483}
 for i,w in enumerate(words):
  op,rs=w>>26,w>>21&31
  if op in(4,5,6,7,20,21,22,23)or op==17 and rs==8:
   leaders.update((i+1+(((w&65535)^32768)-32768),i+2))
 ordered=sorted(leaders);entries={}
 for first,last in zip(ordered,ordered[1:]):
  mapped=[inverse[i]for i in range(first,last)if i in inverse]
  if mapped:entries[first]=min(mapped)
 assert words[75]==0 and words[409]>>26==words[424]>>26==9 and words[409]&65535==3 and words[424]&65535==1
 overrides={v['target']:v for v in PLAN['read_role_overrides']};phases=[]
 for phase in PLAN['permutations']:
  maps={t:permutation(phase[t])for t in('g','f')};assert maps['g'][0]==0 and maps['g'][29]==29;phases.append((phase['start'],phase['end'],maps))
 result=[];bindings={}
 for j,item in enumerate(order):
  if isinstance(item,dict):
   template=words[item['template']]
   if item['kind']=='copy-value':
    assert template>>26==0 and template&63==37 and template>>16&31==0
    w=(template&~(31<<21|31<<16|31<<11))|(item['source_register']<<21)|(item['destination_register']<<11)
   else:
    assert item['kind']=='transfer-zero'and template>>26==17 and template>>21&31==4 and template>>16&31==0
    w=(template&~(31<<11))|(item['destination_register']<<11)
  else:
   i=item;w=words[i];maps=next(m for a,b,m in phases if a<=j<b)
   for t,shift in fields(words[i]):w=(w&~(31<<shift))|(maps[t][words[i]>>shift&31]<<shift)
   if j in overrides:
    override=overrides[j];assert override['source']==i;shift=override['field'];w=(w&~(31<<shift))|(override['value']<<shift)
   op,rs=words[i]>>26,words[i]>>21&31
   if op in(4,5,6,7,20,21,22,23)or op==17 and rs==8:
    target=i+1+(((words[i]&65535)^32768)-32768);assert target in entries,('omitted branch block',i,target)
    offset=entries[target]-j-1;assert -32768<=offset<32768;w=(w&0xffff0000)|(offset&65535)
   if 4*i in refs:bindings[4*j]=list(refs[4*i])
  result.append(w)
 assert len(bindings)==len(refs)
 return struct.pack('>484I',*result),bindings