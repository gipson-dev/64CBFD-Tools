"""Exit callback with nine checked private descriptor/vector home adjustments."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
from tools.experiments import game_actor_exit_150c3d5c_recovery as old
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-actor-exit-150c3d5c-match';OUT=ROOT/BUILD
SOURCE,NAME,ENTRY,ROM,SIZE=old.SOURCE,old.NAME,old.ENTRY,old.ROM,old.SIZE
BODY,PREAMBLE,proposed,symbols=old.BODY,old.PREAMBLE,old.proposed,old.symbols
PATCHES={
    191:(0xA3A900F4,0xA3A900EC),
    193:(0xA3AA00F5,0xA3AA00ED),
    198:(0xA7AB00F6,0xA7AB00EE),
    199:(0xA3A000F8,0xA3A000F0),
    204:(0xAFAD00E8,0xAFAD00E0),
    209:(0xAFAF00EC,0xAFAF00E4),
    214:(0xAFA800F0,0xAFA800E8),
    229:(0x27A400F4,0x27A400EC),
    230:(0x27A500E8,0x27A500E0),
}

def normalize(raw,refs):
    manifest=json.loads(Path(__file__).with_name('game_actor_exit_150c3d5c_manifest.json').read_text())
    assert len(raw)==SIZE and hashlib.sha256(raw).hexdigest()==manifest['raw_sha256']=='6b9f78a86e13330cafd2a5164810f4e9ad72cf1f546b3f15a8952044575b1589'
    assert {str(k):[list(x) for x in v] for k,v in refs.items()}==manifest['raw_relocations']
    words=list(struct.unpack('>240I',raw))
    for i,(expected,replacement) in PATCHES.items():assert words[i]==expected;words[i]=replacement
    return struct.pack('>240I',*words),refs

def programs():
    truth=list(struct.unpack_from('>240I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM))
    raw,refs=payload(OUT/'recovered.o',NAME);fixed,fr=normalize(raw,refs)
    return truth,bound_blob(raw,refs,symbols()),bound_blob(fixed,fr,symbols())

def main():
    frozen=OUT/'production-baseline';record=json.loads((frozen/'fingerprints.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    before=(frozen/SOURCE).read_text();source=proposed(before);installed=(ROOT/SOURCE).read_text()==source
    plan=json.loads((OUT/'adoption-plan.json').read_text()) if (OUT/'adoption-plan.json').exists() else {}
    for n,h in record['inputs'].items():assert sha(ROOT/n)==(plan.get(n,h) if installed else h),n
    base,d1=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,source,'recovered');assert d1==d2,(d1,d2)
    assert same_functions(base,obj,(NAME,))==17 and normalized_pools(base)==normalized_pools(obj)
    subprocess.run([sys.executable,str(ROOT/'tools/check_motion_effect_150c2c00_pool.py'),str(obj)],cwd=ROOT,check=True)
    truth,raw,fixed=programs();assert fixed==truth
    fields=next(csv.reader(io.StringIO((frozen/'conker/retail_word_patches.us.csv').read_text())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
    for i,(expected,replacement) in PATCHES.items():
        writer.writerow(dict(filename='game_EF410',function=NAME,offset='0x%03X'%(i*4),expected='0x%08X'%expected,replacement='0x%08X'%replacement,expected_relocations='-',replacement_relocations='-',note='Normalize exit descriptor/vector private homes',insert_after='',insert_after_relocations='',omit='false'))
    (OUT/'proposed-guards.csv').write_bytes((frozen/'conker/retail_word_patches.us.csv').read_bytes()+stream.getvalue().encode())
    for n,h in record['inputs'].items():assert sha(ROOT/n)==(plan.get(n,h) if installed else h),n
    report=dict(installed=installed,body_words=240,slot_words=241,frame=256,guards=9,groups=1,bindings=14,neighbors=17,prior_literal_pool_bytes=80,c_match_credit=int(installed))
    (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
