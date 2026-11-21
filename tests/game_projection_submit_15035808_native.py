"""SDK32 defined-object cross-check of the private draft's complete public state."""
from pathlib import Path
import sys
from tools.experiments import game_projection_submit_15035808_recovery as recovery
ROOT=recovery.ROOT
import hashlib,json,subprocess
from tools.tests import game_projection_submit_15035808_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
OUT=recovery.OUT
TOKENS={g.COLORS_TOKEN:0xe0000010,g.PRIMARY_TOKEN:0xe0000020,g.SECONDARY_TOKEN:0xe0000030}
def hashed(values):
    h=2166136261
    for v in values:h=((h^v)*16777619)&0xffffffff
    return h
def parts(source=None):
    text=(source or OUT/'qualified-screen/candidate.c').read_text();a=text.index('typedef struct {');b=text.index('} ProjectionDisplayDescriptor61D10;',a)+len('} ProjectionDisplayDescriptor61D10;')
    start=text.index('/* Queue an actor');end=text.index('/* Draw matching projection',start)
    return text[a:b],text[start:end]
def rows():
    rows=[]
    for c in g.cases():
        state=g.Reference(g.fixture(c),c).run()
        trace=[v for target,args in state.trace for v in(target,len(args),*(TOKENS[v]if isinstance(v,str)else v for v in args))]
        memory=g.public(state.memory);public=hashed(memory[a]for a in sorted(memory))
        values=[c.seed,c.mode,c.index,c.count,c.gate,c.pattern,c.effect,c.phase,
            0xffffffff if c.distance_override is None else c.distance_override,hashed(trace),public,len(state.trace),state.allocations]
        rows.append('{'+','.join('0x%Xu'%v for v in values)+'}')
    return ',\n'.join(rows),len(rows)
def source_controls(body):
    cache=body.replace('    Mtx *secondary;','    Mtx *secondary;\n    u8 bufferIndex;')
    cache=cache.replace('                    if (descriptor->cachedMatrices[D_800BE9C0] == 0)',
        '                    bufferIndex = D_800BE9C0;\n                    if (descriptor->cachedMatrices[D_800BE9C0] == 0)')
    cache=cache.replace('cachedMatrices[D_800BE9C0]','cachedMatrices[bufferIndex]')
    return {'wrong-fade-denominator':body.replace('(f32)(distanceLimit - 200));','200.0f);'),
        'late-next-link':body.replace('descriptor = next;','descriptor = descriptor->next;'),
        'cached-allocation-index':cache,
        'late-actor-opacity':body.replace('    if (opacity != 255) factor','    opacity = actor->unk7;\n    if (opacity != 255) factor'),
        'wrong-color':body.replace('record->color[2] = colors[2]','record->color[2] = colors[1]'),
        'wrong-rollback':body.replace('        D_800C3F00--;','        D_800C3F00++;')}

def run(source=None,label='native'):
    assert '/' not in label and '\\' not in label
    where=OUT/label;where.mkdir(exist_ok=True);types,body=parts(source);data,count=rows()
    text=Path(__file__).with_name('game_projection_submit_15035808_native.c.in').read_text().replace('TYPES',types).replace('ROWS',data)
    valid=[];rejected={}
    def execute(name,body,opt):
        p=where/(name+'.c');p.write_text(text.replace('BODY',body));exe=p.with_suffix('')
        q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
        (where/(name+'-compile.log')).write_text(q.stdout+q.stderr);assert q.returncode==0,q.stdout+q.stderr
        q=subprocess.run([str(exe)],capture_output=True,text=True,timeout=90)
        (where/(name+'-run.log')).write_text(q.stdout+q.stderr)
        return q
    for opt in('-O0','-O2','-O3'):
        q=execute(opt[1:],body,opt);assert q.returncode==0,(opt,q.returncode,q.stdout,q.stderr)
        valid.append(dict(optimization=opt,cases=count,strict_aliasing=True,UBSan=True))
    for name,changed in sorted(source_controls(body).items()):
        assert changed!=body,name
        if name=='late-next-link':
            # The intentional late-read defect makes the old captured-next
            # binding dead. Remove only that binding for warning-clean C.
            changed=changed.replace('    ProjectionDisplayDescriptor61D10 *next;\n','').replace('            next = descriptor->next;\n','')
        q=execute(name,changed,'-O2');assert q.returncode in(11,12),(name,q.returncode,q.stderr)
        rejected[name]=dict(exit_code=q.returncode,observation=q.stderr.strip())
    assert len(rejected)==6
    report=dict(valid=valid,rejected=rejected,complete_native_objects=True,full_public_checksum=True,all_19_matrix_arguments=True,
        retained_color_and_primary_secondary_homes=True,exact_private_frame_claim=False,matching_credit=0,
        source=str(source or OUT/'qualified-screen/candidate.c'),body_sha256=hashlib.sha256(body.encode()).hexdigest())
    (OUT/(label+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
