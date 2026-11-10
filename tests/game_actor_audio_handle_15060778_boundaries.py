"""Whole-input checks, stale guards, independent padders and symbol rebases."""
import csv,hashlib,json,struct,sys
from dataclasses import replace
from pathlib import Path
import os
root=Path(os.environ.get("CBFD_CONSUMER_ROOT",Path(__file__).resolve().parents[2])).resolve();base=root/"conker/build/game-actor-audio-15060778-match";out=base/"adoption"
from tools.tests import game_actor_audio_handle_15060778_oracle as game, game_sound_slot_10010be8_oracle as alloc, game_object_audio_10010ffc_oracle as caller
from tools.experiments import game_actor_audio_handle_15060778_match as integrate
from tools.experiments.game_actor_audio_handle_15060778_audit import function_payload
from tools.pad_generated_object import parse_object
from tools import pad_c_object,pad_generated_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
sha=lambda b:hashlib.sha256(b).hexdigest()

def checked(raw,refs,name,d):
 expected={int(k):[tuple(r)for r in v]for k,v in d[name]['source_refs'].items()}
 if sha(raw)!=d[name]['raw_sha256']or refs!=expected:raise ValueError('Stale audio source words or bindings')
 return raw,refs

def bound(path,name,s):return bound_blob(*function_payload(parse_object(path),name),s)

def guards(d):
 mutations=stales=0
 for name,v in d.items():
  owner,n,_,_=integrate.TARGETS[name];obj=out/(name+'-raw.o');raw,refs=function_payload(parse_object(obj),name);checked(raw,refs,name,d)
  for i in range(n):
   b=bytearray(raw);b[4*i+3]^=1
   try:checked(bytes(b),refs,name,d)
   except ValueError:mutations+=1
   else:raise AssertionError((name,i,'word corruption accepted'))
  for offset,entries in refs.items():
   wrong=dict(refs);wrong[offset]=[(kind,symbol+'_stale')for kind,symbol in entries]
   try:checked(raw,wrong,name,d)
   except ValueError:mutations+=1
   else:raise AssertionError((name,offset,'binding corruption accepted'))
  rows=v['rows'];p=out/'stale-guards.csv';layout=out/(name+'-layout.csv');asm=root/('conker/asm/nonmatchings/'+owner+'/'+name+'.s')
  for i,r in enumerate(rows):
   stale=[dict(x)for x in rows];stale[i]['expected']='0x%08X'%(int(r['expected'],16)^1)
   with p.open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(stale)
   for emit in(lambda:pad_c_object.emit_padded_assembly(obj,layout,owner,word_patches_path=p),lambda:pad_generated_object.emit_padded_assembly(obj,asm,filename=owner,word_patches_path=p)):
    try:emit()
    except ValueError as e:assert 'expected'in str(e)or'stale'in str(e).lower();stales+=1
    else:raise AssertionError((name,i,'stale guard accepted'))
 return dict(word_and_binding_corruptions=mutations,stale_guard_rejections=stales,both_padders=True)

def rebases():
 s=alloc.symbols();rom=(root/'conker/conker.us.bin').read_bytes();programs={};executions=0
 for name,(owner,n,at,entry)in integrate.TARGETS.items():
  asm=(root/('conker/asm/nonmatchings/'+owner+'/'+name+'.s')).read_text()
  ref=integrate.assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm+'\n.size '+name+',.-'+name+'\n',name+'-reference')
  assert struct.pack('>%dI'%n,*bound(ref,name,s))==rom[at:at+n*4]
  programs[name]=[out/(name+'-raw.o'),out/(name+'-generic.o'),ref]
 old_game={n:getattr(game,n)for n in('QUERY','UPDATE','SPATIAL','CREATE','POSITION','COUNTS')}
 old_alloc={n:getattr(alloc,n)for n in('TABLE','BANK','MIX','ACTIVE','STOP','RATIO','PLAY','COUNTS')}
 old_caller={n:getattr(caller,n)for n in('TABLE','BUS','ENTRY')}
 try:
  for low in(0,0x7FFC,0x8000,0xFFFC):
   new=dict(s)
   for i,(var,symbol)in enumerate(zip(('QUERY','UPDATE','SPATIAL','CREATE','POSITION'),('func_1001147C','func_1000F85C','func_1000F91C','func_10010BE8','func_10010E78'))):value=0x10100000+i*0x1000;setattr(game,var,value);new[symbol]=value
   game.COUNTS={game.QUERY:1,game.UPDATE:3,game.SPATIAL:10,game.CREATE:7,game.POSITION:11}
   alloc.TABLE=0x80300000+low;alloc.BANK=0x80400000+low;alloc.MIX=0x80500000+low
   for i,(var,symbol)in enumerate(zip(('ACTIVE','STOP','RATIO','PLAY'),('func_100173C4','func_10017594','alCents2Ratio','func_10017438'))):value=0x10200000+i*0x1000;setattr(alloc,var,value);new[symbol]=value
   alloc.COUNTS={alloc.ACTIVE:1,alloc.STOP:1,alloc.RATIO:1,alloc.PLAY:8}
   for name,offset in(('D_800425E0',0),('D_800425E4',4),('D_800425E8',8)):new[name]=alloc.TABLE+offset
   new['D_8003E368']=alloc.BANK;new['D_80041FD8']=alloc.MIX
   caller.TABLE=0x80600000+low;caller.BUS=alloc.MIX+1;caller.ENTRY=0x10014FFC
   new['D_800D1C90']=caller.TABLE;new['D_80041FD9']=caller.BUS
   cases={'func_15060778':[game.Case(flags=0),game.Case(flags=7,mutation=1),game.Case(flags=7,query=-1)],'func_10010BE8':[alloc.Case(),alloc.Case(handle=0x1000,generation=0xFFF0),alloc.Case(matching=False,occupied=65535,active=65535,reserved=65535),alloc.Case(occupied=65535,active=65535,mutation=31)],'func_10010FFC':[caller.Case(camera=0),caller.Case(camera=1),caller.Case(identity=255),caller.Case(actor=0)]}
   for name,paths in programs.items():
    module=game if name=='func_15060778'else alloc if name=='func_10010BE8'else caller
    for path in paths:
     ws=bound(path,name,new)
     for c in cases[name]:
      kwargs={'entry':0x15260778 if module is game else 0x10014BE8}if module is not caller else{}
      m=module.Oracle(ws,module.fixture(c),c,**kwargs);m.run();module.check(m,c);executions+=1
 finally:
  for module,values in((game,old_game),(alloc,old_alloc),(caller,old_caller)):
   for name,value in values.items():setattr(module,name,value)
 return dict(executions=executions,independent_symbol_sets=4,source_normalized_and_original=True,table_aliases_preserved=True)

def main():
 d=json.loads((out/'derivation.json').read_text());r=dict(guards=guards(d),rebases=rebases());(base/'audio-boundaries.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
