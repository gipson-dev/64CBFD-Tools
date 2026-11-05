"""Alternate point effect: saved mode lifetime, original helper and dispatch."""
from dataclasses import dataclass,replace
import csv,itertools,json,math,struct,subprocess,unittest
from tools.experiments import game_alternate_point_effect_candidates as candidate
from tools.experiments import game_alternate_point_effect_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import emit_padded_assembly
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

ROOT=candidate.ROOT;ACTOR,OTHER,TABLE=0x30000,0x60000,0x8008A0B4
POINT,EFFECT=0x15146890,0x15141F78
RESOLVE,INIT,QUERY=0x15142314,0x1504715C,0x15046C80
u32=lambda v:v&0xFFFFFFFF
signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000
def single(v):
    try:return bits(v)
    except OverflowError:return 0xFF800000 if v<0 else 0x7F800000
def product(a,b):return single(floating(a)*floating(b))
def converted(word):
    value=floating(word)
    if not math.isfinite(value):return 255
    n=math.trunc(value);return n&255 if 0<=n<2**32 else 255
VALUES=(0,0x80000000,1,0x80000001,bits(.75),bits(-.75),bits(255.75),bits(256.75),
        0x4EFFFFFF,0x4F000000,0x4F7FFFFF,0x4F800000,0xCF000000,0x7F800000,0xFF800000,0x7FC12345)
@dataclass(frozen=True)
class Case:
    active:int=0x50000
    mode:int=1
    amount:int=85
    value:int=0x3F800000
    first:int=0x3C40C0C1
    second:int=0x3F360B61
    answer:int=1
    mutation:int=0
    phase:int=0
    fcsr:int=0
    actor:int=ACTOR
    connected:bool=False
def syms(a=0x800A5728,b=0x800A572C,point=POINT,effect=EFFECT):
    return dict(D_800A5728=a,D_800A572C=b,func_15146890=point,func_15141F78=effect)
def fixture(c=Case(),s=None):
    s=s or syms();m={STACK+i:(i*17+165)&255 for i in range(-1024,1024)}
    for a in(c.actor,OTHER):m.update({a+i:(i*13+91)&255 for i in range(0x340)})
    put(m,c.actor+0x1D4,c.active);put(m,c.actor+0x40,c.value);put(m,OTHER+0x40,bits(3.75))
    put(m,s['D_800A5728'],c.first);put(m,s['D_800A572C'],c.second)
    return m
def packet(m,p,n):return bytes(m[p+i]for i in range(n))
def fill(m,p,r):
    for i,w in enumerate((bits(1.25),bits(-2.5),bits(3.75))):put(m,p+4*i,w)
    for i in range(36):m[r+i]=(i*29+0x31)&255
def effect(m,c,home,s):
    if c.mutation&1:put(m,c.actor+0x40,bits(27.5));put(m,s['D_800A5728'],bits(.5));put(m,s['D_800A572C'],bits(2.))
    if c.mutation&2:put(m,home,OTHER);put(m,home+8,0xFFFFFF85)
    if c.mutation&4:put(m,home+4,0x123400FF)
    if c.mutation&8:put(m,c.actor+0x1D4,0)
