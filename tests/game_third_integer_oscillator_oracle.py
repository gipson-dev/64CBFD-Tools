"""Third identical oscillator: fresh linked roots, inherited qualified CPU model."""
import itertools,json,struct
from tools.tests import game_embedded_integer_oscillator_oracle as family
from tools.experiments import game_embedded_integer_oscillator_match as previous

ENTRY,ROM=0x150C673C,0xF3BEC
def __getattr__(name):return getattr(family,name)

def programs(output,target,layout):
    assert target==0
    row=json.loads((output/'layout-v1.json').read_text())['layouts'][layout];entry=row['entry']
    roots=[]
    for label in ('original','raw'):
        image=(output/('layout-%d-%s.elf'%(layout,label))).read_bytes()
        at=family.elf_slot_offset(image,entry,240);roots.append(list(struct.unpack_from('>60I',image,at)))
    normalized=roots[1][:]
    for offset,before,after in previous.PATCHES:
        assert normalized[offset//4]==before;normalized[offset//4]=after
    assert normalized==roots[0]
    return entry,{name:row[name]for name in('clock','integer','floating')},(roots[0],normalized,roots[1])

def qualify(root,output):
    count=0;visits=set();corpus=family.cases()
    for layout in range(3):
        entry,s,roots=programs(output,0,layout)
        for case in corpus:
            initial=family.fixture(case,s);expected,calls,result=family.reference(initial,case,s);models=[]
            for i,words in enumerate(roots):
                m=family.Oracle(words,initial,case,s,entry,raw=i==2).run()
                assert(family.public(m.memory,case),m.calls,family.u32(m.r[2]))==(expected,calls,result),(layout,case)
                models.append(m);visits.update(v-layout*0x1000000 for v in m.visits);count+=1
            assert family.state(models[0])==family.state(models[1])==family.state(models[2])
    assert set(range(ENTRY,ENTRY+240,4))-visits=={ENTRY+0x80}
    prefixes=zero=0;entry,s,roots=programs(output,0,0)
    for case in(family.Case(),family.Case(notification=0,remaining=99,ticks=0),family.Case(notification=255,phase=8,mutation=3),family.Case(mutation=12,phase=8)):
        initial=family.fixture(case,s);full=family.Oracle(roots[0],initial,case,s,entry).run()
        for cut in range(full.all_accesses):
            models=[]
            for i,words in enumerate(roots):
                m=family.Oracle(words,initial,case,s,entry,raw=i==2);m.cut=cut
                try:m.run()
                except family.AccessBoundary:pass
                else:raise AssertionError('Access prefix did not fire')
                models.append(m)
            assert family.state(models[0])==family.state(models[1])==family.state(models[2]);prefixes+=1
    for rng,phase in itertools.product((0,0x80000000,0xFFFFFFFF),(0,8)):
        case=family.Case(rng=rng,phase=phase,mutation=0);initial=family.fixture(case,s);family.put(initial,family.address(case,s)+0xC8,-1,2);models=[]
        for i,words in enumerate(roots):
            m=family.Oracle(words,initial,case,s,entry,raw=i==2)
            try:m.run()
            except family.ZeroDivisor:pass
            else:raise AssertionError('Missing zero-divisor boundary')
            assert m.current_pc==entry+0x6C and m.calls==[(s['integer'],())];models.append(m)
        assert family.state(models[0])==family.state(models[1])==family.state(models[2]);zero+=1
    return dict(success=True,cases=count//3,executions=count,layouts=3,corpus=len(corpus),covered_words=59,access_prefix_triples=prefixes,zero_divisor_preinstruction_triples=zero,private_stack_projection_and_guest_aliases=True,no_hardware_DIVU_zero_or_FCSR_claim=True)

def helpers(root,output):
    rom=(root/'conker/conker.us.bin').read_bytes();image=(root/'conker/build/conker.us.elf').read_bytes();code={}
    for entry,off,n in((family.INTEGER,0xDAED0,18),(family.FLOAT,0xDAF18,25)):
        original=rom[off:off+n*4];at=family.elf_slot_offset(image,entry,n*4);assert image[at:at+n*4]==original
        code.update(zip(range(entry,entry+n*4,4),struct.unpack('>%dI'%n,original)))
    off=family.FACTOR-0x80082B20+0x2275E0;at=family.elf_slot_offset(image,family.FACTOR,4)
    assert image[at:at+4]==rom[off:off+4]==struct.pack('>I',0x37800080)
    count=0;seen=set();entry,s,roots=programs(output,0,0)
    for seed,remaining,ticks,notification,phase in itertools.product((0,1,0xFFFFFFFFFFFFFFFF,0x8000000000000000,0x123456789ABCDEF0,0xFEDCBA9876543210),(-1,0,32767),(0,1,0xFFFFFFFF),(0,255),(0,8)):
        case=family.Case(remaining=remaining,ticks=ticks,notification=notification,phase=phase,seed=seed)
        initial=family.fixture(case,s);expected,calls,result=family.reference(initial,case,s,True);models=[]
        for i,words in enumerate(roots):
            m=family.Oracle(words,initial,case,s,entry,raw=i==2,connected=code).run()
            assert(family.public(m.memory,case),m.calls,family.u32(m.r[2]))==(expected,calls,result)
            models.append(m);seen.update(m.visits);count+=1
        assert family.state(models[0])==family.state(models[1])==family.state(models[2])
    assert set(code)<=seen
    return dict(success=True,cases=count//3,executions=count,original_integer_words=18,original_float_words=25,all43_helper_words_executed=True,retained_helpers_equal_original=True,independent_64bit_seed_reference=True)

def native_reuse(root,output):
    prefix='conker/build/game-embedded-integer-oscillator-150C5E0C-match/'
    selected=(output/'selected-input.c').read_text().replace('func_150C673C','func_150C5E0C')
    frozen=lambda name:(output/('before-'+(prefix+name).replace('/','_'))).read_bytes()
    assert selected==frozen('selected-input.c').decode().replace('\r\n','\n')
    assert(output/'selected-headers.c').read_bytes()==frozen('selected-headers.c')
    native=frozen('native-draft.py')
    public=(output/'before-tools_tests_game_embedded_integer_oscillator_native.py').read_bytes()
    assert native==public
    report=json.loads(frozen('private-native-v14.json'))
    assert report['success']and report['cases_each_target_profile']==818 and report['effective_controls_each']==9
    assert len(report['results'])==30
    assert all((row['status']==0)==(row['label']=='selected')for row in report['results'])
    return dict(success=True,fresh_native_execution=False,explicit_fingerprinted_reuse=True,only_C_function_identifier_changed=True,unchanged_source_headers_cases_providers_and_native_tool=True,prior_targets=2,cases_each_target_profile=818,profiles=['O0','O2','O3'],effective_controls_each=9,UBSan=True)
