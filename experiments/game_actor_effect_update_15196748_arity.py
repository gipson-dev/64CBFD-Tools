"""Actual original callback parameter liveness, including first-call frontiers."""
from pathlib import Path
import json,re
from tools.experiments import game_actor_effect_update_15196748_match as p
from tools.tests.game_actor_effect_update_15196748_symbolic import reads_writes
r,o=p.ROOT,p.OUT
def rw(w):
 op,fmt,rt=w>>26,w>>21&31,w>>16&31
 if op==17:
  if fmt in(0,2):return set(),{rt}
  if fmt in(4,6):return{rt},set()
  return set(),set()
 if op in(53,61):return{w>>21&31},set()
 if op in(34,38):return{w>>21&31,rt},{rt}
 if op in(42,46):return{w>>21&31,rt},set()
 if op in(13,14):return{w>>21&31},{rt}
 if op==0 and w&63 in(24,26):return{w>>21&31,rt},set()
 if op==0 and w&63 in(32,34,36,39,43):return{w>>21&31,rt},{w>>11&31}
 if op==11:return{w>>21&31},{rt}
 return reads_writes(w)

def main():
 source=(o/'baseline/conker/asm/1C2C60.s').read_text();rows=[]
 for name in('func_15198110','func_15198C90','func_15198D7C','func_15198570','func_1519897C','func_151987CC'):
  fragment=source.split('glabel '+name+'\n',1)[1].split('endlabel '+name,1)[0];words=[int(v,16)for v in re.findall(r'/\*\s*[0-9A-F]+\s+[0-9A-F]+\s+([0-9A-F]{8})\s*\*/',fragment)];todo=[(0,frozenset((4,5,6,7)))];seen=set();explicit=set();calls=[]
  while todo:
   pc,live=todo.pop()
   if not live or(pc,live)in seen:continue
   seen.add((pc,live));assert 0<=pc<len(words)
   def step(i,values):
    uses,defs=rw(words[i]);explicit.update(uses&values);return values-defs
   w=words[pc];op,rs,rt=w>>26,w>>21&31,w>>16&31;live=step(pc,live)
   if op==3 or(op==0 and w&63==9):
    live=step(pc+1,live);target=((0x15100000+4*pc)&0xf0000000)|((w&0x3ffffff)<<2)if op==3 else'jalr';calls.append(dict(index=pc,target=hex(target)if isinstance(target,int)else target,incoming_arguments_still_live=sorted(live)));continue
   if op in(1,4,5,6,7,20,21,22,23)or(op==17 and rs==8):
    live=step(pc+1,live);dest=pc+1+(((w&65535)^32768)-32768);todo.extend(((dest,frozenset(live)),(pc+2,frozenset(live))))
   elif op==0 and w&63==8:assert rs==31;step(pc+1,live)
   else:todo.append((pc+1,frozenset(live)))
  arity=2 if name=='func_15198110'else 1;assert explicit<=set(range(4,4+arity))
  for call in calls:
   counts={'0x150ada20':0,'0x15183acc':1};assert call['target']in counts
   assert not set(call['incoming_arguments_still_live'])&set(range(4,4+counts[call['target']]))
  rows.append(dict(function=name,observed_argument_words=arity,explicit_entry_arguments_read=sorted(explicit),first_call_frontier=calls,unpassed_entry_arguments_unobserved=True,words=len(words)));print(json.dumps(rows[-1]),flush=True)
 (o/'callback-entry-arity.json').write_text(json.dumps(rows,indent=2)+'\n')

 return rows
