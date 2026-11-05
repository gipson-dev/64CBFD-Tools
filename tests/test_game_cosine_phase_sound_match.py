"""Cosine phase callback: live record reloads, threshold events and original providers."""
from dataclasses import dataclass,replace
import itertools,json,math,struct,subprocess,unittest
from tools.experiments import game_cosine_phase_sound_candidates as candidate
from tools.experiments import game_cosine_phase_sound_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.game_coordinate_query_result_oracle import trunc
from tools.tests.test_game_cosine_match import reference as cosine_reference
from tools.tests.test_game_trig_match import COS_GLOBALS
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=candidate.ROOT;STATE,OTHER,TABLE=0x30000,0x60000,0x80088C90
COS,SOUND,ENGINE=0x15047C00,0x15114D24,0x10010E78
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
VALUES=(0,0x80000000,1,0x80000001,bits(-1.),0x40490FDA,0x40490FDB,0x40490FDC,
        0x40C90FDA,0x40C90FDB,0x40C90FDC,bits(20.),0x7F800000,0xFF800000,0x7FC12345)
RETURNS=(bits(1.),bits(-1.),bits(.5),bits(-.25),0,0x80000000,0x3EAAAAAB,1)
def single(v):
    try:return bits(v)
    except OverflowError:return 0xFF800000 if v<0 else 0x7F800000
def symbols():return dict(D_800BE9E4=0x800BE9E4,D_800A26B0=0x800A26B0,D_800A26B4=0x800A26B4,D_800A26B8=0x800A26B8,cosf=COS,func_15114D24=SOUND)
@dataclass(frozen=True)
class Case:
    phase_word:int=0
    ticks:int=1
    flag:int=0
    old:int=0x3F800000
    returned:int=0x3F800000
    mutation:int=0
    phase:int=0
    state:int=STATE
    actual_cosine:bool=False
    actual_sound:bool=False
def fixture(c=Case(),s=None):
    s=s or symbols();m={STACK+i:(i*17+165)&255 for i in range(-2048,2048)}
    for a in(c.state,OTHER):m.update({a+i:(i*13+91)&255 for i in range(0xA0)})
    for a in(c.state,OTHER):
        put(m,a,c.old);put(m,a+0x7C,c.flag);put(m,a+0x80,c.phase_word);put(m,a+0x74,0xA7,2)
        for off,v in((0x10,-32768),(0x12,32767),(0x14,-1)):put(m,a+off,v,2)
    for name,value in(('D_800BE9E4',c.ticks),('D_800A26B0',0x40490FDB),('D_800A26B4',0x40490FDB),('D_800A26B8',0x40C90FDB)):put(m,s[name],u32(value))
    for a,v in COS_GLOBALS.items():put(m,a,v)
    return m
