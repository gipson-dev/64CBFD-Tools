"""Complete normal-execution actor burst relation; private and uninstalled."""
from pathlib import Path
import hashlib,json,os,struct,subprocess
from tools.experiments import game_actor_burst_150bbb5c_recovery as original
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

ROOT=original.ROOT
PACKET=ROOT/'conker/build/game-next-150bbb5c-trail-private'
FROZEN=PACKET/'baseline'
OUT=Path(os.environ.get('CBFD_ACTOR_BURST_150BBB5C_WORK',PACKET/'qualification-primary'))
assert OUT.resolve().is_relative_to((ROOT/'conker/build').resolve())
PIN=json.loads(Path(__file__).with_name('game_actor_burst_150bbb5c_full_manifest.json').read_text())
NAME = original.NAME
SOURCE=original.SOURCE
ENTRY=original.ENTRY
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()

def check_inputs():
    assert sha(FROZEN/'fingerprints.json')==PIN['baseline_manifest_sha256']
    inputs=json.loads((FROZEN/'fingerprints.json').read_text())['inputs']
    assert len(inputs)==1875
    for name,digest in inputs.items():assert sha(ROOT/name)==digest,name
    return len(inputs)

def lookup():return original.lookup()

def recover(before,body=None):
    assert before.count(original.STUB)==1
    return before.replace(original.STUB,PIN['declarations']+'\n'+(PIN['body']if body is None else body))

def refs(rows):return {int(at):[tuple(value)for value in values]for at,values in rows.items()}

def verify_owner(obj):
    raw,bindings=payload(obj,NAME)
    assert hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']
    assert bindings==refs(PIN['refs'])
    return raw,bindings

