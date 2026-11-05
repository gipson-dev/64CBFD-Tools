"""Fractional emitter: live packets, repeat thresholds, RNG, caller and full image."""
from dataclasses import replace
import csv,itertools,json,struct,subprocess,unittest
from tools.experiments import game_fractional_burst_emitter_candidates as candidate
from tools.experiments import game_fractional_burst_emitter_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import game_fractional_burst_emitter_oracle as g
from tools.tests import game_fractional_burst_emitter_native as native
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=candidate.ROOT
class WindowBoundary(Exception):pass
class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==getattr(self.owner,'stop_pc',None):raise WindowBoundary
        if pc==getattr(self.owner,'poison_pc',None):self.owner.r[2]=self.owner.poison_value
        return super().__getitem__(pc)
def controls():
    b=candidate.SELECTED
    rows=dict(gate_tie=('if (record->payload.phase > 1.0f)','if (record->payload.phase >= 1.0f)'),
        loop_tie=('while (payload->phase > 1.0f)','while (payload->phase >= 1.0f)'),
        inverted_increment=('phase += D_800A8D10','phase -= D_800A8D10'),
        wrong_decrement=('payload->phase -= 1.0f','payload->phase -= 2.0f'),
        wrong_scale=('* 25.0f','* 24.0f'),wrong_base=('+ 15.0f','+ 14.0f'),
        signed_tag=('4, payload->tag','4, (s8)payload->tag'),
        wrong_context=('NULL, record->context','NULL, payload->tag'),
        wrong_axis=('payload->x, payload->y, payload->z','payload->x, payload->y, payload->y'),
        wrong_count=('0, 255, 5, 4','0, 255, 6, 4'))
    result={n:b.replace(a,z,1)for n,(a,z)in rows.items()}
    result['cached_x']=b.replace('        do {','        do {\n            f32 x = payload->x;',1).replace('func_1514C678(payload->x,','func_1514C678(x,',1)
    result['cached_random']=b.replace('        do {','        f32 random = func_150ADA68();\n        do {',1).replace('func_150ADA68() * 25.0f','random * 25.0f')
    if any(v==b for v in result.values()):raise AssertionError('Ineffective emitter control')
    return result
class FractionalBurstEmitterMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>69I',cls.rom,match.ROM));linked,fs=candidate.link_owner(ROOT,cls.out,cls.prepared['qualified_compact'],candidate.OWNER)
        cls.words=list(struct.unpack_from('>69I',linked,fs[match.FUNCTION]['value']))
    def receipt(self,name,row):(self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    def compare(self,c,s=None,entry=match.ENTRY,images=None,connected=None,initial=None,private=False):
        s=s or g.syms();initial=g.fixture(c,s)if initial is None else initial;models=[]
        for body in images or(self.retail,self.words):
            m=g.Oracle(body,initial,c,s,entry,connected);boundary=None
            try:m.run()
            except AssertionError as error:
                if not private:raise
                h=g.STACK+c.phase;at=g.actor(c,s)+0xC
                if at in(h-12,h-8):self.assertEqual(error.args,(('saved register',16 if at==h-12 else 17),))
                elif at==h-4:self.assertEqual(error.args,(('unowned jump',g.read(m.memory,h-4)),))
                else:raise
                boundary=error.args
            broken=private and bool(c.mode&9)and g.actor(c,s)+0xC in(g.STACK+c.phase-12,g.STACK+c.phase-8,g.STACK+c.phase-4)
            self.assertEqual(bool(boundary),broken)
            expected,calls=g.reference(initial,c,s,bool(connected),saved=(m.before[16],m.before[17],m.before[31]))
            self.assertEqual((g.public(m.memory),m.calls),(g.public(expected),calls),c)
            a=g.actor(c,s)
            for at,n in((0xC,1),(0x28,4),(0x2C,4),(0x30,4),(0x34,1),(0x38,4)):
                if all(a+at+i in expected for i in range(n)):self.assertEqual(g.read(m.memory,a+at,n),g.read(expected,a+at,n),c)
            models.append(m)
        self.assertEqual(complete(models[0]),complete(models[1]));return models
    def test_01_direct_words_complete_owner_bindings_and_literal_corruptions(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['relocations'],q['neighbors'],q['raw_neighbors']),(69,96,0,6,38,38));self.assertEqual(self.words,self.retail)
        raw,rs=match.function_blob(self.prepared['qualified_compact']);truth=match.original_bytes(ROOT)
        for i in range(276):
            bad=bytearray(raw);bad[i]^=1
            with self.assertRaises(ValueError):match.checked_payload(bytes(bad),rs,truth)
        for at in rs:
            with self.assertRaises(ValueError):match.checked_payload(raw,{**rs,at:[('R_MIPS_26','wrong')]},truth)
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();self.assertEqual(match.strict_image(before,after,truth),213)
        for at in(0,0x80,match.elf_slot_offset(before,match.ENTRY,276)+276,len(after)-1):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        with(ROOT/match.GUARDS).open()as f:self.assertFalse([r for r in csv.DictReader(f)if r['function']==match.FUNCTION])
    def test_02_fractional_boundaries_all_tag_context_bytes_and_live_mutations(self):
        count=0;visits=set();phases=(0xFF800000,0x7FC12345,g.bits(-1.),0x80000000,0,0x3F7FFFFF,0x3F800000,0x3F800001,g.bits(2.),g.bits(3.25),g.bits(8.5))
        for phase,step,rnd,sp in itertools.product(phases,map(g.bits,(0,.5,1,-1)),range(7),(0,8)):
            c=g.Case(phase_value=phase,step=step,random=rnd,phase=sp)
            for m in self.compare(c):visits.update(m.visits)
            count+=1
        for field,byte,mode in itertools.product(('tag','context'),range(256),(0,1,8)):
            self.compare(replace(g.Case(mode=mode,phase=(byte&1)*8),**{field:byte}));count+=1
        for mode,phase,step,sp in itertools.product(range(32),map(g.bits,(0,1,3.25,8.5)),map(g.bits,(0,.5)),(0,8)):
            self.compare(g.Case(mode=mode,phase_value=phase,step=step,phase=sp));count+=1
        self.assertEqual(visits,set(range(match.ENTRY,match.ENTRY+276,4)))
        self.receipt('guest-contract',dict(cases_per_body=count,covered_words=69,all_tag_context_bytes=True,provider_mutations=32,independent_f32_rounding=True))
    def test_03_global_record_private_aliases_and_stalled_phase_prefixes(self):
        count=0
        for symbol,offset,mode,sp in itertools.product((1,2),range(0,0x3C,4),(0,1,2,4,8,16,31),(0,8)):
            self.compare(g.Case(alias=symbol,offset=offset,mode=mode,phase=sp));count+=1
        for offset,mode,sp in itertools.product((-24,-20,-16,-12,-8,0,16),(0,1,8,16,31),(0,8)):
            self.compare(g.Case(actor=g.STACK+sp+offset,mode=mode,phase=sp),private=True);count+=1
        for value in(0x7F800000,g.bits(33554432.)):
            c=g.Case(phase_value=value,step=0);models=[]
            for body in(self.retail,self.words):
                m=g.Oracle(body,g.fixture(c),c,limit=8)
                with self.assertRaises(g.CallLimit):m.run()
                self.assertEqual((m.n,len(m.packets),g.read(m.memory,g.ACTOR+0x38)),(8,8,value));models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]))
        self.receipt('aliases',dict(cases_per_body=count,aligned_layouts_per_global=15,private_cases=70,expected_private_ABI_corruption_boundaries=18,stalled_phase_prefixes=2,eight_emissions_each_prefix=True,no_termination_claim_for_prefixes=True))
    def test_04_connected_original_64bit_float_rng(self):
        self.assertEqual(struct.unpack_from('>I',self.rom,0x2275E0+g.SCALE-0x80082B20)[0],0x37800080)
        code=g.rng_code(self.rom);count=0
        for seed,phase,mode,sp in itertools.product(g.SEEDS,map(g.bits,(0,1,1.25,3.25,8.5)),(0,4,8,12),(0,8)):
            c=g.Case(phase_value=phase,mode=mode,phase=sp);initial=g.fixture(c);g.put(initial,g.SEED,seed,8);self.compare(c,connected=code,initial=initial);count+=1
        self.receipt('connected-rng',dict(cases_per_body=count,original_words=25,seed_width=64,scale_word='0x37800080'))
    def test_05_original_45word_void_caller_lifetime_and_cleanup(self):
        original=list(struct.unpack_from('>45I',self.rom,0x176714));count=0;visits=set()
        for enabled,flags,life,dtor,mode,sp,poison in itertools.product((False,True),(0,1),(-1,3),(False,True),(0,4,8),(0,8),(0,0xFFFFFFFF)):
            c=g.Case(mode=mode,phase=sp);initial=g.fixture(c);a=g.ACTOR;initial[a+13]=flags;initial[a+16]=0 if dtor else 255;initial[a+17]=1 if enabled else 255
            g.put(initial,a+14,life&65535,2);g.put(initial,g.TICKS,5);g.put(initial,g.TABLE+4,match.ENTRY);g.put(initial,0x8008A4C0,g.DESTRUCTOR)
            expected=dict(initial);remaining=(life-5 if flags else life)&65535;g.put(expected,a+14,remaining,2);calls=[]
            if enabled:expected,calls=g.reference(expected,c,home=g.STACK+sp-32);calls=[(match.ENTRY,(a,)),*calls]
            if remaining&0x8000:
                if dtor:calls.append((g.DESTRUCTOR,(a,)))
                calls.append((g.RELEASE,(a,)));expected[a+0x3F]=0xEE
            models=[]
            for body in(self.retail,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+276,4),body));m=g.Oracle(original,initial,c,entry=g.PARENT,connected=code);m.poison_pc=0x151492B8;m.poison_value=poison;m.code=WindowCode(m.code,m);m.run()
                self.assertEqual((g.public(m.memory),m.calls),(g.public(expected),calls));models.append(m);visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(g.PARENT,g.PARENT+180,4))<=visits)
        self.receipt('caller',dict(cases_per_body=count,original_words=45,callback_slot=1,void_return_poison_values=2,destructor_release_bounded=True))
    def test_06_original_factory_prefix_receives_float_and_narrow_parameters(self):
        code=dict(zip(range(g.EMIT,g.EMIT+0x88,4),struct.unpack_from('>34I',self.rom,0x179B28)));code[g.EMIT+0x88]=0;count=0
        for tag,context,mode,rnd,sp in itertools.product((0,128,255),(0,128,255),(0,1,8),range(7),(0,8)):
            c=g.Case(tag=tag,context=context,mode=mode,random=rnd,phase=sp);models=[]
            for body in(self.retail,self.words):
                m=g.Oracle(body,g.fixture(c),c,connected=code);m.stop_pc=g.EMIT+0x88;m.code=WindowCode(m.code,m)
                with self.assertRaises(WindowBoundary):m.run()
                packet=m.packets[0];self.assertEqual((m.f[26],m.f[24],m.f[28],m.f[22]),packet[:4]);self.assertEqual((m.r[4],m.r[5],m.r[21]),(255,0,5));models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt('factory-prefix',dict(cases_per_body=count,original_words=34,callee_frame=160,four_float_and_three_narrow_inputs=True,full_factory_not_claimed=True))
    def test_07_fired_access_prefixes_and_sparse_inactive_record(self):
        count=0
        for c in(g.Case(phase_value=0,step=0),g.Case(),g.Case(mode=31,phase=8),g.Case(alias=2,offset=0x38)):
            initial=g.fixture(c);done=g.Oracle(self.retail,initial,c).run()
            for cut in range(done.all_accesses):
                models=[]
                for body in(self.retail,self.words):
                    m=g.Oracle(body,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace);count+=1
        c=g.Case(phase_value=0,step=0);initial=g.fixture(c)
        for at,n in((0xC,1),(0x28,12),(0x34,1)):
            for i in range(n):initial.pop(g.ACTOR+at+i)
        self.compare(c,initial=initial);self.receipt('fault-prefixes',dict(fired_prefixes=count,sparse_inactive_payload_unread=True))
    def test_08_independent_GNU_links_all_six_bindings_and_carries(self):
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        ctx=type('EmitterOriginal',(),dict(root=ROOT,out=self.out));original=ViewListSetupTests.original.__func__(ctx,'original-emitter',(ROOT/match.ASM).read_text(),match.FUNCTION);links=count=0
        for j,(entry,s)in enumerate(((match.ENTRY,g.syms()),(0x18017FFC,dict(D_800A8D10=0x800A7FFC,D_800BE9A4=0x800B8000,func_150ADA68=0x18038000,func_1514C678=0x18048000)),(0x1A028000,dict(D_800A8D10=0x800C8000,D_800BE9A4=0x800D7FFC,func_150ADA68=0x1A048000,func_1514C678=0x1A058000)))):
            images=[]
            for k,obj in enumerate((original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(j,k));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
                images.append(list(struct.unpack_from('>69I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for alias,mode,sp in itertools.product((0,1,2),(0,3,12,31),(0,8)):
                self.compare(g.Case(alias=alias,offset=0x38,mode=mode,phase=sp),s,entry,images[:2]);count+=1
        self.receipt('rebases',dict(GNU_links=links,cases_per_body=count,all_six_bindings=True,both_global_carry_edges=True))
    def test_09_native32_typed_calls_live_mutation_and_controls(self):
        p=self.out/'native32.c';p.write_text(native.source(controls()))
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('native32'+opt);built=subprocess.run([*native_command(opt),'-mstackrealign',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            (self.out/('native32'+opt+'-diagnostics.txt')).write_text(built.stdout+built.stderr);self.assertEqual(built.returncode,0,(built.stdout+built.stderr)[:4000]);self.assertEqual(subprocess.run([str(exe)],timeout=60).returncode,0,opt)
        self.receipt('native-contract',dict(positive_executions=12288,profiles=['O0','O2','O3'],direct_and_typed=True,typed_float_aliases_per_global=4,controls=len(controls()),UBSan=True))
    def test_10_actual_IDO_controls_with_discriminating_boundaries(self):
        witnesses=[g.Case(phase_value=g.bits(v),step=0,mode=mode)for v,mode in itertools.product((.5,1.,2.,3.25),(0,1,4,8))]+[g.Case(phase_value=g.bits(.9),step=g.bits(1.))];found={}
        for label,body in controls().items():
            obj,_=candidate.compile_owner(ROOT,self.out,candidate.source_with(body),'negative-'+label);linked,fs=candidate.link_owner(ROOT,self.out,obj,candidate.OWNER);f=fs[match.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),linked,f['value']));witness=False
            for c in witnesses:
                initial=g.fixture(c);expected,calls=g.reference(initial,c);m=g.Oracle(words,initial,c)
                try:m.run()
                except g.CallLimit:witness=True;break
                if(g.public(m.memory),m.calls)!=(g.public(expected),calls):witness=True;break
            self.assertTrue(witness,label);found[label]=True
        self.receipt('compiled-controls',dict(effective_IDO_controls=found))
if __name__=='__main__':unittest.main()
