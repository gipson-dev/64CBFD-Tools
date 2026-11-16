"""Retail frame and full private word image, independent of the normalizer."""
from pathlib import Path
import hashlib,json
from tools.tests import game_scaled_argument_packet_151a1010_proof as p
from tools.experiments import game_scaled_argument_packet_151a1010_recovery as m
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
o,r=m.OUT,m.ROOT
class Program(p.Program):
 def call(self,s,target):
  assert self.frame==120
  s.trace.append(('PRIVATE_FRAME_AT_CALL',tuple(s.load(('STACK',off),4,b'')for off in range(-120,0,4))))
  super().call(s,target)
def prove(raw,retail):
 base=p.prove(raw,retail);assert base['raw_frame']==base['retail_frame']==120
 for provider in('retail-stub','opaque-o32'):
  terms=p.Terms();values={}
  for side,words in(('raw',raw),('retail',retail)):
   machine=Program(words,terms,provider);paths=machine.paths(0,{-4:'return'},p.State(side,provider))
   values[side]={key:(p.observable(s,120),tuple(s.load(('STACK',off),4,b'')for off in range(-120,32,4)),tuple(s.r[2:4]))for key,s in paths.items()}
  assert values['raw']==values['retail'],('full private call/return frame',provider)
 return dict(base,original_frame_equal=True,whole_private_word_image_at_call_and_return=True,incidental_integer_result_registers_preserved=True,private_frame_identity=False)
def main():
 m.check_inputs();raw,refs=payload(o/'qualified.o',m.NAME);symbols={'D_800A8D28':p.CONST,'func_151A11CC':p.CALLEE};words=bound_blob(raw,refs,symbols);truth=m.retail();report=prove(words,truth)
 # The private gap write is valid/aligned and leaves the old public/ABI proof
 # passing. The stronger full-frame relation must reject it independently.
 bad=words[:1]+[0xafa00070]+words[1:];assert p.prove(bad,truth)['all28_call_arguments']
 try:prove(bad,truth)
 except AssertionError as error:assert 'full private call/return frame'in str(error);report['unwritten_private_gap_control_rejected']=True
 else:raise AssertionError('unwritten private gap corruption escaped')
 m.check_inputs();report.update(c_match_credit=0,raw_sha256=hashlib.sha256(raw).hexdigest());(o/'frame-proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
