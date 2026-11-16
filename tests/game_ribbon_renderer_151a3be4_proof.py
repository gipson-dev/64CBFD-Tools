"""Instruction-driven transfer study; unproved phases remain uncredited."""
from pathlib import Path
from copy import deepcopy
import json,struct,sys
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests import game_side_ring_renderer_1519fe6c_opening_proof as opening
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests.game_ring_emitter_151a37c0_setup_screen import read_epochs
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_ribbon_renderer_151a3be4_recovery as source
O=source.OUT;R=source.ROOT;ENTRY=source.ENTRY
BACKEND,TEXTURE,GEOMETRY,ENV,PRIM,COMBINE,MODE,COPY=0x151D5D60,0x15142E24,0x15142B7C,0x15142C10,0x15142CF0,0x1513F4E4,0x15142FBC,0x10022EC0
COUNTS={BACKEND:5,TEXTURE:11,GEOMETRY:3,ENV:6,PRIM:8,COMBINE:3,MODE:4,COPY:3};SYNC={TEXTURE:9,ENV:5,PRIM:7,COMBINE:2,MODE:3}
OWNER,OUTPUT,RECORDS,PROFILE,EYE,VERTICES=('OWNER',),('OUTPUT',),('RECORDS',),('PROFILE',),('EYE',),('VERTICES',)
SAVED={16:-196,17:-192,18:-188,19:-184,20:-180,21:-176,31:-172}
FP={-248+4*i:('ENTRY_FP',20+(i^1))for i in range(12)}
CUTS={'raw':{0xE4:'forward',0x164:'backward',0x1C4:'graphics',0x96C:'epilogue'},'retail':{0xE8:'forward',0x168:'backward',0x1C8:'graphics',0x96C:'epilogue'}}

class State(opening.State):
 def __init__(self,side,phase):
  super().__init__(side,phase);self.r[4]=OWNER;self.r[5]=OUTPUT;self.r[6]=('VIEW',)
  self.fp=[];self.fp_condition=None
 def load(self,address,size,pool):
  if e.tagged(address,'STACK'):assert all(address[1]+i in self.mem for i in range(size)),('uninitialized private read',self.phase,address,size)
  return super().load(address,size,pool)

