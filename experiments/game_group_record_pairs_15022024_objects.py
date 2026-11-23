"""Closed pair lookup normalization through both complete-owner padders."""
import hashlib,json,sys
from tools.experiments import game_group_record_pairs_15022024_match as p
from tools.experiments.game_texture_registration_15195dd4_objects import assemble
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_group_record_pairs_15022024_normalizer import normalize
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
r,o=p.ROOT,p.OUT;NAME=p.FUNCTION;sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def main():
 s=(o/'baseline/conker/asm/49D30.s').read_text();a=s.index('glabel '+NAME+'\n');b=s.index('endlabel '+NAME,a)+len('endlabel '+NAME);fragment=s[a:b];(o/'original-target-fragment.s').write_text(fragment);original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'\n.size '+NAME+',.-'+NAME+'\n';(o/'original-target.s').write_text(original);assemble(original,o/'original-target.o')
 truth=payload(o/'original-target.o',NAME);raw=payload(o/'selected-final/candidate.o',NAME);assert len(raw[0])==348 and len(truth[0])==364 and normalize(*raw)==truth
 where=o/'qualified-owner';where.mkdir(exist_ok=True);outputs={};guard=o/'private-guards.csv'
 for label,text in [('generic',pc.emit_padded_assembly(o/'selected-final/candidate.o',o/'baseline/conker/retail_layout.us.txt','generated_49D30',word_patches_path=guard)),('generated',pg.emit_padded_assembly(o/'selected-final/candidate.o',o/'baseline/conker/asm/49D30.s',filename='generated_49D30',word_patches_path=guard))]:
  f=where/(label+'.o');assemble(text,f);assert payload(f,NAME)==truth;assert same_functions(o/'baseline/conker/build/src/game/generated_49D30.c.o',f,(NAME,))==56;assert normalized_pools(f)==normalized_pools(o/'baseline/conker/build/src/game/generated_49D30.c.o');outputs[label]=sha(f)
 assert len(set(outputs.values()))==1;(where/'generated_49D30.c.o').write_bytes((where/'generic.o').read_bytes())
 q=dict(raw_words=87,raw_frame=8,normalized_words=91,normalized_frame=16,raw_direct_byte_exact=False,normalized_byte_exact=True,guards=87,insertions=6,omissions=2,neighbors=56,both_full_owner_padders_equal=True,padded_owner_sha256=outputs['generic'],source_installed=p.installed(),matching_credit=0);(o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
