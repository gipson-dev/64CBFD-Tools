"""Complete state-19/20 callback with one constant-multiply operand guard."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
from tools.experiments import game_impact_phase_150c3994_recovery as old
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD=old.BUILD;OUT=ROOT/BUILD
SOURCE,NAME,ENTRY,ROM,SIZE=old.SOURCE,old.NAME,old.ENTRY,old.ROM,old.SIZE
PREAMBLE=old.PREAMBLE
_OLD='''        actor[0xD0] = 1;
        *(u32 *)(actor + 0xF8) |= 0x01008000;
        *(f32 *)(actor + 0x114) = 500.0f;'''
_NEW='''        *(f32 *)(actor + 0x114) = 500.0f;
        actor[0xD0] = 1;
        *(u32 *)(actor + 0xF8) |= 0x01008000;'''
assert old.BODY.count(_OLD)==1
BODY=old.BODY.replace(_OLD,_NEW)
RAW_SHA256='5a3da9a33d1df37c8c658b4e40a5d3f5bd4158aeab22703a83be4fe05449ac3f'
PATCHES={77:(0x46100482,0x46008482,'constant multiply operand order')}
symbols=old.symbols

def proposed(source):return old.proposed(source).replace(old.BODY,BODY)

def normalize(raw,refs):
    manifest=json.loads(Path(__file__).with_name('game_impact_phase_150c3994_manifest.json').read_text())
    assert len(raw)==SIZE and hashlib.sha256(raw).hexdigest()==RAW_SHA256==manifest['raw_sha256'],'Impact callback compiler body changed'
    assert {str(k):[list(x) for x in v] for k,v in refs.items()}==manifest['raw_relocations'],'Impact callback bindings changed'
    words=list(struct.unpack('>237I',raw))
    for i,(expected,replacement,_) in PATCHES.items():assert words[i]==expected;words[i]=replacement
    return struct.pack('>237I',*words),refs

def programs():
    truth=list(struct.unpack_from('>237I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM))
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
    for i,(expected,replacement,group) in PATCHES.items():
        writer.writerow(dict(filename='game_EF410',function=NAME,offset='0x%03X'%(i*4),expected='0x%08X'%expected,replacement='0x%08X'%replacement,expected_relocations='-',replacement_relocations='-',note='Normalize state-19/20 '+group,insert_after='',insert_after_relocations='',omit='false'))
    (OUT/'proposed-guards.csv').write_bytes((frozen/'conker/retail_word_patches.us.csv').read_bytes()+stream.getvalue().encode())
    for n,h in record['inputs'].items():assert sha(ROOT/n)==(plan.get(n,h) if installed else h),n
    report=dict(installed=installed,body_words=237,frame=80,guards=1,groups=1,bindings=14,neighbors=17,prior_literal_pool_bytes=80,raw_word_differences=1,c_match_credit=int(installed))
    (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