class Program(e.Program):
 def __init__(self,words,terms):super().__init__(words,b'',ENTRY);self.terms=terms
 def step(self,s,w):
  op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63
  if op==0 and fn==37 and(s.r[rs]==0 or s.r[rt]==0)and(e.tagged(s.r[rs],'STACK')or e.tagged(s.r[rt],'STACK')):s.r[w>>11&31]=s.r[rs]if s.r[rt]==0 else s.r[rt]
  elif op in(53,61):
   at=e.add(s.r[rs],e.signed((w&65535)|(-65536 if w&32768 else 0)));assert e.tagged(at,'STACK')and at[1]%8==0
   if op==61:s.store(at,4,s.f[rt+1]);s.store(e.add(at,4),4,s.f[rt])
   else:s.f[rt+1]=s.load(at,4,b'');s.f[rt]=s.load(e.add(at,4),4,b'')
  elif op==17 and rs==4:s.f[w>>11&31]=s.r[rt]
  elif op==17 and rs==16:
   fs,fd=w>>11&31,w>>6&31
   if fn==6:s.f[fd]=s.f[fs]
   else:
    assert fn in(0,1,2,3,4,5,7,13,50,60),('unsupported FP',hex(w))
    args=(s.f[fs],s.f[rt])if fn in(0,1,2,3,50,60)else(s.f[fs],)
    event=(fn,args,s.fcsr);s.fp.append(event);s.trace.append(('FP',event))
    value=self.terms.term('FP_VALUE',*event);s.fcsr=self.terms.term('FP_STATUS',*event)
    if fn in(50,60):s.fp_condition=value
    else:s.f[fd]=value
  else:super().step(s,w)
 def call(self,s,t):
  assert t in COUNTS and s.r[29]==('STACK',-296),('provider',hex(t))
  n=COUNTS[t];args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(('STACK',-280+4*i),4,b'')for i in range(max(0,n-4)))
  if t==BACKEND:assert args[3:]==(('STACK',-4),0),('allocator home',args)
  if t in SYNC:assert args[SYNC[t]]==('STACK',-93),('sync home',args)
  for i,a in enumerate(args):
   if not(t==BACKEND and i==3)and not(t in SYNC and i==SYNC[t]):e.plain(a)
  ordinal=s.calls[t];s.calls[t]+=1
  if t==COPY:
   assert args[2]==32 and args[1]==e.add(args[0],-32),('seam copy',args)
   packet=tuple(s.load(e.add(args[1],i),1,b'')for i in range(32))
   s.trace.append(('COPY',t,args,packet,s.fcsr))
   for i,value in enumerate(packet):s.store(e.add(args[0],i),1,value)
  else:s.trace.append(('CALL',t,args,s.fcsr));s.epoch+=1
  for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',t,ordinal,i)
  for i in range(20):s.f[i]=('CALLER_FP',t,ordinal,i)
  for i in range(max(4,n)):s.store(('STACK',-296+4*i),4,('CALL_HOME',t,ordinal,i))
  if t==BACKEND:s.store(('STACK',-4),4,VERTICES)
  if t in SYNC:s.store(('STACK',-93),1,('SYNC_AFTER',t,ordinal))
  s.r[2]=('RESULT',t,ordinal);s.r[31]=('CALL_RETURN',t,ordinal);s.hi=('CALL_HI',t,ordinal);s.lo=('CALL_LO',t,ordinal);s.fcsr=('CALL_FCSR',t,ordinal)
 def paths(self,start,stops,initial):
  active=[(start,initial)];answers={};work=0
  while active:
   pc,s=active.pop();work+=1;s.steps+=1;assert work<30000 and s.steps<600,('unbounded phase',initial.phase,pc,work)
   if s.steps>1 and pc in stops:
    key=(stops[pc],tuple(sorted(s.facts.items(),key=repr)));assert key not in answers,('duplicate path',key);answers[key]=s;continue
   w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31;floating=op==17 and rs==8
   if floating or op in(1,4,5,6,7,20,21,22,23):
    if floating:
     condition=s.fp_condition;assert condition is not None;likely=bool(rt&2)
     if not rt&1:condition=e.negate(condition)
    elif op==1:
     assert rt in(0,1,2,3);condition=e.pred('SLT',s.r[rs],0);likely=rt in(2,3)
     if rt in(1,3):condition=e.negate(condition)
    else:
     if op in(4,5,20,21):condition=e.pred('EQ',s.r[rs],s.r[rt])
     else:assert rt==0;condition=e.pred('SLT',0,s.r[rs])
     if op in(5,21,6,22):condition=e.negate(condition)
     likely=op>=20
    for taken in e.choices(s,condition):
     q=deepcopy(s);e.assume(q,condition,taken)
     if taken or not likely:self.step(q,self.instruction(pc+4))
     active.append((pc+4+4*e.signed((w&65535)|(-65536 if w&32768 else 0))if taken else pc+8,q))
   elif op==3:
    s.r[31]=ENTRY+pc+8;self.step(s,self.instruction(pc+4));self.call(s,((ENTRY+pc+4)&0xF0000000)|((w&0x3FFFFFF)<<2));active.append((pc+8,s))
   elif op==0 and w&63==8:
    target=s.r[rs];self.step(s,self.instruction(pc+4));assert target==('RETURN',);active.append((-4,s))
   else:self.step(s,w);active.append((pc+4,s))
  return answers

def saved(s):
 assert s.r[29]==('STACK',-296)
 for reg,off in SAVED.items():assert s.load(('STACK',off),4,b'')==(('RETURN',)if reg==31 else('ENTRY',reg)),('saved GPR',s.phase,reg)
 for off,value in FP.items():assert s.load(('STACK',off),4,b'')==value,('saved FP',s.phase,off)
 assert all(s.r[i]==('ENTRY',i)for i in(22,23,28,30))

def initial(side,phase):
 s=State(side,phase)
 if phase=='prefix':return s
 s.r[29]=('STACK',-296);s.r[16]=OUTPUT;s.r[17]=OWNER;s.r[18]=RECORDS;s.r[19]=24;s.r[20]=PROFILE;s.r[21]=EYE
 for reg,off in SAVED.items():s.store(('STACK',off),4,('RETURN',)if reg==31 else('ENTRY',reg))
 for off,value in FP.items():s.store(('STACK',off),4,value)
 s.store(('STACK',-4),4,VERTICES);s.store(('STACK',-93),1,1);s.store(('STACK',8),4,('VIEW',));s.r[7]=0 if side=='retail'else('DEAD_A3',)
 if phase=='forward':
  s.r[2]=('INDEX',);s.r[3 if side=='raw'else 4]=('REMAINING',);s.r[4 if side=='raw'else 3]=('FACTOR',)
 elif phase=='backward':s.r[4 if side=='raw'else 2]=('INDEX',);s.r[5]=('REMAINING',);s.r[6]=('FACTOR',)
 s.private_writes=[];return s

