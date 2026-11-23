"""Direct actor-linked effect update through both padding implementations."""
from pathlib import Path
import hashlib,json,subprocess,sys
from tools.experiments import game_linked_effect_update_151d1138_match as packet
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
r,o=packet.ROOT,packet.OUT;NAME='func_151D1138';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def assemble(text,path):
 p=path.with_suffix('.s');p.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(p)],capture_output=True,text=True);assert q.returncode==0,q.stderr
def main():
 packet.prepare();s=(o/'baseline/conker/asm/1FA770.s').read_text();a=s.index('glabel '+NAME+'\n');b=s.index('endlabel '+NAME,a)+len('endlabel '+NAME);fragment=s[a:b];(o/'original-target-fragment.s').write_text(fragment)
 assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'\n.size '+NAME+',.-'+NAME+'\n',o/'original-target.o');truth=payload(o/'original-target.o',NAME);raw=payload(o/'selected-final/candidate.o',NAME);assert len(raw[0])==len(truth[0])==496 and raw==truth
 guard=o/'private-guards.csv'
 if 'selected_guards_sha256'in packet.MANIFEST:assert sha(guard)==packet.MANIFEST['selected_guards_sha256']
 assert guard.read_bytes()==(o/'baseline/conker/retail_word_patches.us.csv').read_bytes()+(o/'guard-suffix.csv').read_bytes()
 where=o/'qualified-owner';where.mkdir(exist_ok=True);outputs={}
 for label,text in [('generic',pc.emit_padded_assembly(o/'selected-final/candidate.o',o/'baseline/conker/retail_layout.us.txt','generated_1FA770',word_patches_path=guard)),('generated',pg.emit_padded_assembly(o/'selected-final/candidate.o',o/'baseline/conker/asm/1FA770.s',filename='generated_1FA770',word_patches_path=guard))]:
  p=where/(label+'.o');assemble(text,p);assert payload(p,NAME)==truth;assert same_functions(o/'baseline/conker/build/src/game/generated_1FA770.c.o',p,(NAME,))==51;assert normalized_pools(p)==normalized_pools(o/'baseline/conker/build/src/game/generated_1FA770.c.o');outputs[label]=sha(p)
 from tools.pad_generated_object import parse_object
 assert parse_object(where/'generic.o')==parse_object(where/'generated.o')
 assert same_functions(where/'generic.o',where/'generated.o',())==52
 (where/'generated_1FA770.c.o').write_bytes((where/'generated.o').read_bytes())
 q=dict(raw_words=124,retail_words=124,frame=56,direct_byte_exact=True,normalized_byte_exact=True,guards=packet.MANIFEST['guard_count'],insertions=0,omissions=0,neighbors=51,both_full_owner_text_definitions_bindings_and_pools_equal=True,padder_object_metadata_identical=outputs['generic']==outputs['generated'],padded_owner_sha256=outputs['generated'],source_installed=packet.installed(),matching_credit=0);(o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
