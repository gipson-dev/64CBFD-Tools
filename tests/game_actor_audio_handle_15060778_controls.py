"""Compiled semantic controls and static closure of uncovered retail words."""
import json,shutil,struct,sys
from pathlib import Path
import os
root=Path(os.environ.get("CBFD_CONSUMER_ROOT",Path(__file__).resolve().parents[2])).resolve();out=root/"conker/build/game-actor-audio-15060778-match"
from tools.tests import game_actor_audio_handle_15060778_oracle as game, game_sound_slot_10010be8_oracle as alloc, game_object_audio_10010ffc_oracle as caller
from tools.experiments.game_remaining_donor_candidates import body,compile_owner
from tools.experiments.game_actor_classifier_candidates import sections

def reachable(ws,entry):
 n=len(ws);branches={};targets=set()
 for i,w in enumerate(ws):
  op,rs,rt=w>>26,w>>21&31,w>>16&31
  if op in(1,4,5,6,7,20,21,22,23)or op==17 and rs==8:
   d=i+1+(((w&65535)^32768)-32768);targets.add(d)
 positive=[]
 for i,w in enumerate(ws):
  if w>>26==1 and w>>16&31==1 and i>=2:
   reg=w>>21&31;load,move=ws[i-2:i]
   if load>>26==37 and load>>16&31==reg and move>>26==17 and move>>21&31==4 and move>>16&31==reg:
    assert i-1 not in targets and i not in targets
    assert i<3 or ws[i-3]>>26 not in(1,2,3,4,5,6,7,20,21,22,23)
    positive.append(i)
 pending=[0];seen=set()
 while pending:
  i=pending.pop()
  if i in seen:continue
  assert 0<=i<n,(i,n);seen.add(i);w=ws[i];op,rs,rt=w>>26,w>>21&31,w>>16&31
  if op==0 and w&63==8:assert rs==31;seen.add(i+1);continue
  if op in(2,3):
   seen.add(i+1)
   if op==3:pending.append(i+2)
   else:pending.append((((entry+4*i+4)&0xF0000000)|((w&0x3FFFFFF)<<2))-entry>>2)
   continue
  if op in(1,4,5,6,7,20,21,22,23)or op==17 and rs==8:
   d=i+1+(((w&65535)^32768)-32768);take=None;likely=op in(20,21,22,23)or op==1 and rt&2 or op==17 and rt&2
   if op in(4,20)and rs==rt:take=True
   elif op in(5,21)and rs==rt:take=False
   elif op in(6,22)and rs==0:take=True
   elif op in(7,23)and rs==0:take=False
   elif i in positive:take=True
   if take is not False:seen.add(i+1);pending.append(d)
   if take is not True:
    if not likely:seen.add(i+1)
    pending.append(i+2)
  else:pending.append(i+1)
 return dict(unreachable=[i for i in range(n)if i not in seen],unsigned_lhu_nonnegative_branches=positive,reachable_words=len(seen))