def qualify_source():
    check_inputs();OUT.mkdir(parents=True,exist_ok=False)
    before=(FROZEN/SOURCE).read_text()
    baseline,diag=compile_owner(ROOT,OUT,before,'baseline');assert not diag,diag
    owner,diag=compile_owner(ROOT,OUT,recover(before),'owner');assert not diag,diag
    assert same_functions(baseline,owner,(NAME,))==8
    assert normalized_pools(baseline)==normalized_pools(owner)
    raw,bindings=verify_owner(owner)
    asm=(FROZEN/'conker/asm/E8C10.s').read_text()
    fragment='glabel '+NAME+'\n'+asm.split('glabel '+NAME+'\n')[1].split('endlabel '+NAME)[0]
    path=OUT/'original.s';path.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'.size '+NAME+',.-'+NAME+'\n')
    q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(path.with_suffix('.o')),str(path)],cwd=ROOT/'conker',capture_output=True,text=True)
    assert q.returncode==0 and not q.stderr,(q.stdout,q.stderr)
    truth,truth_refs=payload(path.with_suffix('.o'),NAME)
    assert hashlib.sha256(truth).hexdigest()==PIN['retail_unbound_sha256']
    assert truth_refs==refs(PIN['retail_refs'])
    raw_words,retail_words=struct.unpack('>591I',raw),struct.unpack('>587I',truth)
    assert 65536-(raw_words[0]&65535)==624
    assert sum(x!=y for x,y in zip(raw_words,retail_words))==569
    state()
    from tools.tests import game_actor_burst_150bbb5c_full_proof as proof
    relation=proof.run();assert relation['passes']and relation['count_pairs']==16 and relation['symbolic_paths']==80
    report=dict(passes=True,raw_words=591,retail_words=587,frame=624,bindings=len(bindings),
        overlapping_word_differences=569,extra_words=4,neighbors_unchanged=8,pools_unchanged=True,
        symbolic_paths=80,full_normal_execution_relation_proved=True,physical_byte_match=False,source_installed=False,c_match_credit=0)
    (OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n')
    check_inputs();return report

def state():
    raw,bindings=verify_owner(OUT/'owner.o')
    truth,truth_refs=payload(OUT/'original.o',NAME)
    assert hashlib.sha256(truth).hexdigest()==PIN['retail_unbound_sha256']
    assert truth_refs==refs(PIN['retail_refs'])
    table=lookup();retail=bound_blob(truth,truth_refs,table)
    assert struct.pack('>587I',*retail)==(FROZEN/'conker/conker.us.bin').read_bytes()[0xE900C:0xE9938]
    return dict(raw=bound_blob(raw,bindings,table),retail=retail)

def full_controls():
    from tools.tests import game_actor_burst_150bbb5c_full_proof as proof
    forms=(
        ('reverse-trail-add', '                position[1] = (*(f32 *)(actor + 0x18) + func_150ADA68() * height) + 5.0f;', '                position[1] = (func_150ADA68() * height + *(f32 *)(actor + 0x18)) + 5.0f;'),
        ('restore-old-trail-order', '                position[2] = *(f32 *)(actor + 0x1C) - radialCosine * trailRadius;\n                velocity[0] = radialCosine * trailSpeed + driftX;\n', '                velocity[0] = radialCosine * trailSpeed + driftX;\n                position[2] = *(f32 *)(actor + 0x1C) - radialCosine * trailRadius;\n'),
        ('restore-old-vector-homes', '    f32 trailRadius;\n    f32 trailSpeed;\n    f32 trailSample;\n    f32 burstSpeed;\n    f32 burstSine;\n    f32 position[3];\n    f32 velocity[3];\n', '    f32 position[3];\n    f32 velocity[3];\n    f32 trailRadius;\n    f32 trailSpeed;\n    f32 trailSample;\n    f32 burstSpeed;\n    f32 burstSine;\n'),
        ('reverse-burst-multiply', 'burstSpeed = *(f32 *)(actor + 0x150) * (func_150ADA68() * 30.0f) + 10.0f;', 'burstSpeed = (func_150ADA68() * 30.0f) * *(f32 *)(actor + 0x150) + 10.0f;'),
        ('restore-old-burst-order', '            descriptor.velocity[0] = horizontalSpeed * burstCosine + driftX;\n            descriptor.velocity[1] = -burstSpeed * pitchCosine;\n            descriptor.velocity[2] = horizontalSpeed * burstSine + driftZ;\n', '            descriptor.velocity[1] = -burstSpeed * pitchCosine;\n            descriptor.velocity[0] = horizontalSpeed * burstCosine + driftX;\n            descriptor.velocity[2] = horizontalSpeed * burstSine + driftZ;\n'),
        ('wrong-sound-z', '(s32)*(f32 *)(actor + 0x1C), 200, 2000);', '(s32)*(f32 *)(actor + 0x18), 200, 2000);'),
        ('remove-factory-ordering-view','*(volatile f32 *)&descriptor.position[1] =','descriptor.position[1] ='),
        ('reverse-factory-add','(*(f32 *)(actor + 0x18) + func_150ADA68() * height)','(func_150ADA68() * height + *(f32 *)(actor + 0x18))'),
        ('remove-ordering-view','*(volatile s16 *)&sprite.y =','sprite.y ='),
        ('unsigned-width','width = *(s16 *)','width = *(u16 *)'),
        ('wrong-sprite-x','sprite.x = (s16)(s32)*(f32 *)(actor + 0x14)','sprite.x = (s16)(s32)*(f32 *)(actor + 0x1C)'),
        ('wrong-color-alpha','func_1516865C(&sprite, 255, 255, 255, 255)','func_1516865C(&sprite, 255, 255, 255, 254)'),
        ('wrong-rejected-return','if (actor[4] != 32) return 1','if (actor[4] != 32) return 0'),
    )
    before=(FROZEN/SOURCE).read_text();rows=[]
    for label,old,new in forms:
        assert old in PIN['body'],label
        owner,diag=compile_owner(ROOT,OUT,recover(before,PIN['body'].replace(old,new)),'prefix-negative-'+label)
        assert not diag,diag
        assert same_functions(OUT/'baseline.o',owner,(NAME,))==8
        assert normalized_pools(OUT/'baseline.o')==normalized_pools(owner)
        try:
            row=proof.run(owner,'negative-'+label)
            assert not row['passes'],('ineffective prefix control',label)
            reason='different ordered FP/call/packet trace'
        except AssertionError as error:
            assert not str(error).startswith("('ineffective prefix control'")
            assert error.args and error.args[0] and isinstance(error.args[0],tuple)
            assert error.args[0][0] in ('public factory reads','factory path predicates differ','factory returned result'),('verifier limitation is not a semantic rejection',label,str(error))
            reason=str(error)[:400]
        rows.append(dict(label=label,effective=True,reason=reason))
    report=dict(passes=True,effective_controls=len(rows),controls=rows,source_installed=False,c_match_credit=0)
    (OUT/'full-controls.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
