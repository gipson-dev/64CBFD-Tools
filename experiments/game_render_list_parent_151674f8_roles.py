"""Closed integer reaching-definition proof, including delay slots and calls.

Only four pairwise-independent setup operations are permuted. Every other
origin keeps its opcode, literal, binding, control edges and memory order.
"""
from pathlib import Path
from collections import deque
import hashlib,json,struct,subprocess,sys
from tools.experiments import game_render_list_parent_151674f8_match as packet
r,o=packet.ROOT,packet.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
NAME='func_151674F8';CALLS={28:3,163:4,192:3,238:3,264:3};VOLATILE=(1,2,3,*range(4,16),24,25)
def info(w):
 op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;fn=w&63;sh=w>>6&31;kind='normal';write=None
 if op==0:
  if fn in(0,2,3):fields=(16,11);reads=(rt,);write=rd
  elif fn in(33,35,36,37,38,42,43):fields=(21,16,11);reads=(rs,rt);write=rd
  elif fn==8:assert rd==rt==sh==0;fields=(21,);reads=(rs,);kind='return'
  elif fn==9:assert rd==31 and rt==sh==0;fields=(21,);reads=(rs,);write=31;kind='call'
  else:raise AssertionError(('Unsupported ALU',hex(w)))
 elif op==3:fields=();reads=();write=31;kind='call'
 elif op in(4,5,6,7,20,21,22,23):fields=(21,16)if op in(4,5,20,21)else(21,);reads=(rs,rt)if op in(4,5,20,21)else(rs,);kind='branch'
 elif op==1:assert rt in(0,1);fields=(21,);reads=(rs,);kind='branch'
 elif op==15:assert rs==0;fields=(16,);reads=();write=rt
 elif op in(9,10,11,12,13,14,0x20,0x21,0x23,0x24,0x25):fields=(21,16);reads=(rs,);write=rt
 elif op in(0x28,0x29,0x2B):fields=(21,16);reads=(rs,rt)
 else:raise AssertionError(('Unsupported instruction',hex(w)))
 mask=sum(31<<s for s in fields)
 return dict(kind=kind,fields=fields,reads=reads,write=write,signature=w&~mask,mask=mask)
def graph(words):
 start=('word',0,None);nodes={};todo=[start]
 def word(i,resume=None):assert 0<=i<len(words),i;return('word',i,resume)
 def resume_key(resume):return word(resume[1])if resume[0]=='pc'else('post',resume[1],None)if resume[0]=='post'else('exit',0,None)
 while todo:
  key=todo.pop()
  if key in nodes:continue
  tag,i,resume=key
  if tag=='exit':node=dict(reads=(2,*range(16,24),28,29,30,31),write=None,successors=[])
  elif tag=='post':assert i in CALLS;node=dict(reads=(*range(4,4+CALLS[i]),29),write=None,successors=[word(i+2)])
  else:
   w=words[i];s=info(w);node=dict(reads=s['reads'],write=s['write']);kind=s['kind']
   if resume is not None:assert kind=='normal';successors=[resume_key(resume)]
   elif kind=='return':assert w>>21&31==31;successors=[word(i+1,('exit',))]
   elif kind=='call':assert i in CALLS;successors=[word(i+1,('post',i))]
   elif kind=='branch':
    op=w>>26;rs=w>>21&31;rt=w>>16&31;dst=i+1+(((w&65535)^32768)-32768);possible=(True,False)
    if op in(4,20)and rs==rt:possible=(True,)
    if op in(5,21)and rs==rt:possible=(False,)
    if op in(6,22)and rs==0:possible=(True,)
    if op in(7,23)and rs==0:possible=(False,)
    successors=[word(i+1,('pc',dst))if take else word(i+2)if op in(20,21,22,23)else word(i+1,('pc',i+2))for take in possible]
   else:successors=[word(i+1)]
   node['successors']=successors
  nodes[key]=node;todo.extend(node['successors'])
 return start,nodes
def reaching(words):
 start,nodes=graph(words);entry=tuple(frozenset({('entry',i)})for i in range(32));states={start:entry};todo=deque([start]);updates=0
 while todo:
  key=todo.popleft();state=list(states[key]);tag,i,_=key;node=nodes[key]
  if tag=='post':
   for reg in VOLATILE:state[reg]=frozenset({('return',i)if reg==2 else('clobber',i,reg)})
  elif tag=='word'and node['write']:
   reg=node['write'];state[reg]=frozenset({('link',i)if info(words[i])['kind']=='call'else('value',i)})
  after=tuple(state)
  for target in node['successors']:
   old=states.get(target);merged=after if old is None else tuple(a|b for a,b in zip(old,after))
   if old!=merged:states[target]=merged;todo.append(target);updates+=1
 return nodes,states,updates
def prove(source,retail):
 assert len(source)==len(retail)==348
 for i,(a,b)in enumerate(zip(source,retail)):
  x,y=info(a),info(b);assert x['kind']==y['kind']and x['signature']==y['signature'],('Opcode, literal or control substitution',i,hex(a),hex(b))
 a,sa,ua=reaching(source);b,sb,ub=reaching(retail);assert a.keys()==b.keys(),('CFG nodes changed',a.keys()-b.keys(),b.keys()-a.keys());reads=0
 for key in a:
  assert a[key]['successors']==b[key]['successors'],('Control edge changed',key)
  left,right=a[key]['reads'],b[key]['reads'];assert len(left)==len(right)
  for x,y in zip(left,right):
   assert sa[key][x]==sb[key][y],('Reaching definition mismatch',key,x,y,sa[key][x],sb[key][y]);reads+=1
 return dict(expanded_CFG_nodes=len(a),register_operand_pairs=reads,fixed_point_updates=[ua,ub],unreachable_words=[i for i in range(348)if not any(k[0]=='word'and k[1]==i for k in a)])