def mutants(name,p):
 if name=='game':
  substitutions={
   'wrong-mode1-slot':('slot = &arg1->unk8C;','slot = &arg1->unk8E;'),
   'wrong-effect-shift':('>> 3','>> 2'),
   'wrong-mode2-query':('if ((arg6 & 3) == 2)','if ((arg6 & 3) == 1)'),
   'ignored-query-mismatch':('& 0x7FFF) {','| 1) {'),
   'missing-restart-bit':('arg0 |= 0x8000;','arg0 |= 0;'),
   'early-volume-truncation':('func_1000F85C(handle, 8, arg2 + effect * 50);','func_1000F85C(handle, 8, (u16)(arg2 + effect * 50));'),
   'wrong-pitch-scale':('arg1->unk13F * 10','arg1->unk13F'),
   'reloaded-cached-handle':('func_1000F91C(handle,','func_1000F91C(*slot,'),
   'wrong-spatial-bit':('arg6 & 4','arg6 & 2'),
   'wrong-result-handle':('*slot = result;','*slot = result ^ 1;')}
 elif name=='init':
  substitutions={
   'wrong-slot-index':('arg0 & 0xF','arg0 & 7'),
   'wrong-zero-handle-gate':('(arg0 != 0)','(arg0 == 0)'),
   'wrong-reservation-bit':('0x8000','0x4000'),
   'wrong-volume-edge':('arg2 < 100','arg2 < 101'),
   'wrong-sound-limit':('soundId >= 0x6E3','soundId >= 0x6E2'),
   'wrong-sound-mask':('arg1 & 0x7FFF','arg1 & 0x7FFE'),
   'wrong-generation-step':('next = handle + 0x10;','next = handle + 1;'),
   'missing-generation-wrap-skip':('next += 0x10;','next += 0;'),
   'wrong-mix-saturation':('mix |= 0x7F;','mix |= 0x3F;'),
   'signed-global-mix':('(u8)D_80041FD8','D_80041FD8')}
 else:
  substitutions={
   'wrong-active-state-gate':('arg5->interaction_state == 0','arg5->interaction_state == 1'),
   'inverted-camera-gate':('arg5->camera != NULL','arg5->camera == NULL'),
   'wrong-volume-scale':('>> 2','>> 1'),
   'wrong-upper-scale-edge':('scale > 256.0f','scale > 257.0f'),
   'wrong-lower-scale-edge':('scale < 80.0f','scale < 79.0f'),
   'wrong-scale-factor':('scale *= 0.00390625f','scale *= 0.0078125f'),
   'wrong-far-distance':('+ 501','+ 500'),
   'wrong-x-coordinate':('arg5->x_position','arg5->y_position'),
   'wrong-created-return':('return func_10010BE8(','return 1 + func_10010BE8(')}
 result={}
 for label,(a,b)in substitutions.items():assert a in p,(label,a);q=p.replace(a,b);assert q!=p;result[label]=q
 return result

def main():
 s=alloc.symbols();rom=(root/'conker/conker.us.bin').read_bytes();cfg={}
 for name,entry,n,at in(('game',game.ENTRY,174,0x8DC28),('init',alloc.ENTRY,164,0x10BE8),('caller',caller.ENTRY,115,0x10FFC)):
  ws=list(struct.unpack_from('>%dI'%n,rom,at));cfg[name]=reachable(ws,entry)
 assert cfg['game']['unreachable']==[]
 assert cfg['init']['unreachable']==[33,83]
 assert cfg['caller']['unreachable']==[18,47,48,49,68,78],cfg['caller']
 (out/'audio-cfg.json').write_text(json.dumps(cfg,indent=2)+'\n')
 shutil.copyfile(out/'public-audit/proposed-functions.h',out/'proposed-functions.h')
 report={}
 for kind,name,src,oracle in(('game','func_15060778','game-proposal.c',game),('init','func_10010BE8','init-proposal.c',alloc),('caller','func_10010FFC','init-proposal.c',caller)):
  old=(out/'public-audit'/src).read_text();part=body(old,name);cases=oracle.cases();found={}
  for label,p in mutants(kind,part).items():
   obj,_=compile_owner(root,out,old.replace(part,p),'negative-'+kind+'-'+label);sec=sections(obj);syms=dict(s);pool={}
   if '.rodata'in sec:
    syms['.rodata']=0xE0000;pool={0xE0000+i:b for i,b in enumerate(sec['.rodata'][1])}
   ws=alloc.words(obj,syms,name);errors=0
   for i,c in enumerate(cases):
    memory=oracle.fixture(c);memory.update(pool)
    try:m=oracle.Oracle(ws,memory,c);m.run()
    except (AssertionError,KeyError,ValueError,OverflowError):errors+=1;continue
    expected,calls,answer=oracle.reference(m.initial,c)
    different=m.calls!=calls or game.public(m.memory)!=game.public(expected)or(kind!='game'and m.r[2]!=answer)
    if different:found[label]=dict(case=i,normal_completion=True,skipped_execution_errors=errors);break
   assert label in found,('No normal functional witness',kind,label,errors)
   print(kind,label,json.dumps(found[label]),flush=True)
  report[kind]=found
 (out/'audio-controls.json').write_text(json.dumps(report,indent=2)+'\n');print('effective controls',sum(map(len,report.values())),flush=True);return report
if __name__=='__main__':main()
