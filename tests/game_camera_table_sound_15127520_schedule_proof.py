"""Check the two exact call windows and their independent operations.

Domain: the global table object is disjoint from the automatic outgoing
argument word. Raw access order differs; retail/padded fault order is separate.
"""
from pathlib import Path
import itertools,json,struct,sys
from tools.experiments import game_camera_table_sound_15127520_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
SYMS={'D_800894E0':0x800894E0,'D_800A3580':0x800A3580,'func_100111C8':0x100111C8,'func_10010F30':0x10010F30,'func_151CC290':0x151CC290}
def prove(raw,original):
 assert len(raw)==len(original)==164
 assert[i for i,(a,b)in enumerate(zip(raw,original))if a!=b]==[128,129,147,150]
 assert tuple(raw[128:132])==(0x95040002,0xAFA00010,0x0C0043CC,0x00003825)
 assert tuple(original[128:132])==(0xAFA00010,0x95040002,0x0C0043CC,0x00003825)
 assert tuple(raw[147:151])==(0x95040004,0xAFA00010,0x0C0043CC,0x00003825)
 assert tuple(original[147:151])==(0x00003825,0xAFA00010,0x0C0043CC,0x95040004)
 def execute(words,pc,table,stack,value):
  r=[0]*32;r[4]=0xDEADBEEF;r[5]=20000;r[6]=64;r[7]=0xABCDEF01;r[8]=table;r[29]=stack
  m={table+i:0x35 for i in range(6)};m[table+2]=m[table+4]=value>>8;m[table+3]=m[table+5]=value&255
  m.update({stack+16+i:0xA5 for i in range(4)});assert table+6<=stack+16 or stack+20<=table
  for i,w in enumerate(words):
   op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;off=w&65535
   if op==37:r[rt]=(m[r[rs]+off]<<8)|m[r[rs]+off+1]
   elif op==43:
    assert rt==0
    for n in range(4):m[r[rs]+off+n]=0
   elif op==3:r[31]=pc+4*i+8
   else:assert w==0x00003825;r[7]=0
  return tuple(r),m,(r[4],r[5],r[6],r[7],int.from_bytes(bytes(m[stack+16+i]for i in range(4)),'big'))
 checks=0
 for selector,phase,delta,value in itertools.product((0,1),(0,8),(0,0x18020),(0,1,0x8000,0xFFFF)):
  table=0x800894E0+6*selector+delta;stack=0x7FFF0000+phase
  for a,b in((128,132),(147,151)):
   assert execute(raw[a:b],0x15127520+4*a,table,stack,value)==execute(original[a:b],0x15127520+4*a,table,stack,value);checks+=1
 return {'changed_words':4,'exact_window_cases':checks,'non_window_words_identical':160,
  'independence':'LHU writes A0; outgoing SW reads SP/zero; zeroing A3 and JAL link RA do not change the table address. Delayed calls observe the same five arguments.',
  'precondition':'Fixed global table storage is disjoint from the automatic outgoing argument word.',
  'raw_fault_order_claim':False}
def run():
 raw=bound_blob(*payload(out/'qualified-source/candidate.o','func_15127520'),SYMS)
 original=struct.unpack_from('>164I',(root/'conker/conker.us.bin').read_bytes(),0x1549D0);r=prove(raw,original);controls=[]
 for i in(128,129,147,150):
  bad=list(raw);bad[i]^=1;failed=False
  try:prove(bad,original)
  except AssertionError:failed=True
  assert failed;controls.append(i)
 r.update(effective_controls=controls,source_installed=packet.installed(),matching_credit=0)
 (out/'schedule-proof.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':run()
