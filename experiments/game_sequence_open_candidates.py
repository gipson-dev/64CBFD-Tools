"""Reproduce private sequence C screens; never install or credit a match.

Both drafts remain unqualified. In particular, the teardown draft retains an
uninitialized local in one helper-mutation scenario; it must not be promoted
without proving or correctly recovering that behavior.
"""
import difflib,hashlib,json,os,subprocess
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import body
from tools.experiments.game_sequence_direction_1501fe68_match import compile_selected
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-open-sequence-screens'
SOURCE='conker/src/game/generated_49D30.c';ASM='conker/asm/49D30.s'
CANDIDATES=json.loads(Path(__file__).with_name('game_sequence_open_candidates.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def payload(path,name):
 data,functions,relocs=parse_object(path);item=functions[name];start=item['value'];size=item['size']
 return data[start:start+size],{i-start:v for i,v in relocs.items() if start<=i<start+size}

def screen():
 OUT.mkdir(parents=True,exist_ok=True);original=(ROOT/SOURCE).read_text();asm=(ROOT/ASM).read_text();results=[]
 baseline,base_diag=compile_selected(ROOT,OUT,original,'baseline')
 for spec in CANDIDATES:
  name=spec['function'];old=body(original,name)
  if old!='s32 '+name+'() {\n    return 0;\n}':raise ValueError('Unexpected live predecessor: '+name)
  source=original.replace(old,spec['candidate'],1)
  if name=='func_1501E81C':source=source.replace('s32 func_1501E81C();','void func_1501E81C(s32, s32);')
  candidate,diag=compile_selected(ROOT,OUT,source,name+'-candidate')
  marker='glabel '+name+'\n';end='endlabel '+name
  snippet=marker+asm.split(marker,1)[1].split(end,1)[0]+end
  src=OUT/(name+'-retail.s');src.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+snippet+'\n.size '+name+',.-'+name+'\n')
  obj=src.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=ROOT/'conker',check=True,capture_output=True)
  raw,refs=payload(candidate,name);retail,rrefs=payload(obj,name)
  ra=[(raw[i:i+4],tuple(refs.get(i,()))) for i in range(0,len(raw),4)]
  rb=[(retail[i:i+4],tuple(rrefs.get(i,()))) for i in range(0,len(retail),4)]
  aligned=sum(a==b for a,b in zip(ra,rb));lcs=sum(x.size for x in difflib.SequenceMatcher(a=ra,b=rb,autojunk=False).get_matching_blocks())
  results.append(dict(function=name,description=spec['description'],candidate_words=len(ra),retail_words=len(rb),aligned_words=aligned,ordered_equal_words=lcs,
   candidate_relocation_sites=len(refs),retail_relocation_sites=len(rrefs),other_functions_unchanged=same_functions(baseline,candidate,(name,)),
   pools_unchanged=normalized_pools(baseline)==normalized_pools(candidate),reginfo_unchanged=sections(baseline)['.reginfo'][1]==sections(candidate)['.reginfo'][1],
   diagnostics_unchanged=diagnostic_rows(base_diag)==diagnostic_rows(diag),installed=False,qualified=False))
 report=dict(source_sha256=sha(ROOT/SOURCE),assembly_sha256=sha(ROOT/ASM),production_elf_sha256=sha(ROOT/'conker/build/conker.us.elf'),
             interpretation='Private screens only; ordered-equal words are not matching credit.',candidates=results)
 (OUT/'screen.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':print(json.dumps(screen(),indent=2))
