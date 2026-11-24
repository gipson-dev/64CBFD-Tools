"""Full production owner and strict isolated target through both padders."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
from tools.experiments import game_actor_command_1506e46c_match as p
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_actor_command_1506e46c_normalizer import normalize
r,o=p.ROOT,p.OUT;NAME=p.FUNCTION;sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def assemble(text,path):
 f=path.with_suffix('.s');f.write_bytes(text.encode());q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
def assembly(data,refs):
 text='.set noat\n.set noreorder\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(word,)in enumerate(struct.iter_unpack('>I',data)):
  for kind,n in refs.get(i*4,[]):text+=f'.reloc ., {kind}, {n}\n'
  text+=f'.word 0x{word:08X}\n'
 return text+'.size '+NAME+',.-'+NAME+'\n'
def main():
 p.prepare();s=(o/'baseline/conker/asm/nonmatchings/game_981E0/func_1506E46C.s').read_text();a=s.index('glabel '+NAME+'\n');b=s.index('endlabel '+NAME,a)+len('endlabel '+NAME);fragment=s[a:b];(o/'original-target-fragment.s').write_bytes(fragment.encode());text='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'\n.size '+NAME+',.-'+NAME+'\n';(o/'original-target.s').write_bytes(text.encode());assemble(text,o/'original-target.o');truth=payload(o/'original-target.o',NAME);raw=payload(o/'selected-final/candidate.o',NAME);assert len(raw[0])==380 and len(truth[0])==400 and normalize(*raw)==truth
 guard=o/'private-guards.csv';assert guard.read_bytes()==(o/'baseline/conker/retail_word_patches.us.csv').read_bytes()+(o/'guard-suffix.csv').read_bytes()
 if 'selected_guards_sha256'in p.MANIFEST:assert sha(guard)==p.MANIFEST['selected_guards_sha256']
 where=o/'qualified-owner';where.mkdir(exist_ok=True);full=where/'game_981E0.c.o';assemble(pc.emit_padded_assembly(o/'selected-final/candidate.o',o/'baseline/conker/retail_layout.us.txt','game_981E0',word_patches_path=guard),full);before=o/'baseline/conker/build/src/game_981E0.c.o';assert payload(full,NAME)==truth and same_functions(before,full,(NAME,))==327 and normalized_pools(full)==normalized_pools(before)
 left,right=sections(before),sections(full);assert left['.game_overflow'][1]==right['.game_overflow'][1]and len(left['.game_overflow'][1])==80
 target=where/'raw-target.o';assemble(assembly(*raw),target);lines=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();selected=[v for v in lines if v.split(',')[1:3]==['game_981E0',NAME]];assert len(selected)==1;layout=where/'target-layout.csv';layout.write_bytes((lines[0]+'\n'+selected[0]+'\n').encode());small=where/'target-guards.csv';small.write_bytes(guard.read_bytes().splitlines(keepends=True)[0]+(o/'guard-suffix.csv').read_bytes());outputs={}
 for label,text in(('generic',pc.emit_padded_assembly(target,layout,'game_981E0',word_patches_path=small)),('generated',pg.emit_padded_assembly(target,o/'original-target.s',filename='game_981E0',word_patches_path=small))):
  f=where/(label+'.o');assemble(text,f);assert payload(f,NAME)==truth;outputs[label]=sha(f)
 assert pg.parse_object(where/'generic.o')==pg.parse_object(where/'generated.o')
 q=dict(raw_words=95,retail_words=100,frame=48,direct_byte_exact=False,normalized_byte_exact=True,guards=95,insertions=8,omissions=3,neighbors=327,complete_generic_owner_neighbors_bindings_and_pools_fixed=True,both_strict_isolated_target_padders_byte_exact=True,existing_1506EE60_overflow_bytes_preserved=80,whole_generated_owner_padder_claim=False,padded_owner_sha256=sha(full),source_installed=p.installed(),matching_credit=0);(o/'objects.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