def reference(initial,c,ra,s=None,home=None,point_connected=False):
    s=s or syms();h=STACK+c.phase if home is None else home;m=dict(initial)
    for at,v in((-60,ra),(0,c.actor),(4,c.mode),(8,c.amount)):put(m,h+at,u32(v))
    mode=read(m,h+7,1);actor=read(m,h);calls=[];observations=[]
    if read(m,actor+0x1D4):
        p,r=h-12,h-48;put(m,h-52,mode);calls.append((s['func_15146890'],(p,actor,r,mode)))
        if point_connected:
            if mode not in(1,2):return m,calls,observations
            calls.append((RESOLVE,(read(m,actor+0x1D4),19 if mode==1 else 23,p)))
            for i,w in enumerate((bits(1.25),bits(-2.5),bits(3.75))):put(m,p+4*i,w)
            calls.append((INIT,(r,actor)))
            start=h-100
            for i,w in enumerate((bits(1.25),bits(7.5),bits(3.75))):put(m,start+4*i,w)
            for i in range(36):m[r+i]=(i*29+0x31)&255
            calls.append((QUERY,(start,0,bits(-52.5),r)))
        else:fill(m,p,r);effect(m,c,h,s)
        if c.answer:
            amount=read(m,h+8);actor=read(m,h)
            scale=product(single(float(signed(amount))),read(m,s['D_800A5728']))
            tag=converted(product(read(m,actor+0x40),read(m,s['D_800A572C'])))
            calls.append((s['func_15141F78'],(10,r,scale,tag,p,read(m,h-52))))
            observations.append((packet(m,r,36),packet(m,p,12)))
    return m,calls,observations
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=match.ENTRY,connected=None):
        self.c=c;self.s=s or syms();self.home=STACK+c.phase;self.observations=[]
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(c.actor,u32(c.mode),u32(c.amount)))
        self.fcsr=self.initial_fcsr=c.fcsr;self.hi,self.lo,self.condition=0x89ABCDEF,0x76543210,True
    def execute(self,w):
        op,rs,fn=w>>26,w>>21&31,w&63
        if op==17 and(rs in(2,6)or(rs==16 and fn==36)):AreaOracle.execute(self,w)
        elif op==17 and rs==16 and fn==2:self.f[w>>6&31]=product(self.f[w>>11&31],self.f[w>>16&31])
        else:super().execute(w)
    def record_call(self,t):
        s=self.s;counts={match.ENTRY:3,s['func_15146890']:4,s['func_15141F78']:6,RESOLVE:3,INIT:2,QUERY:4}
        if t not in counts:raise AssertionError(('unbounded interval effect helper',hex(t)))
        a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
        if t==match.ENTRY:self.home=self.r[29]
        if t==s['func_15141F78']:
            self.observations.append((packet(self.memory,a[1],36),packet(self.memory,a[4],12)))
            self.assert_control()
    def assert_control(self):
        assert self.fcsr==self.initial_fcsr,('temporary conversion control leaked',self.fcsr,self.initial_fcsr)
    def hook(self,t):
        c,s=self.c,self.s;a=self.calls[-1][1];value=0x12345678
        if t==s['func_15146890']:fill(self.memory,a[0],a[2]);effect(self.memory,c,self.home,s);value=u32(c.answer)
        elif t==RESOLVE:
            for i,w in enumerate((bits(1.25),bits(-2.5),bits(3.75))):put(self.memory,a[2]+4*i,w)
        elif t==INIT:
            for i in range(36):self.memory[a[0]+i]=(i*29+0x31)&255
        elif t==QUERY:value=u32(c.answer)
        else:assert t==s['func_15141F78']
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=value
def state(m):return complete(m),m.trace,m.fcsr,m.observations

def controls():
    b=candidate.SELECTED
    return dict(wrong_gate=b.replace('== 0) return','!= 0) return'),
        wrong_point_mode=b.replace('&result, selected)','&result, selected + 1)'),
        inverted_result=b.replace('&result, selected) != 0','&result, selected) == 0'),
        wrong_slot=b.replace('func_15141F78(10,','func_15141F78(9,'),
        wrong_scale=b.replace('(f32)amount * D_800A5728','(f32)amount * D_800A572C'),
        wrong_tag_constant=b.replace('0x40) * D_800A572C','0x40) * D_800A5728'),
        wrong_mode=b.replace('position, selected);','position, selected + 1);'),
        cached_tag=b.replace('    f32 position[3];','    f32 cached = *(f32 *)(actor + 0x40);\n    f32 position[3];').replace('*(f32 *)(actor + 0x40) * D_800A572C','cached * D_800A572C'))

class GameAlternatePointEffectMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>73I',cls.rom,match.ROM))
        linked,functions=candidate.link_owner(ROOT,cls.out,cls.prepared['qualified_owner'],candidate.OWNER)
        cls.words=list(struct.unpack_from('>73I',linked,functions[match.FUNCTION]['value']))
    def receipt(self,name,value):(self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    def compare(self,c,initial=None,images=None,s=None,entry=match.ENTRY,connected=None,allow_redirect=False):
        initial=fixture(c,s)if initial is None else initial;models=[]
        for w in images or(self.retail,self.words):
            m=Oracle(w,initial,c,s,entry,connected)
            try:m.run()
            except AssertionError as exc:
                if not allow_redirect or not exc.args or not isinstance(exc.args[0],tuple)or exc.args[0][0]!='unowned jump':raise
                self.assertNotEqual(m.r[31],m.before[31]);self.assertEqual(exc.args[0][1],read(m.memory,STACK+c.phase-60))
            m.assert_control();models.append(m)
        expected,calls,observations=reference(initial,c,models[0].before[31],s,point_connected=bool(connected))
        for m in models:
            self.assertEqual(public(m.memory),public(expected),c);self.assertEqual(m.calls,calls,c);self.assertEqual(m.observations,observations,c)
            self.assertEqual(m.r[29],STACK+c.phase)
        self.assertEqual(state(models[0]),state(models[1]));return models
    def test_01_saved_mode_lifetime_owner_full_slot_image_and_corruption_controls(self):
        r=self.prepared['report'];self.assertEqual((r['words'],r['slot_words'],r['frame'],r['guards'],r['neighbors'],r['relocations']),(73,73,88,2,12,6))
        self.assertEqual(self.words,self.retail);raw,bindings=match.function_blob(self.prepared['qualified_compact']);truth=match.original_bytes(ROOT)
        linked,fs=candidate.link_owner(ROOT,self.out,self.prepared['qualified_compact'],candidate.OWNER)
        natural=list(struct.unpack_from('>73I',linked,fs[match.FUNCTION]['value']))
        for c in(Case(),Case(active=0),Case(mode=255),Case(answer=0),Case(mode=2,mutation=1,amount=32767)):
            initial=fixture(c);model=Oracle(natural,initial,c).run();expected,calls,observations=reference(initial,c,model.before[31])
            self.assertEqual((public(model.memory),model.calls,model.observations),(public(expected),calls,observations))
        for at in range(len(raw)):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.checked_payload(bytes(bad),bindings,truth)
        for at in bindings:
            with self.assertRaises(ValueError):match.checked_payload(raw,{**bindings,at:[(bindings[at][0][0],'wrong_symbol')]},truth)
        rows=self.prepared['qualified_rows'];checked=0
        for i,row in enumerate(rows):
            if row['function']!=match.FUNCTION:continue
            bad=[dict(r)for r in rows];bad[i]['expected']='0x00000000';path=self.out/'bad-preimage.csv'
            match.harness.write_patches(path,self.prepared['fields'],bad)
            with self.assertRaises(ValueError):emit_padded_assembly(self.prepared['qualified_compact'],ROOT/match.ASM,word_patches_path=path,filename=match.FILENAME)
            checked+=1
        self.assertEqual(checked,2)
        before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes()
        for at in(0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,match.SLOT_SIZE)+match.SIZE):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
    def test_02_all_mode_bytes_gate_return_signed_scale_tag_and_FCSR(self):
        count=0;visits=set()
        for mode,active,answer,phase in itertools.product(range(256),(0,0x50000),(0,1),(0,8)):
            c=Case(mode=0xABCD0000|mode,active=active,answer=answer,phase=phase,amount=u32(mode*0x1234567),value=VALUES[mode%16],fcsr=(0,3,0xA5A50003)[mode%3])
            ms=self.compare(c);visits.update(ms[0].visits);count+=1
        for amount,value,const,answer,fcsr,mode in itertools.product((0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF),VALUES,(0x3F800000,0x3F360B61),(0,0x80000000),(0,0x00801004),(1,2)):
            c=Case(mode=mode,amount=amount,value=value,second=const,answer=answer,fcsr=fcsr)
            ms=self.compare(c);visits.update(ms[0].visits);count+=1
        unreachable={match.ENTRY+0xE8}
        self.assertEqual(visits,set(range(match.ENTRY,match.ENTRY+match.SIZE,4))-unreachable)
        self.receipt('guest-contract',dict(cases_per_body=count,reachable_words=len(visits),unreachable_duplicate=hex(match.ENTRY+0xE8),all_mode_bytes=True,
            bounded_nontrapping_conversion_model=True,hardware_FCSR_exception_and_NaN_payload_claimed=False))
    def test_03_private_homes_and_ordered_aliases(self):
        count=redirects=0
        for mutation,mode,phase in itertools.product(range(16),(1,2,0xAABBCCFF),(0,8)):
            self.compare(Case(mutation=mutation,mode=mode,phase=phase));count+=1
        for actor,mode,mutation,phase in itertools.product((STACK-12-0x40,STACK-48-0x40,STACK-52-0x40),
                (1,2),(0,1,4,8),(0,8)):
            ms=self.compare(Case(actor=actor,mode=mode,mutation=mutation,phase=phase),allow_redirect=True)
            redirects+=ms[0].r[31]!=ms[0].before[31];count+=1
        self.receipt('aliases',dict(cases_per_body=count,incoming_actor_amount_can_change=True,mode_snapshot_local_can_be_overwritten=True,
            actor_tag_can_alias_position_result_or_mode_local=True,redirected_alias_returns=redirects))
    def test_04_connected_original_point_interval_helper(self):
        code=dict(zip(range(POINT,POINT+224,4),struct.unpack_from('>56I',self.rom,0x173D40)));count=0
        for active,mode,answer,phase in itertools.product((0,0x50000),(0,1,2,255),(0,1,0xFFFFFFFF),(0,8)):
            self.compare(Case(active=active,mode=mode,answer=answer,phase=phase,connected=True),connected=code);count+=1
        self.receipt('connected',dict(cases_per_body=count,original_point_helper_words=56,resolver_initializer_query_bounded=True,no_new_helper_credit=True))
    def test_05_original_dispatch_windows_and_retail_positive_count_route(self):
        counts=[0,0]
        for which,mode,amount,active,answer,phase in itertools.product(range(2),(1,2,0xABCD00FF),(-32768,0,85,32767),(0,0x50000),(0,1),(0,8)):
            c=Case(mode=mode,amount=u32(0 if which==0 else amount),active=active,answer=answer,phase=phase);initial=fixture(c)
            put(initial,TABLE+3*8,match.ENTRY);put(initial,TABLE+3*8+4,85);record=0x70000
            for i in range(64):initial[record+i]=165
            put(initial,record+14,amount,2);entry,rom,n,end=(0x15141B4C,0x16EFFC,5,0x15141B60)if which==0 else(0x15141BAC,0x16F05C,8,0x15141BCC)
            models=[]
            for w in(self.retail,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+match.SIZE,4),w));code[end]=0
                m=Oracle(list(struct.unpack_from('>%dI'%n,self.rom,rom)),initial,c,entry=entry,connected=code)
                m.r[18]=c.actor;m.r[19]=u32(mode);m.r[16]=TABLE;m.r[14]=TABLE+3*8;m.r[12]=3;m.r[2]=record
                m.code=WindowCode(m.code,m);m.code.ends=(end,)
                with self.assertRaises(WindowBoundary):m.run()
                ra=entry+(20 if which==0 else 32);expected,calls,observations=reference(initial,c,ra)
                self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,[(match.ENTRY,(c.actor,u32(mode),c.amount))]+calls)
                self.assertEqual(m.observations,observations);models.append(m)
            self.assertEqual(state(models[0]),state(models[1]));counts[which]+=1
        # With this callback's real +85 count, the earlier classifier route
        # creates/refreshes a timed record rather than calling the first window.
        entry,rom,n,end=0x15141B28,0x16EFD8,14,0x15141B60
        initial=fixture();put(initial,TABLE+3*8+4,85)
        m=Oracle(list(struct.unpack_from('>%dI'%n,self.rom,rom)),initial,entry=entry)
        m.r[3]=TABLE+3*8;m.r[7]=3;m.r[18]=ACTOR;m.r[16]=TABLE;m.r[2]=3
        m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
        m.record_call=lambda t:m.calls.append((t,tuple(m.arguments(2))))
        m.hook=lambda t:self.assertEqual(t,0x15141E38)
        with self.assertRaises(WindowBoundary):m.run()
        self.assertEqual(m.calls,[(0x15141E38,(ACTOR,3))])
        self.receipt('callers',dict(cases_per_body=counts,window_words=[5,8],callback_index=3,retail_count=85,
            first_window_direct_dispatch_boundary_only=True,retail_first_stage_uses_record_registration=True,full_parent_not_claimed=True))
    def test_06_fired_fault_prefixes_and_disabled_inputs(self):
        count=0
        for c in(Case(active=0),Case(answer=0),Case(),Case(value=0x7FC12345,phase=8),Case(mutation=7),Case(value=0x4F000000,second=0x3F800000)):
            initial=fixture(c);done=Oracle(self.retail,initial,c).run()
            for cut in range(done.all_accesses):
                models=[]
                for w in(self.retail,self.words):
                    m=Oracle(w,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(state(models[0]),state(models[1]));count+=1
        c=Case(active=0);initial=fixture(c)
        for a in syms().values():
            for i in range(4):initial.pop(a+i,None)
        for i in range(4):initial.pop(ACTOR+0x40+i)
        self.compare(c,initial);self.receipt('fault-prefixes',dict(fired_prefixes=count,disabled_path_needs_no_tag_or_constants=True))
    def test_07_independent_rebase_links(self):
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context=type('PointEffectOriginal',(),dict(root=ROOT,out=self.out))
        original=ViewListSetupTests.original.__func__(context,'original-point-effect',(ROOT/match.ASM).read_text(),match.FUNCTION)
        links=count=0
        for index,(entry,a,b,point,effect)in enumerate(((match.ENTRY,0x800A5728,0x800A572C,POINT,EFFECT),
                (0x18017FFC,0x800B7FFC,0x800B8000,0x18028000,0x18038000),(0x1A028000,0x800C8000,0x800C7FFC,0x1A037FFC,0x1A048000))):
            s=syms(a,b,point,effect);images=[]
            for ordinal,obj in enumerate((original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(index,ordinal));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>73I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[2]);wanted=list(images[0]);wanted[0x34//4]=0xAFA70020;wanted[0xF8//4]=0x8FAB0020;self.assertEqual(images[1],wanted)
            for active,answer,mutation,mode in itertools.product((0,0x50000),(0,1),(0,7),(1,2)):
                self.compare(Case(active=active,answer=answer,mutation=mutation,mode=mode),images=(images[0],images[2]),s=s,entry=entry);count+=1
        self.receipt('rebases',dict(GNU_links=links,cases_per_body=count,both_HI_LO_carry_edges=True,all_targets_relocated=True))
    def test_08_native32_unsigned_byte_conversion_and_typed_calls(self):
        cases=[]
        for active,mode,amount,value,mutation,answer in itertools.product((0,0x50000),(1,2,0xABCD00FF),
                (0,85,0x80000000,0x7FFFFFFF),(bits(.75),bits(255.75),bits(256.75),0x4F000000,0x4F7FFFFF),(0,1),(0,1)):
            c=Case(active=active,mode=mode,amount=amount,value=value,mutation=mutation,answer=answer)
            # All controls remain within the unsigned-word conversion domain.
            cases.append(c)
        rows=[('positive-'+opt[1:],candidate.SELECTED,opt,0)for opt in('-O0','-O2','-O3')]
        rows.extend((name,body,'-O2',1)for name,body in controls().items())
        for label,body,opt,expected in rows:
            p=self.out/('native-'+label+'.c');p.write_text(native_source(body,cases));exe=p.with_suffix('.elf')
            built=subprocess.run([*native_command(opt),'-fsanitize=float-cast-overflow','-mstackrealign',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            result=subprocess.run([str(exe)],capture_output=True,timeout=60);self.assertEqual(result.returncode,expected,(label,result.stderr))
        self.receipt('native-contract',dict(profiles=['O0','O2','O3'],direct_cases_per_profile=len(cases),typed_cases_per_profile=len(cases),
            controls=len(controls()),UBSan=True,float_cast_overflow_traps=True,finite_unsigned32_tag_domain=True,
            tag_wrap_across_256_and_unsigned_high_half=True,actual_height_result_layout=True))
    def test_09_actual_IDO_controls_and_named_metadata_corruptions(self):
        found={}
        for label in('wrong_gate','wrong_point_mode','inverted_result','wrong_slot','wrong_scale','wrong_tag_constant','wrong_mode','cached_tag'):
            obj,_=candidate.compile_owner(ROOT,self.out,candidate.source_with(controls()[label]),'negative-'+label)
            text,fs=candidate.link_owner(ROOT,self.out,obj,candidate.OWNER);f=fs[match.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(f['size']//4),text,f['value']));witness=False
            for c in(Case(value=bits(256.75),mutation=1),Case(active=0),Case(answer=0),Case(mode=2,amount=32767)):
                initial=fixture(c);m=Oracle(words,initial,c).run();expected,calls,observations=reference(initial,c,m.before[31])
                if public(m.memory)!=public(expected)or m.calls!=calls or m.observations!=observations:witness=True;break
            self.assertTrue(witness,label);found[label]=True
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=match.original_bytes(ROOT)
        for offset in(0x2C34CC,0x2C34DC,0x303567,0x303572):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        self.receipt('compiled-controls',dict(controls=found,named_metadata_corruptions=4))

def native_source(body,cases):
    rows=[]
    for c in cases:
        initial=fixture(c);_,calls,observations=reference(initial,c,0xDEAD0000)
        scale,tag=(calls[-1][1][2:4]if len(calls)==2 else(0,0))
        rows.append('{%s}'%','.join('0x%Xu'%u32(v)for v in(c.active,c.mode,c.amount,c.value,c.first,c.second,c.answer,c.mutation,scale,tag,len(calls))))
    return '#include <ultra64.h>\n'+candidate.RESULT_TYPE+'\n'+candidate.DECLARATIONS+r'''
typedef struct {u32 active,mode,amount,value,first,second,answer,mutation,scale,tag,calls;} Fixture;
typedef void (*Handler)(u8*,s32,s32);
static const Fixture cases[]={'''+','.join(rows)+r'''};
static const Fixture *current;
static u8 *actor;
static s32 error,calls;
static f32 *position;
static HeightResult71820 *interval;
f32 D_800A5728,D_800A572C;
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
s32 func_15146890(f32*p,u8*a,HeightResult71820*r,u8 mode){
 u32 i;if(a!=actor||mode!=(u8)current->mode||calls++)error=1;position=p;interval=r;
 p[0]=1.25f;p[1]=-2.5f;p[2]=3.75f;for(i=0;i<sizeof(*r);i++)((u8*)r)[i]=(u8)(i*29+0x31);
 if(current->mutation&1){*(f32*)(actor+0x40)=27.5f;D_800A5728=.5f;D_800A572C=2.f;}
 if(current->mutation&8)*(s32*)(actor+0x1D4)=0;
 return (s32)current->answer;
}
void func_15141F78(u8 slot,u8*source,f32 scale,u8 tag,f32*p,u8 mode){
 u32 i;if(calls++!=1||slot!=10||source!=(u8*)interval||word(scale)!=current->scale||tag!=current->tag||p!=position||mode!=(u8)current->mode)error=1;
 if(word(p[0])!=0x3FA00000u||word(p[1])!=0xC0200000u||word(p[2])!=0x40700000u)error=1;
 for(i=0;i<sizeof(*interval);i++)if(source[i]!=(u8)(i*29+0x31))error=1;
}
'''+body+r'''
__attribute__((noinline))static void invoke(Handler fn,u8*a,s32 b,s32 c){fn(a,b,c);}
static s32 run(void){
 u32 args[6]={0,4096,3,0x22,0xFFFFFFFFu,0},address,i,j;
 if(sizeof(void*)!=4||sizeof(HeightResult71820)!=36||__builtin_offsetof(HeightResult71820,metadata)!=24||__builtin_offsetof(HeightResult71820,value)!=32)return 9;
 __asm__ volatile("int $0x80":"=a"(address):"a"(90),"b"(args):"memory");if(address>=0xFFFFF000u)return 10;actor=(u8*)address;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++)for(j=0;j<2;j++){
  current=cases+i;calls=error=0;*(s32*)(actor+0x1D4)=(s32)current->active;*(f32*)(actor+0x40)=real(current->value);
  D_800A5728=real(current->first);D_800A572C=real(current->second);
  if(j)invoke(func_15146D60,actor,(s32)current->mode,(s32)current->amount);else func_15146D60(actor,(s32)current->mode,(s32)current->amount);
  if(error||(u32)calls!=current->calls)return 1;
 }
 return 0;
}
void _start(void){s32 result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''

if __name__=='__main__':unittest.main()
