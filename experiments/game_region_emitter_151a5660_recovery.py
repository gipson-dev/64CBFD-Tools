"""Region emitter semantic recovery and immutable-input qualification."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_path_heading_turn_roles import bound_blob
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2]))
ADOPTION=ROOT/'conker/build/game-next-151a5660-private/adoption'
OUT=Path(os.environ.get('CBFD_REGION_EMITTER_WORK',str(ADOPTION/'qualification-primary')))
assert OUT.resolve().is_relative_to((ROOT/'conker/build').resolve())
FROZEN=ADOPTION/'production-baseline-v4'
PIN=json.loads(Path(__file__).with_name('game_region_emitter_151a5660_manifest.json').read_text())
NAME,SOURCE,ENTRY,ROM,SIZE=PIN['name'],PIN['source'],PIN['entry'],PIN['rom'],1612
def symbols():return dict(PIN['symbols'])
def recover(before):
 stub='s32 func_151A5660() {\n    return 0;\n}'
 assert before.count(stub)==1
 return before.replace(stub,PIN['replacement'])
def installed():
 before=(FROZEN/SOURCE).read_text();live=(ROOT/SOURCE).read_text();assert live in(before,recover(before));return live!=before
def check_inputs():
 record=json.loads((FROZEN/'fingerprints.json').read_text());active=installed()
 plan=json.loads((ADOPTION/'adoption-plan.json').read_text())if active else{}
 if active:assert set(plan)=={SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_1D2B10.c.o','conker/build/conker.us.elf'}
 for name,h in record['inputs'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==plan.get(name,h),name
 return len(record['inputs'])
def retail():
 blob=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert hashlib.sha256(blob).hexdigest()==PIN['retail_sha256'];return list(struct.unpack('>403I',blob))
def compile_and_check():
 check_inputs();OUT.mkdir(parents=True,exist_ok=True);before=(FROZEN/SOURCE).read_text()
 a,ad=compile_owner(ROOT,OUT,before,'baseline');b,bd=compile_owner(ROOT,OUT,recover(before),'qualified');assert not ad and not bd,(ad,bd)
 raw,refs=payload(b,NAME);assert hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']
 assert refs=={int(k):[tuple(v)for v in values]for k,values in PIN['refs'].items()}
 assert same_functions(a,b,(NAME,))==14 and normalized_pools(a)==normalized_pools(b)
 (OUT/'retail.bin').write_bytes(struct.pack('>403I',*retail()));(OUT/'retail.s').write_text((FROZEN/'conker/asm/1D2B10.s').read_text().split('glabel '+NAME+'\n',1)[1].split('endlabel '+NAME,1)[0])
 rom=(ROOT/'conker/conker.us.bin').read_bytes()
 (OUT/'caller-retail.bin').write_bytes(rom[0x176714:0x1767C8]);(OUT/'func_150139AC-factory-retail.bin').write_bytes(rom[0x40E5C:0x410E8])
 elf=(ROOT/'conker/build/conker.us.elf').read_bytes()
 for entry,size in((0x15149264,180),(0x151464B8,80),(0x15046C80,128),(0x15149130,196),(0x151491F4,112)):
  at=elf_slot_offset(elf,entry,size);off=entry-0x14FD2B50;assert elf[at:at+size]==rom[off:off+size]
 at=elf_slot_offset(elf,0x8008A500,4);assert elf[at:at+4]==rom[0x22EFC0:0x22EFC4]==struct.pack('>I',ENTRY)
 (OUT/'proposed-owner.c').write_text(recover(before));report=dict(raw_words=403,frame=264,neighbors_unchanged=14,pools_unchanged=True,source_installed=installed(),c_match_credit=0)
 (OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
def programs():
 from tools.experiments.game_region_emitter_151a5660_match import normalize
 raw,refs=payload(OUT/'qualified.o',NAME);normal,nrefs=normalize(raw,refs)
 return dict(retail=retail(),raw=bound_blob(raw,refs,symbols()),padded=bound_blob(normal,nrefs,symbols()))
if __name__=='__main__':print(json.dumps(compile_and_check()),flush=True)