def relation(s,end):
 saved(s)
 allowed={(off,4)for off in SAVED.values()}|{(off,4)for off in FP}|{(off,4)for off in range(-296,-252,4)}|{(-4,4),(-93,1),(8,4)}
 assert all(item in allowed for item in s.private_writes),('private write escape',s.phase,s.private_writes)
 assert tuple(s.f[20:])==tuple(('ENTRY_FP',i)for i in range(20,32))
 trace=read_epochs(s.trace)
 if end=='epilogue':return trace,s.fcsr,s.r[16],s.load(('STACK',8),4,b'')
 if s.side=='retail':assert s.r[7]==0,('retail width-argument custody',s.phase,s.r[7])
 common=(trace,s.fcsr,s.r[16],s.r[17],s.r[18],s.r[20],s.r[21],s.load(('STACK',-4),4,b''),s.load(('STACK',-93),1,b''),s.load(('STACK',8),4,b''))
 if end=='graphics':assert s.r[19]==24;return common
 assert s.r[19]==24
 if end=='forward':live=(s.r[2],s.r[3 if s.side=='raw'else 4],s.r[4 if s.side=='raw'else 3])
 else:assert end=='backward';live=(s.r[4 if s.side=='raw'else 2],s.r[5],s.r[6])
 return common,live

def opening_proof(raw,retail):
 reports={}
 for phase in('prefix','forward','backward'):
  terms=Terms();paths={}
  for side,words in(('raw',raw),('retail',retail)):
   start=0 if phase=='prefix'else next(pc for pc,label in CUTS[side].items()if label==phase)
   paths[side]=Program(words,terms).paths(start,CUTS[side],initial(side,phase))
  a,b=paths['raw'],paths['retail'];assert a.keys()==b.keys(),('opening predicates',phase,len(a),len(b),list(a.keys()-b.keys())[:1],list(b.keys()-a.keys())[:1])
  for key in a:
   left,right=relation(a[key],key[0]),relation(b[key],key[0]);assert left==right,('opening transfer',phase,key,left,right)
  reports[phase]=len(a);print(phase,len(a),'passed',flush=True)
 return dict(paths=reports,whole_function=False,source_installed=False,c_match_credit=0)

def programs(label='raw'):
 return source.programs()['raw'],source.retail()

def setup_proof(raw,retail):
 terms=Terms();answers=[]
 for side,words in(('raw',raw),('retail',retail)):
  s=initial(side,'setup');start=next(pc for pc,label in CUTS[side].items()if label=='graphics')
  result=Program(words,terms).paths(start,{0x298:'seed'},s);assert len(result)==1
  relations={}
  for key,q in result.items():
   saved(q);assert tuple(q.f[20:])==tuple(('ENTRY_FP',i)for i in range(20,32))
   assert all((off,sz)in{(x,4)for x in range(-296,-252,4)}|{(-93,1)}for off,sz in q.private_writes),q.private_writes
   assert all(q.calls[t]==1 for t in(TEXTURE,GEOMETRY,ENV,PRIM,COMBINE,MODE))
   assert q.r[16]==('STACK',-93)and q.r[17]==OWNER and q.r[18]==RECORDS and q.r[19]==24 and q.r[20]==PROFILE and q.r[21]==EYE
   relations[key]=(read_epochs(q.trace),q.r[2],q.fcsr,q.load(('STACK',-4),4,b''),q.load(('STACK',-93),1,b''))
  answers.append(relations)
 assert answers[0]==answers[1],('setup transfer',answers)
 return dict(paths=1,opaque_graphics_providers=6,sync_home=-93,cursor_home=-4,arbitrary_public_mutations_and_FCSR=True,whole_function=False,source_installed=False,c_match_credit=0)

