"""Compare the original assembly, postprocessed owner and padded retail slot."""
from pathlib import Path
import json,os,subprocess
from tools.experiments import game_huffman_pair_151f8870_restoration as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools import pad_generated_object as pad
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();conker=root/'conker';out=root/source.BUILD
fragment=(root/source.ASSEMBLY).read_text();(out/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'\n.size '+source.FUNCTION+',.-'+source.FUNCTION+'\n')
(out/'proposed-guards.csv').write_bytes((conker/'retail_word_patches.us.csv').read_bytes())
(out/'guarded.s').write_text(pad.emit_padded_assembly(out/'selected.o',conker/'asm/225D20.s',filename='generated_225D20',word_patches_path=out/'proposed-guards.csv'))
for label in ('retail','guarded'):
 subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out/(label+'.o')),str(out/(label+'.s'))],cwd=conker,capture_output=True,check=True)
truth=(conker/'conker.us.bin').read_bytes()[source.ROM:source.ROM+source.BODY_BYTES]
assert all(payload(out/f,source.FUNCTION)==(truth,{}) for f in ('retail.o','selected.o','guarded.o'))
assert same_functions(conker/'build/src/game/generated_225D20.c.o',out/'guarded.o',(source.FUNCTION,))==5
report=dict(body_words=47,alignment_words=0,guards=0,owner_neighbors=5);(out/'object-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
