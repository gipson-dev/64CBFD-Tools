"""State-24 callback with recovered halfword heading and eleven local-home guards."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
from tools.experiments import game_actor_motion_150c3574_recovery as old
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-actor-motion-150c3574-match';OUT=ROOT/BUILD
SOURCE,NAME,ENTRY,ROM,SIZE=old.SOURCE,old.NAME,old.ENTRY,old.ROM,old.SIZE
PREAMBLE=old.PREAMBLE
# The current heading is the unsigned halfword read by retail. The square
# expression order recovers IDO's retail FP allocation and complete schedule.
_SQUARES='''    speed = sqrtf(*(f32 *)(actor + 0xBC) * *(f32 *)(actor + 0xBC) +
                  *(f32 *)(actor + 0x148) * *(f32 *)(actor + 0x148));'''
assert old.BODY.count(_SQUARES)==1 and old.BODY.count('    s32 currentHeading;')==1
BODY=old.BODY.replace('    s32 currentHeading;','    u16 currentHeading;').replace(
    _SQUARES,_SQUARES.replace('0xBC','TEMP').replace('0x148','0xBC').replace('TEMP','0x148'))
PATCHES={
    10: (0xE7A40030, 0xE7A40028, 'private floating local homes'),
    50: (0xE7A00030, 0xE7A00028, 'private floating local homes'),
    53: (0xC7A00030, 0xC7A00028, 'private floating local homes'),
    62: (0xE7A00030, 0xE7A00028, 'private floating local homes'),
    114: (0xE7B0002C, 0xE7B00030, 'private floating local homes'),
    120: (0xC7B0002C, 0xC7B00030, 'private floating local homes'),
    141: (0xE7B0002C, 0xE7B00030, 'private floating local homes'),
    145: (0xC7B0002C, 0xC7B00030, 'private floating local homes'),
    162: (0xE7B0002C, 0xE7B00030, 'private floating local homes'),
    166: (0xC7B0002C, 0xC7B00030, 'private floating local homes'),
    188: (0xC7B20030, 0xC7B20028, 'private floating local homes'),
}
RAW_SHA256='5c57ed69838918c71545ea64fd3f5df1d771b1a56ff7ee29a37f654cae2891f3'
symbols=old.symbols

def proposed(source):
    stub=body(source,NAME);assert stub=='s32 func_150C3574() {\n    return 0;\n}'
    result=source.replace(stub,BODY).replace('s32 func_150C3574();\n','')
    result=result.replace('/* Generated placeholder declarations. */',PREAMBLE+'\n/* Generated placeholder declarations. */',1)
    result=result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_EF410/func_150C3574.s. */\n','')
    return result.rstrip()+'\n'

def normalize(raw,refs):
    assert len(raw)==SIZE and hashlib.sha256(raw).hexdigest()==RAW_SHA256,'Actor motion compiler body changed'
    manifest=json.loads(Path(__file__).with_name('game_actor_motion_150c3574_manifest.json').read_text())
    assert {str(k):[list(x) for x in v] for k,v in refs.items()}==manifest['raw_relocations'],'Actor motion relocation set changed'
    words=list(struct.unpack('>264I',raw))
    for i,(expected,replacement,_) in PATCHES.items():
        assert words[i]==expected,(i,words[i]);words[i]=replacement
    return struct.pack('>264I',*words),refs

def programs():
    truth=list(struct.unpack_from('>264I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM))
    raw,refs=payload(OUT/'recovered.o',NAME);fixed,fr=normalize(raw,refs)
    return truth,bound_blob(raw,refs,symbols()),bound_blob(fixed,fr,symbols())

def main():
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();frozen=OUT/'production-baseline'
    record=json.loads((frozen/'fingerprints.json').read_text());before=(frozen/SOURCE).read_text();source=proposed(before)
    installed=(ROOT/SOURCE).read_text()==source;plan=json.loads((OUT/'adoption-plan.json').read_text()) if (OUT/'adoption-plan.json').exists() else {}
    for n,h in record['inputs'].items():assert sha(ROOT/n)==(plan.get(n,h) if installed else h),n
    base,d1=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,source,'recovered');assert d1==d2,(d1,d2)
    assert same_functions(base,obj,(NAME,))==17 and normalized_pools(base)==normalized_pools(obj)
    subprocess.run([sys.executable,str(ROOT/'tools/check_motion_effect_150c2c00_pool.py'),str(obj)],cwd=ROOT,check=True)
    truth,raw,fixed=programs();assert fixed==truth
    fields=next(csv.reader(io.StringIO((frozen/'conker/retail_word_patches.us.csv').read_text())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
    _,refs=payload(obj,NAME)
    for i,(expected,replacement,group) in sorted(PATCHES.items()):
        assert not refs.get(i*4)
        writer.writerow(dict(filename='game_EF410',function=NAME,offset='0x%03X'%(i*4),expected='0x%08X'%expected,replacement='0x%08X'%replacement,expected_relocations='-',replacement_relocations='-',note='Normalize state-24 actor '+group,insert_after='',insert_after_relocations='',omit='false'))
    (OUT/'proposed-guards.csv').write_bytes((frozen/'conker/retail_word_patches.us.csv').read_bytes()+stream.getvalue().encode())
    for n,h in record['inputs'].items():assert sha(ROOT/n)==(plan.get(n,h) if installed else h),n
    report=dict(installed=installed,body_words=264,frame=56,guards=11,groups=1,bindings=len(refs),neighbors=17,prior_literal_pool_bytes=80,raw_word_differences=11,c_match_credit=int(installed))
    (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