def observations(s):
 # Mapped ordinary reads may cross FP operations, whose operands and FCSR
 # order remain exact. Every public store/provider still ends a read epoch.
 effects=tuple(event for event in s.trace if event[0]!='READ')
 epochs=read_epochs([event for event in s.trace if event[0]!='FP'])
 return effects,epochs,s.fcsr

def preserved_fp(s):
 assert all(s.f[i]==('ENTRY_FP',i)for i in range(21,32,2)),('odd FP lifetime',s.phase)
 assert s.f[26]==('ENTRY_FP',26),('unused saved F26 lifetime',s.phase)

def seed_proof(raw,retail):
 terms=Terms();answers=[]
 for side,words in(('raw',raw),('retail',retail)):
  s=initial(side,'seed');s.r[2]=('OUTPUT_AFTER_SETUP',);s.r[16]=('STACK',-93)
  s.store(('STACK',-93),1,('DIRTY',));s.private_writes=[]
  paths=Program(words,terms).paths(0x298,{0x4C4:'first-pair'},s);out={}
  for key,q in paths.items():
   saved(q);preserved_fp(q)
   assert all(size==4 and off in(-80,-76,-72,-68,-64,-60)for off,size in q.private_writes),q.private_writes
   assert q.r[16]==('OUTPUT_AFTER_SETUP',)and q.r[17]==OWNER and q.r[18]==RECORDS and q.r[19]==24 and q.r[20]==PROFILE and q.r[21]==EYE
   assert q.r[12]==('STACK',-68)and q.f[30]==0
   live=(tuple(q.f[i]for i in(18,20,22,6)),q.r[5],q.r[11],q.r[10 if side=='raw'else 9],q.r[9 if side=='raw'else 10],q.r[8],tuple(q.load(('STACK',off),4,b'')for off in(-80,-76,-72,-68,-64,-60)),q.load(('STACK',-4),4,b''),q.load(('STACK',-93),1,b''),q.load(('STACK',8),4,b''))
   out[key]=(observations(q),live)
  answers.append(out)
 a,b=answers;assert a.keys()==b.keys(),('seed predicates',len(a),len(b),list(a.keys()-b.keys())[:1],list(b.keys()-a.keys())[:1])
 for key in a:assert a[key]==b[key],('seed transfer',key,a[key],b[key])
 return dict(paths=len(a),exact_FP_operands_operations_and_FCSR=True,ordinary_read_inventory=True,private_positions=[-80,-68],whole_function=False,source_installed=False,c_match_credit=0)

def geometry_initial(side,phase):
 s=initial(side,phase)
 for i in range(1,16):s.r[i]=('CARRY_%s_G%d'%(side,i),)
 for i in range(20):s.f[i]=('CARRY_%s_F%d'%(side,i),)
 for i in(20,22,24,28,30):s.f[i]=('CARRY_%s_F%d'%(side,i),)
 s.r[24]=('CARRY_%s_G24'%side,);s.r[25]=('CARRY_%s_G25'%side,);s.r[31]=('CARRY_%s_RA'%side,)
 s.hi=('CARRY_%s_HI'%side,);s.lo=('CARRY_%s_LO'%side,)
 for off,label in zip((-80,-76,-72,-68,-64,-60),('A_X','A_Y','A_Z','B_X','B_Y','B_Z')):s.store(('STACK',off),4,(label,))
 s.r[5]=e.bitop('AND',('ALPHA_A',),255);s.r[11]=e.bitop('AND',('PHASE_A',),255)
 s.r[10 if side=='raw'else 9]=e.bitop('AND',('PHASE_B',),255);s.r[9 if side=='raw'else 10]=e.bitop('AND',('ALPHA_B',),255)
 s.r[8]=('INDEX',);s.r[12]=('STACK',-68);s.f[30]=0
 s.store(('STACK',-93),1,e.bitop('AND',('DIRTY',),255));s.private_writes=[]
 return s

def geometry_live(s):
 return(s.r[16],s.r[17],s.r[18],s.r[19],s.r[20],s.r[21],s.r[8],s.r[11],s.r[10 if s.side=='raw'else 9],s.r[9 if s.side=='raw'else 10],s.r[12],s.load(('STACK',-4),4,b''),tuple(s.load(('STACK',off),4,b'')for off in(-80,-76,-72,-68,-64,-60)),s.load(('STACK',-93),1,b''),s.load(('STACK',8),4,b''))

