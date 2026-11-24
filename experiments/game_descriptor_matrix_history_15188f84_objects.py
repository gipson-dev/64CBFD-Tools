"""Complete descriptor matrix-history owner through both strict padding implementations."""
from pathlib import Path
import hashlib,json,subprocess,sys
from tools.experiments import game_descriptor_matrix_history_15188f84_match as packet
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_descriptor_matrix_history_15188f84_normalizer import normalize
r,o=packet.ROOT,packet.OUT;NAME=packet.FUNCTION;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def assemble(text,path):
 f=path.with_suffix('.s');f.write_bytes(text.encode());q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
def main():
 packet.prepare();s=(o/'baseline/conker/asm/1B5CC0.s').read_text();a=s.index('glabel '+NAME+'\n');b=s.index('endlabel '+NAME,a)+len('endlabel '+NAME);fragment=s[a:b];(o/'original-target-fragment.s').write_bytes(fragment.encode())
 assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'\n.size '+NAME+',.-'+NAME+'\n',o/'original-target.o');truth=payload(o/'original-target.o',NAME);raw=payload(o/'selected-final/candidate.o',NAME);assert len(raw[0])==404 and len(truth[0])==404 and normalize(*raw)==truth
 guard=o/'private-guards.csv'
 if 'selected_guards_sha256'in packet.MANIFEST:assert sha(guard)==packet.MANIFEST['selected_guards_sha256']
 assert guard.read_bytes()==(o/'baseline/conker/retail_word_patches.us.csv').read_bytes()+(o/'guard-suffix.csv').read_bytes()
 where=o/'qualified-owner';where.mkdir(exist_ok=True);outputs={}
 for label,text in [('generic',pc.emit_padded_assembly(o/'selected-final/candidate.o',o/'baseline/conker/retail_layout.us.txt','generated_1B5CC0',word_patches_path=guard)),('generated',pg.emit_padded_assembly(o/'selected-final/candidate.o',o/'baseline/conker/asm/1B5CC0.s',filename='generated_1B5CC0',word_patches_path=guard))]:
  p=where/(label+'.o');assemble(text,p);assert payload(p,NAME)==truth;assert same_functions(o/'baseline/conker/build/src/game/generated_1B5CC0.c.o',p,(NAME,))==14;assert normalized_pools(p)==normalized_pools(o/'baseline/conker/build/src/game/generated_1B5CC0.c.o');outputs[label]=sha(p)
 assert pg.parse_object(where/'generic.o')==pg.parse_object(where/'generated.o');assert same_functions(where/'generic.o',where/'generated.o',())==15
 (where/'generated_1B5CC0.c.o').write_bytes((where/'generated.o').read_bytes())
 q=dict(raw_words=101,retail_words=101,frame=48,direct_byte_exact=False,normalized_byte_exact=True,guards=101,insertions=0,omissions=0,neighbors=14,both_full_owner_text_definitions_bindings_and_pools_equal=True,padder_object_metadata_identical=outputs['generic']==outputs['generated'],padded_owner_sha256=outputs['generated'],source_installed=packet.installed(),matching_credit=0);(o/'objects.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