def cosine_effect(m,c,h,s):
    if c.mutation&1:put(m,c.state,bits(-7.5));put(m,c.state+0x80,bits(8.5));put(m,c.state+0x7C,0x80000000)
    if c.mutation&2:put(m,h,OTHER)
    if c.mutation&4:put(m,s['D_800A26B4'],bits(.25));put(m,s['D_800A26B8'],bits(1.5));put(m,s['D_800BE9E4'],0xFFFFFFFF)
    if c.mutation&8:put(m,c.state+0x60,bits(123.));put(m,c.state+0x74,0xCAFE,2)
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def snapshot(m,p):return tuple(read(m,p+i)for i in(0,0x60,0x7C,0x80))
def reference(initial,c,s=None,home=None,ra=0xDEAD0000):
    s=s or symbols();h=STACK+c.phase if home is None else home;m=dict(initial);p=c.state
    put(m,h-4,ra)
    step=fp(fp(read(m,s['D_800A26B0']),single(float(signed(read(m,s['D_800BE9E4'])))),'mul'),bits(60.),'div')
    put(m,p+0x80,fp(read(m,p+0x80),step,'add'));arg=read(m,p+0x80);put(m,h,p)
    calls=[(s['cosf'],(arg,))];observations=[]
    answer=cosine_reference(arg)if c.actual_cosine else c.returned
    if not c.actual_cosine:cosine_effect(m,c,h,s)
    p=read(m,h);value=fp(answer,bits(10.),'mul');delta=fp(read(m,p),value,'sub')
    flag=read(m,p+0x7C);put(m,p,value);put(m,p+0x60,delta);event=None
    if not flag:
        if floating(read(m,s['D_800A26B4']))<=floating(read(m,p+0x80)):
            put(m,p+0x7C,1);event=0x4CA
    else:
        period=read(m,s['D_800A26B8']);phase=read(m,p+0x80)
        if floating(period)<=floating(phase):
            wrapped=fp(phase,period,'sub');put(m,p+0x7C,0);put(m,p+0x80,wrapped);event=0x4CB
    if event is not None:
        put(m,h-12,4);put(m,h-16,1000)
        calls.append((s['func_15114D24'],(p,event,12000,200,1000,4)));observations.append(snapshot(m,p))
        if c.actual_sound:
            coords=tuple(u32(((read(m,p+off,2)^32768)-32768))for off in(0x10,0x12,0x14))
            calls.append((ENGINE,(read(m,p+0x74,2),event,12000,0,0,0xFFFFFFFF,*coords,200,1000)))
            put(m,p+0x74,0,2)
    return m,calls,observations
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=match.ENTRY,connected=None):
        self.c=c;self.s=s or symbols();self.home=STACK+c.phase;self.observations=[]
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(c.state,))
        self.hi,self.lo,self.condition=0x89ABCDEF,0x76543210,True
    def execute(self,w):
        if w>>26==17 and w>>21&31==16 and w&63 in(7,13):
            self.f[w>>6&31]=(self.f[w>>11&31]^0x80000000)if w&63==7 else trunc(self.f[w>>11&31])
        else:super().execute(w)
    def record_call(self,t):
        s=self.s
        if t==s['cosf']:a=(self.f[12],)
        elif t==s['func_15114D24']:a=tuple(map(u32,self.arguments(6)));self.observations.append(snapshot(self.memory,a[0]))
        elif t==ENGINE:a=tuple(map(u32,self.arguments(11)))
        else:
            assert t==match.ENTRY,('unbounded cosine motion call',hex(t));a=tuple(self.arguments(1));self.home=self.r[29]
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        s,c=self.s,self.c
        if t==s['cosf']:cosine_effect(self.memory,c,self.home,s);value=c.returned
        elif t in(s['func_15114D24'],ENGINE):value=0x87654321
        else:raise AssertionError(('unexpected motion provider',hex(t)))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for k in(1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=u32(value)
        if t==s['cosf']:self.f[0]=value
def state(m):return complete(m),m.trace,m.observations
def controls():
    b=candidate.SELECTED
    return dict(wrong_delta=b.replace('*(f32 *)state - value','value - *(f32 *)state'),
        wrong_tick_sign=b.replace('(f32)D_800BE9E4','(f32)(u32)D_800BE9E4'),
        wrong_divisor=b.replace('/ 60.0f','/ 30.0f'),wrong_amplitude=b.replace('* 10.0f','* 9.0f'),
        wrong_first_threshold=b.replace('D_800A26B4 <=','D_800A26B4 <'),wrong_second_threshold=b.replace('D_800A26B8 <=','D_800A26B8 <'),
        wrong_first_event=b.replace('0x4CA','0x4C9'),wrong_second_event=b.replace('0x4CB','0x4CC'),
        wrong_flag=b.replace('= 1;','= 2;'),wrong_flags=b.replace('1000, 4','1000, 3'),
        stale_period=b.replace('        previous = *(f32 *)(state + 0x80) - D_800A26B8;\n        *(s32 *)(state + 0x7C) = 0;',
            '        *(s32 *)(state + 0x7C) = 0;\n        previous = *(f32 *)(state + 0x80) - D_800A26B8;'))
class GameCosinePhaseSoundMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>66I',cls.rom,match.ROM));text,fs,rs=parse_object(cls.prepared['qualified_compact']);f=fs[match.FUNCTION]
        cls.raw_blob=text[f['value']:f['value']+f['size']];cls.fitted_blob,cls.proof=match.normalized(cls.raw_blob,match.BINDINGS,cls.rom[match.ROM:match.ROM+match.SIZE])
        cls.raw=cls.link(cls.prepared['qualified_compact'],'raw');cls.fitted=cls.link(cls.prepared['qualified_owner'],'fitted')
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context=type('CosinePhaseOriginal',(),dict(root=ROOT,out=cls.out))
        cls.original=ViewListSetupTests.original.__func__(context,'original-cosine-phase',(ROOT/match.ASM).read_text(),match.FUNCTION)
    @classmethod
    def link(cls,obj,label,entry=match.ENTRY,s=None):
        s=s or symbols();text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[match.FUNCTION],rs,match.FUNCTION,s)
        if unknown:raise AssertionError(unknown)
        p=cls.out/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,
            *['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack_from('>66I',sections(p.with_suffix('.elf'))['.text'][1]))
    def receipt(self,n,v):(self.out/(n+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c,initial=None,images=None,s=None,entry=match.ENTRY,connected=None,allow_redirect=False):
        initial=fixture(c,s)if initial is None else initial;models=[];outcomes=[]
        for w in images or(self.retail,self.raw,self.fitted):
            m=Oracle(w,initial,c,s,entry,connected)
            outcome=None
            try:m.run()
            except AssertionError as error:
                if not allow_redirect or not error.args or not isinstance(error.args[0],tuple):raise
                outcome=error.args[0]
                if outcome[0]=='unowned jump':
                    self.assertNotEqual(m.r[31],m.before[31]);self.assertEqual(outcome[1],read(m.memory,STACK+c.phase-4))
                elif outcome[0]!='unmapped read':raise
            models.append(m);outcomes.append(outcome)
        self.assertEqual(outcomes[0],outcomes[2]);self.assertEqual(state(models[0]),state(models[2]))
        if outcomes[0]and outcomes[0][0]=='unmapped read':
            with self.assertRaises(KeyError)as error:reference(initial,c,s)
            self.assertTrue(outcomes[0][1]<=error.exception.args[0]<outcomes[0][1]+outcomes[0][2]);return models
        expected,calls,obs=reference(initial,c,s)
        for m in models:
            self.assertEqual(public(m.memory),public(expected),c);self.assertEqual(m.calls,calls,c);self.assertEqual(m.observations,obs,c)
            for r in(*range(16,24),28,29,30):self.assertEqual(m.r[r],m.before[r])
            self.assertEqual(m.f[20:],m.saved_f)
        self.assertEqual(state(models[0]),state(models[2]));return models
    def test_01_closed_roles_bindings_real_padder_and_full_image(self):
        r=self.prepared['report'];self.assertEqual((r['words'],r['guards'],r['neighbors'],r['relocations']),(66,9,3,11));self.assertEqual(self.retail,self.fitted)
        self.assertEqual(self.proof['FPR_lifetimes'],4)
        for i in range(264):
            bad=bytearray(self.raw_blob);bad[i]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),match.BINDINGS,self.rom[match.ROM:match.ROM+264])
        for at in match.BINDINGS:
            with self.assertRaises(ValueError):match.normalized(self.raw_blob,{**match.BINDINGS,at:[('R_MIPS_LO16','wrong_symbol')]},self.rom[match.ROM:match.ROM+264])
        for index in(0,5,6,8):
            rows=[dict(r)for r in self.prepared['predecessor_rows']]+[match.complete_row(r)for r in match.PATCH_ROWS]
            rows[len(self.prepared['predecessor_rows'])+index]['expected']='0x%08X'%(match.GUARD_WORDS[index][1]^1)
            p=self.out/('wrong-preimage-%d.csv'%index)
            from tools.experiments.game_embedded_dual_phase_position_update_match import write_patches
            write_patches(p,self.prepared['fields'],rows)
            with self.assertRaises(ValueError):emit_padded_assembly(self.prepared['qualified_compact'],ROOT/match.ASM,word_patches_path=p,filename=match.FILENAME)
        before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes()
        for at in(0x80,len(after)-1,0x2B450C,0x2B454C,0x2F6FBE):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.rom[match.ROM:match.ROM+264])
    def test_02_phase_ticks_flags_crossings_and_live_provider_mutations(self):
        count=0;visits=set()
        for phase,ticks,flag,result,mutation,alignment in itertools.product(VALUES,(0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF),
                (0,1,0x80000000),(0,3),(0,7),(0,8)):
            c=Case(phase,ticks,flag,VALUES[(result+4)%15],RETURNS[result],mutation,alignment)
            models=self.compare(c);visits.update(models[0].visits);count+=1
        self.assertEqual(visits,set(range(match.ENTRY,match.ENTRY+264,4)))
        self.receipt('guest-contract',dict(cases_per_body=count,reachable_words=66,all_words_reached=True,nonzero_flag_not_boolean_equality=True,
            signed_ticks_and_single_period_subtraction=True,bounded_float_model_no_hardware_FCSR_claim=True))
    def test_03_constant_aliases_homes_and_period_capture(self):
        count=0
        for field,offset in itertools.product(('D_800BE9E4','D_800A26B0','D_800A26B4','D_800A26B8'),(0,0x60,0x7C,0x80)):
            s=symbols();s[field]=STATE+offset
            images=[self.link(obj,'alias-%s-%X-%d'%(field,offset,j),s=s)for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner']))]
            for phase,flag,mutation in itertools.product((0,8),(0,1),(0,1,7)):
                c=Case(bits(10.),1,flag,returned=bits(.5),mutation=mutation,phase=phase)
                self.compare(c,s=s,images=images);count+=1
        for record,flag,mutation,phase in itertools.product((STACK-0x80,STACK-0x7C,STACK-0x60,STACK-4),
                (0,1),(0,1,7),(0,8)):
            self.compare(Case(bits(10.),1,flag,mutation=mutation,phase=phase,state=record),allow_redirect=True);count+=1
        self.receipt('aliases',dict(cases_per_body=count,full_period_can_alias_flag_and_phase=True,cosine_can_redirect_incoming_record_home=True,
            wrapped_phase_captured_before_flag_store=True))
    def test_04_original_cosine_and_sound_flag4_path(self):
        cosine=dict(zip(range(COS,COS+352,4),struct.unpack_from('>88I',self.rom,0x750B0)))
        sound=dict(zip(range(SOUND,0x15114F04,4),struct.unpack_from('>%dI'%((0x15114F04-SOUND)//4),self.rom,0x1421D4)))
        counts=[0,0]
        for actual_cosine,phase,ticks,flag,alignment in itertools.product((False,True),VALUES[:12],(0,1,5),(0,1),(0,8)):
            c=Case(phase,ticks,flag,actual_cosine=actual_cosine,actual_sound=True,phase=alignment)
            code=dict(sound)
            if actual_cosine:code.update(cosine)
            self.compare(c,connected=code);counts[int(actual_cosine)]+=1
        self.receipt('connected',dict(cases_per_body=counts,original_cosine_slot_words=88,original_sound_words=len(sound),
            sound_flags4_provider=hex(ENGINE),remaining_audio_provider_bounded=True,all_sound_paths_not_claimed=True))
    def test_05_original_installer_and_both_void_dispatch_windows(self):
        count=0;rom=self.rom
        # The original installer transfers the table triple into record fields.
        code=struct.unpack_from('>22I',rom,0xCC06C);c=Case();initial=fixture(c);script=0x70000
        for i in range(32):initial[script+i]=165
        put(initial,script+8,47)
        for j in range(3):put(initial,TABLE+47*12+4*j,struct.unpack_from('>I',rom,0x22D984+4*j)[0])
        m=Oracle(list(code),initial,c,entry=0x1509EBBC);m.r[16]=script;m.r[2]=STATE;m.before=m.r[:]
        m.code=WindowCode(m.code,m);m.code.ends=(0x1509ED5C,)
        with self.assertRaises(WindowBoundary):m.run()
        self.assertEqual((read(m.memory,STATE+0x38),read(m.memory,STATE+0x78),m.memory[STATE+0x92]),(match.ENTRY,0,0))
        windows=((0x15113EE0,0x141390,7,(0x15113EB4,0x15113EFC),0x15113EF0),(0x15113FB8,0x141468,9,(0x15113FDC,),0x15113FC8))
        class PoisonCode(WindowCode):
            def __getitem__(self,pc):
                if pc==self.owner.return_pc:self.owner.r[2]=self.owner.poison;self.owner.hits+=1
                return super().__getitem__(pc)
        for which,phase,flag,poison,loop in itertools.product(range(2),(0,0x40490FDB,0x40C90FDB),(0,1),(0,1,0x80000000,0xFFFFFFFF),(0,1)):
            c=Case(phase,0,flag);initial=fixture(c);put(initial,STATE+0x38,match.ENTRY);put(initial,0x800D23C0,OTHER);put(initial,OTHER+2,0x1234,2)
            expected,calls,obs=reference(initial,c);entry,off,n,ends,return_pc=windows[which];models=[]
            for w in(self.retail,self.raw,self.fitted):
                connected=dict(zip(range(match.ENTRY,match.ENTRY+264,4),w));m=Oracle(list(struct.unpack_from('>%dI'%n,rom,off)),initial,c,entry=entry,connected=connected)
                m.r[16]=STATE;m.r[17]=OTHER;m.r[18]=loop;m.r[23]=0;m.r[30]=0;m.before=m.r[:]
                m.return_pc,m.poison,m.hits=return_pc,poison,0;m.code=PoisonCode(m.code,m);m.code.ends=ends
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,[(match.ENTRY,(STATE,))]+calls);self.assertEqual(m.observations,obs)
                self.assertEqual((m.r[2],m.hits),(poison,1));models.append(m)
            self.assertEqual(state(models[0]),state(models[2]));count+=1
        self.receipt('callers',dict(installer_words=22,registry_row=47,dispatch_cases_per_body=count,window_words=[7,9],void_result_poisoned_four_ways=True,full_parents_not_claimed=True))
    def test_06_literal_fault_prefixes(self):
        count=0
        for c in(Case(),Case(bits(4.),0,0),Case(bits(8.),0,1),Case(bits(2.),1,1,mutation=7),Case(0x7FC12345,phase=8)):
            initial=fixture(c);full=Oracle(self.retail,initial,c).run()
            for cut in range(full.all_accesses):
                models=[]
                for w in(self.retail,self.fitted):
                    m=Oracle(w,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(state(models[0]),state(models[1]));count+=1
        self.receipt('fault-prefixes',dict(fired_prefixes=count,complete_original_fitted_private_state_equal=True,natural_read_order_fault_parity_not_claimed=True))
    def test_07_GNU_rebases_including_relocated_LO16_read(self):
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context=type('CosinePhaseOriginal',(),dict(root=ROOT,out=self.out));original=ViewListSetupTests.original.__func__(context,'original-cosine-phase',(ROOT/match.ASM).read_text(),match.FUNCTION)
        count=links=0
        for index,entry in enumerate((match.ENTRY,0x18017FFC,0x1A028000)):
            s=symbols()
            if index:
                s.update(D_800BE9E4=0x800D7FFC+index*0x10000,D_800A26B0=0x800E8000+index*0x10000,
                    D_800A26B4=0x800F7FFC+index*0x10000,D_800A26B8=0x80108000+index*0x10000,cosf=0x18048000+index*0x1000000,func_15114D24=0x18038000+index*0x1000000)
            images=[self.link(obj,'rebase-%d-%d'%(index,j),entry,s)for j,obj in enumerate((original,self.prepared['qualified_compact'],self.prepared['qualified_owner']))];links+=3
            self.assertEqual(images[0],images[2])
            for phase,flag,mu,alignment in itertools.product((0,0x40490FDB,0x40C90FDB),(0,1),(0,7),(0,8)):
                self.compare(Case(phase,0,flag,mutation=mu,phase=alignment),images=images,s=s,entry=entry);count+=1
        self.receipt('rebases',dict(GNU_links=links,cases_per_body=count,all_11_bindings_including_moved_LO16=True,carry_edges=True))
    def test_08_native32_typed_calls_and_effective_controls(self):
        cases=[Case(phase,ticks,flag,bits(-1.25),answer,mu)for phase,ticks,flag,answer,mu in itertools.product(
            VALUES[:12],(0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF),(0,1,0x80000000),RETURNS[:6],(0,1,4,5,8,13))]
        rows=[('positive-'+opt[1:],candidate.SELECTED,opt,0)for opt in('-O0','-O2','-O3')]
        rows.extend((name,body,'-O2',1)for name,body in controls().items()if name!='stale_period')
        for label,body,opt,expected in rows:
            p=self.out/('native-'+label+'.c');p.write_text(native_source(body,cases));exe=p.with_suffix('.elf')
            built=subprocess.run([*native_command(opt),'-mstackrealign',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            (self.out/('native-'+label+'-diagnostics.txt')).write_text(built.stdout+built.stderr)
            self.assertEqual(built.returncode,0,(built.stdout+built.stderr)[:4000])
            result=subprocess.run([str(exe)],capture_output=True,timeout=60);self.assertEqual(result.returncode,expected,(label,result.stderr))
        self.receipt('native-contract',dict(profiles=['O0','O2','O3'],direct_cases_per_profile=len(cases),typed_cases_per_profile=len(cases),
            controls=len(controls())-1,trap_UBSan=True,only_finite_arithmetic_inputs=True,cosine_provider_bounded=True,stack_home_mutation_not_claimed=True))
    def test_09_actual_IDO_controls_and_period_alias_counterexample(self):
        results={}
        witnesses=[Case(bits(10.),0,0,returned=bits(.5)),Case(0x40490FDB,0,0),Case(0x40C90FDB,0,1),Case(0,0xFFFFFFFF,0),Case(0,0,0,mutation=7)]
        for label,body in controls().items():
            obj,_=candidate.compile_owner(ROOT,self.out,candidate.source_with(body),'control-'+label)
            if label=='stale_period':
                s=symbols();s['D_800A26B8']=STATE+0x7C
                text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/'control-alias';p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%match.ENTRY)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                words=list(struct.unpack_from('>%dI'%(fs[match.FUNCTION]['size']//4),sections(p.with_suffix('.elf'))['.text'][1]))
                corpus=[Case(bits(10.),0,0x40C90FDB)]
            else:
                s=symbols();data,fs=candidate.link_owner(ROOT,self.out,obj,candidate.OWNER);f=fs[match.FUNCTION]
                words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));corpus=witnesses
            found=False
            for c in corpus:
                initial=fixture(c,s);m=Oracle(words,initial,c,s).run();wanted,calls,obs=reference(initial,c,s)
                if public(m.memory)!=public(wanted)or m.calls!=calls or m.observations!=obs:found=True;break
            self.assertTrue(found,label);results[label]=True
        self.receipt('compiled-controls',results)

def native_source(body,cases):
    rows=[]
    for c in cases:
        initial=fixture(c);m,calls,obs=reference(initial,c);p=c.state
        word=lambda v:'0x%Xu'%u32(v)
        prefix=','.join(map(word,(c.phase_word,c.ticks,c.flag,c.old,c.returned,c.mutation,calls[0][1][0],calls[-1][1][1]if len(calls)>1 else 0)))
        final=','.join(map(word,snapshot(m,p)))
        tail=','.join(map(word,(read(m,symbols()['D_800BE9E4']),read(m,symbols()['D_800A26B4']),read(m,symbols()['D_800A26B8']))))
        rows.append('{'+prefix+',{'+final+'},'+tail+'}')
    return '#include <ultra64.h>\n'+candidate.DECLARATIONS+r'''
typedef struct{u32 phase,ticks,flag,old,answer,mutation,arg,event,final[4],ticksAfter,halfAfter,fullAfter;} Fixture;
typedef void(*Handler)(u8*);
static const Fixture cases[]={'''+','.join(rows)+r'''};
static const Fixture *current;
static u8 *record;
static s32 calls,error;
s32 D_800BE9E4;
f32 D_800A26B0,D_800A26B4,D_800A26B8;
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
f32 cosf(f32 argument){
 if(calls++||word(argument)!=current->arg)error=1;
 if(current->mutation&1){*(f32*)record=-7.5f;*(f32*)(record+0x80)=8.5f;*(u32*)(record+0x7C)=0x80000000u;}
 if(current->mutation&4){D_800A26B4=.25f;D_800A26B8=1.5f;D_800BE9E4=-1;}
 if(current->mutation&8){*(f32*)(record+0x60)=123.f;*(u16*)(record+0x74)=0xCAFE;}
 return real(current->answer);
}
s32 func_15114D24(u8*p,s32 event,s32 volume,s16 pan,s16 duration,s32 flags){
 u32 i,values[4]={word(*(f32*)p),word(*(f32*)(p+0x60)),*(u32*)(p+0x7C),word(*(f32*)(p+0x80))};
 if(calls++!=1||p!=record||(u32)event!=current->event||volume!=12000||pan!=200||duration!=1000||flags!=4)error=1;
 for(i=0;i<4;i++)if(values[i]!=current->final[i])error=1;
 return (s32)0xA5A5A5A5u;
}
'''+body+r'''
__attribute__((noinline))static void invoke(Handler fn,u8*p){fn(p);}
static s32 run(void){u32 args[6]={0,4096,3,0x22,0xFFFFFFFFu,0},address,i,j,k,values[4];
 if(sizeof(void*)!=4)return 9;
 __asm__ volatile("int $0x80":"=a"(address):"a"(90),"b"(args):"memory");if(address>=0xFFFFF000u)return 10;record=(u8*)address;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++)for(j=0;j<2;j++){
  current=cases+i;calls=error=0;*(f32*)record=real(current->old);*(u32*)(record+0x7C)=current->flag;*(f32*)(record+0x80)=real(current->phase);
  D_800BE9E4=(s32)current->ticks;D_800A26B0=real(0x40490FDB);D_800A26B4=real(0x40490FDB);D_800A26B8=real(0x40C90FDB);
  if(j)invoke(func_1510ADD8,record);else func_1510ADD8(record);
  values[0]=word(*(f32*)record);values[1]=word(*(f32*)(record+0x60));values[2]=*(u32*)(record+0x7C);values[3]=word(*(f32*)(record+0x80));
  for(k=0;k<4;k++)if(values[k]!=current->final[k])return 1;
  if(error||calls!=(current->event?2:1)||(u32)D_800BE9E4!=current->ticksAfter||word(D_800A26B4)!=current->halfAfter||word(D_800A26B8)!=current->fullAfter)return 1;
 }
 return 0;
}
void _start(void){s32 result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''

if __name__=='__main__':unittest.main()