def first_pair_proof(raw,retail):
 terms=Terms();answers=[]
 for side,words in(('raw',raw),('retail',retail)):
  s=geometry_initial(side,'first-pair');s.f[6]=('A_X',)
  for reg,label in((18,'OFFSET_X'),(20,'OFFSET_Y'),(22,'OFFSET_Z')):s.f[reg]=(label,)
  result=Program(words,terms).paths(0x4C4,{0x5FC:'loop-geometry'},s);assert len(result)==1;out={}
  for key,q in result.items():
   saved(q);preserved_fp(q);assert all((off,size)==(-4,4)for off,size in q.private_writes),q.private_writes
   assert q.load(('STACK',-4),4,b'')==e.add(VERTICES,32)and q.r[7]==255 and q.f[8]==('B_X',)and q.f[30]==0
   assert len([v for v in q.trace if v[0]=='WRITE'])==20
   out[key]=(observations(q),geometry_live(q),q.f[8])
  answers.append(out)
 assert answers[0]==answers[1],('first-pair transfer',answers)
 return dict(paths=1,vertices=2,public_stores=20,ordered_FP_and_public_writes=True,whole_function=False,source_installed=False,c_match_credit=0)

def loop_geometry_proof(raw,retail):
 terms=Terms();answers=[]
 for side,words in(('raw',raw),('retail',retail)):
  s=geometry_initial(side,'loop-geometry');s.f[8]=('B_X',);s.r[7]=255
  result=Program(words,terms).paths(0x5FC,{0x6E8:'second-pair'},s);out={}
  for key,q in result.items():
   saved(q);preserved_fp(q);assert not q.private_writes and q.f[30]==0
   assert q.r[2]==OUTPUT and q.r[3]==e.scale(e.bitop('AND',('PHASE_B',),255),64)and q.r[6]==32 and q.r[7]==255,('loop geometry command liveout',q.r[2],q.r[3],q.r[6],q.r[7])
   live=(geometry_live(q),tuple(q.f[i]for i in(18,20,22,4)),q.r[1],q.r[4],q.r[5],q.r[2],q.r[3],q.r[6],q.r[7])
   out[key]=(observations(q),live)
  answers.append(out)
 a,b=answers;assert a.keys()==b.keys(),('loop geometry predicates',len(a),len(b))
 for key in a:assert a[key]==b[key],('loop geometry transfer',key,a[key],b[key])
 return dict(paths=len(a),exact_cross_product_normalization_FP_FCSR=True,ordinary_read_inventory=True,whole_function=False,source_installed=False,c_match_credit=0)

def second_pair_initial(side):
 s=geometry_initial(side,'second-pair');s.f[4]=('B_X',)
 for reg,label in((18,'OFFSET_X'),(20,'OFFSET_Y'),(22,'OFFSET_Z')):s.f[reg]=(label,)
 a=e.bitop('AND',('PHASE_A',),255);b=e.bitop('AND',('PHASE_B',),255)
 s.r[1]=e.boolean(e.pred('SLT',a,b));s.r[2]=OUTPUT;s.r[3]=e.scale(b,64);s.r[4]=b;s.r[5]=a;s.r[6]=32;s.r[7]=255
 return s

def second_pair_proof(raw,retail):
 terms=Terms();answers=[]
 for side,words in(('raw',raw),('retail',retail)):
  s=second_pair_initial(side);paths=Program(words,terms).paths(0x6E8,{0x860:'seam'},s);assert len(paths)==1;out={}
  for key,q in paths.items():
   saved(q);preserved_fp(q);assert all(item==(-4,4)for item in q.private_writes),q.private_writes
   assert q.load(('STACK',-4),4,b'')==e.add(VERTICES,32)and q.r[16]==e.add(OUTPUT,24)and q.r[6]==32 and q.r[7]==255 and q.f[30]==0
   assert len([event for event in q.trace if event[0]=='WRITE'])==26
   out[key]=(observations(q),geometry_live(q),q.r[1],q.r[6],q.r[7])
  answers.append(out)
 assert answers[0]==answers[1],('second pair and commands transfer',answers)
 return dict(paths=1,vertices=2,Gfx_commands=3,public_stores=26,ordered_FP_and_public_writes=True,whole_function=False,source_installed=False,c_match_credit=0)

