"""Original helper entry-argument liveness across every provider until definition/return."""
from pathlib import Path
import json,re,sys
from tools.experiments import game_actor_ring_emitter_15196b4c_match as p
r=p.ROOT;o=p.OUT
from tools.experiments.game_actor_effect_update_15196748_arity import rw
def main():
 source=(o/'baseline/conker/asm/1C2C60.s').read_text();rows=[]
 for name in('func_15198D88','func_151990AC'):
  fragment=source.split('glabel '+name+'\n',1)[1].split('endlabel '+name,1)[0];words=[int(v,16)for v in re.findall(r'/\*\s*[0-9A-F]+\s+[0-9A-F]+\s+([0-9A-F]{8})\s*\*/',fragment)];todo=[(0,frozenset((4,5,6,7)))];seen=set();explicit=set();calls=[]
  while todo:
   pc,live=todo.pop()
   if not live or(pc,live)in seen:continue
   seen.add((pc,live));assert 0<=pc<len(words)
   def step(i,values):
    uses,defs=rw(words[i]);explicit.update(uses&values);return values-defs
   w=words[pc];op,rs,rt=w>>26,w>>21&31,w>>16&31
   if op==0 and w&63==13:continue
   live=step(pc,live)
   if op==3 or(op==0 and w&63==9):
    live=step(pc+1,live);target=((0x15100000+4*pc)&0xf0000000)|((w&0x3ffffff)<<2)if op==3 else'jalr';calls.append(dict(index=pc,target=hex(target)if isinstance(target,int)else target,incoming_arguments_still_live=sorted(live)));todo.append((pc+2,frozenset(live)));continue
   if op in(1,4,5,6,7,20,21,22,23)or(op==17 and rs==8):
    # Likely-annulment can only remove explicit reads; following both delays
    # is conservative for establishing absence of extra incoming arguments.
    live=step(pc+1,live);dest=pc+1+(((w&65535)^32768)-32768);todo.extend(((dest,frozenset(live)),(pc+2,frozenset(live))))
   elif op==0 and w&63==8:assert rs==31;step(pc+1,live)
   else:todo.append((pc+1,frozenset(live)))
  assert explicit=={4,5},(name,explicit)
  for call in calls:
   arities={'0x150ada68':0,'0x150ada20':0,'0x151423d8':1};assert call['target']in arities,call
   assert not(set(call['incoming_arguments_still_live'])&{6,7}&set(range(4,4+arities[call['target']]))),call
  rows.append(dict(function=name,observed_argument_words=2,explicit_entry_arguments_read=sorted(explicit),all_call_frontiers=calls,argument_liveness_continues_across_calls=True,unpassed_entry_arguments_unobserved=True,return_unused_by_target=True,words=len(words)))
 (o/'callback-entry-arity.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows),flush=True);return rows