def seam_initial(side):
 s=geometry_initial(side,'seam');s.r[6]=32;s.r[7]=255
 s.r[1]=e.boolean(e.pred('SLT',e.bitop('AND',('PHASE_A',),255),e.bitop('AND',('PHASE_B',),255)))
 return s

def seam_proof(raw,retail):
 terms=Terms();answers=[]
 for side,words in(('raw',raw),('retail',retail)):
  s=seam_initial(side);paths=Program(words,terms).paths(0x860,{0x8CC:'tail'},s);out={}
  for key,q in paths.items():
   saved(q);preserved_fp(q)
   allowed={(off,4)for off in range(-296,-280,4)}|{(-84,4),(-89,1),(-90,1),(-91,1),(-4,4)}
   assert all(item in allowed for item in q.private_writes),q.private_writes
   assert q.r[7]==255 and q.r[12]==('STACK',-68)and q.f[30]==0
   assert q.load(('STACK',-4),4,b'')==e.add(VERTICES,32 if q.calls[COPY]else 0)
   live=(geometry_live(q),q.r[7],q.f[30])
   out[key]=(observations(q),live)
  answers.append(out)
 a,b=answers;assert a.keys()==b.keys(),('seam predicates',len(a),len(b))
 for key in a:assert a[key]==b[key],('seam copy transfer',key,a[key],b[key])
 return dict(paths=len(a),all_32_copy_bytes=True,source_pair_adjusted_after_copy=True,private_phase_index_lifetime=True,whole_function=False,source_installed=False,c_match_credit=0)

def tail_initial(side):
 s=geometry_initial(side,'tail');s.r[7]=255
 return s

def tail_proof(raw,retail):
 terms=Terms();answers=[]
 for side,words in(('raw',raw),('retail',retail)):
  s=tail_initial(side);paths=Program(words,terms).paths(0x8CC,{0x5FC:'repeat',0x96C:'epilogue'},s);out={}
  for key,q in paths.items():
   saved(q);preserved_fp(q);assert q.r[7]==255 and q.f[30]==0
   assert all(size==4 and off in(-80,-76,-72,-68,-64,-60)for off,size in q.private_writes),q.private_writes
   live=(q.r[16],)if key[0]=='epilogue'else(geometry_live(q),q.f[8])
   if key[0]=='repeat':assert q.f[8]==q.load(('STACK',-68),4,b'')
   out[key]=(observations(q),live)
  answers.append(out)
 a,b=answers;assert a.keys()==b.keys(),('tail predicates',len(a),len(b))
 for key in a:assert a[key]==b[key],('tail transfer',key,a[key],b[key])
 return dict(paths=len(a),index_wrap_and_head_termination=True,loop_live_values_preserved=True,whole_function=False,source_installed=False,c_match_credit=0)

def epilogue_proof(raw,retail,require_identical=True):
 if require_identical:assert raw[-16:]==retail[-16:]
 terms=Terms();answers=[]
 for side,words in(('raw',raw),('retail',retail)):
  s=geometry_initial(side,'epilogue');paths=Program(words,terms).paths(0x96C,{-4:'returned'},s);assert len(paths)==1;out={}
  for key,q in paths.items():
   assert q.r[2]==OUTPUT and q.r[29]==('STACK',0)and q.r[31]==('RETURN',),('epilogue return ABI',q.r[2],q.r[29],q.r[31])
   assert all(q.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and tuple(q.f[20:])==tuple(('ENTRY_FP',i)for i in range(20,32)),('epilogue saved-register restoration',q.r[16:24],q.f[20:])
   assert not q.private_writes and not q.trace
   out[key]=(q.r[2],q.fcsr)
  answers.append(out)
 assert answers[0]==answers[1],('epilogue transfer',answers)
 return dict(paths=1,saved_GPR_FPR_restored=True,private_frame_preserved=True,whole_function=False,source_installed=False,c_match_credit=0)

if __name__=='__main__':
 label=sys.argv[1]if len(sys.argv)>1 else'v7';words=programs(label)
 for name,check in(('opening',opening_proof),('setup',setup_proof),('seed',seed_proof),('first-pair',first_pair_proof),('loop-geometry',loop_geometry_proof),('second-pair',second_pair_proof),('seam',seam_proof),('tail',tail_proof),('epilogue',epilogue_proof)):
  report=check(*words);(O/(name+'-'+label+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(phase=name,**report)),flush=True)
