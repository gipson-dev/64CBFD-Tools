"""Direct dual-point motion: rounded results, aliases, actual caller and image."""
from dataclasses import replace
import csv,itertools,json,math,struct,subprocess,unittest
from tools.experiments import game_dual_damped_motion_candidates as candidate
from tools.experiments import game_dual_damped_motion_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import game_dual_damped_motion_oracle as g
from tools.tests import game_dual_damped_motion_native as native
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_effect_owner_ray as ray
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=candidate.ROOT

def controls():
    b=candidate.SELECTED
    rows=dict(wrong_return=('return 1;','return 0;'),
        missing_x_damping=('    motion->velocity[0] *= damping;\n',''),
        shared_end_damping=('motion->endVelocity[0] *= endDamping','motion->endVelocity[0] *= damping'),
        missing_end_z_damping=('    motion->endVelocity[2] *= endDamping;\n',''),
        inverted_acceleration=('motion->velocity[1] += acceleration','motion->velocity[1] -= acceleration'),
        unscaled_second_acceleration=('motion->endVelocity[1] += acceleration * D_800BE9A4','motion->endVelocity[1] += acceleration'),
        wrong_position_axis=('motion->position[1] += motion->velocity[1]','motion->position[1] += motion->velocity[0]'),
        shared_endpoint_velocity=('motion->endPoint[0] += motion->endVelocity[0]','motion->endPoint[0] += motion->velocity[0]'))
    result={n:b.replace(a,z,1)for n,(a,z)in rows.items()}
    result['cached_timestep']=b.replace('    f32 damping =','    f32 step = D_800BE9A4;\n    f32 damping =',1).replace(' * D_800BE9A4',' * step')
    a='    motion->position[0] += motion->velocity[0] * D_800BE9A4;\n';z='    motion->position[1] += motion->velocity[1] * D_800BE9A4;\n'
    result['reversed_position_order']=b.replace(a+z,z+a)
    if any(v==b for v in result.values()):raise AssertionError('Ineffective motion control')
    return result

class DualDampedMotionMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>66I',cls.rom,match.ROM));linked,fs=candidate.link_owner(ROOT,cls.out,cls.prepared['qualified_compact'],candidate.OWNER)
        cls.words=list(struct.unpack_from('>66I',linked,fs[match.FUNCTION]['value']))
    def receipt(self,name,row):(self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    def compare(self,c,phase=0,entry=match.ENTRY,step=g.STEP,images=None,initial=None):
        initial=g.fixture(c,step)if initial is None else initial;expected=g.reference(initial,c,step);models=[]
        for body in images or(self.retail,self.words):
            m=g.Oracle(body,initial,c,phase,entry,step).run();actual=dict(m.memory);wanted=dict(expected)
            for at in g.WRITTEN:
                p=g.owner(c,step)+at
                if math.isnan(g.floating(g.read(actual,p)))and math.isnan(g.floating(g.read(wanted,p))):g.put(actual,p,0x7FC00000);g.put(wanted,p,0x7FC00000)
            self.assertEqual(actual,wanted,c);self.assertEqual(m.r[2],1);self.assertFalse(m.calls);models.append(m)
        self.assertEqual(complete(models[0]),complete(models[1]));return models
    def test_01_direct_words_bindings_owner_and_literal_corruptions(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['relocations'],q['neighbors'],q['raw_neighbors']),(66,0,0,2,68,68));self.assertEqual(self.words,self.retail)
        raw,bindings=match.function_blob(self.prepared['qualified_compact']);truth=match.original_bytes(ROOT)
        for i in range(264):
            bad=bytearray(raw);bad[i]^=1
            with self.assertRaises(ValueError):match.checked_payload(bytes(bad),bindings,truth)
        for bad in({},{0:bindings[0]},{**bindings,4:[('R_MIPS_LO16','D_800BE9A8')]}):
            with self.assertRaises(ValueError):match.checked_payload(raw,bad,truth)
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();self.assertEqual(match.strict_image(before,after,truth),227)
        for i in(0,0x80,match.elf_slot_offset(before,match.ENTRY,264)+264,len(after)-1):
            bad=bytearray(after);bad[i]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        with(ROOT/match.GUARDS).open()as s:self.assertFalse([r for r in csv.DictReader(s)if r['function']==match.FUNCTION])
    def test_02_rounded_motion_signed_zero_subnormals_and_nonfinite(self):
        visits=set();count=0
        for c in g.corpus():
            for m in self.compare(c):visits.update(m.visits)
            count+=1
        for at,value in itertools.product(g.INPUTS,(0x7FC12345,0x7F800000,0xFF800000,0x7F7FFFFF)):
            c=g.Case();initial=g.fixture(c);g.put(initial,g.ACTOR+at,value);self.compare(c,initial=initial);count+=1
        for value in(0x7FC12345,0x7F800000,0xFF800000,0x7F7FFFFF):self.compare(g.Case(step=value));count+=1
        self.assertEqual(visits,set(range(match.ENTRY,match.ENTRY+264,4)))
        self.receipt('guest-contract',dict(cases_per_body=count,covered_words=66,independent_operation_rounding=True,nonfinite_reference='NaN classification; all other bytes exact',FCSR_hardware_not_claimed=True))
    def test_03_every_aligned_timestep_overlap_and_private_state(self):
        count=0
        for layout,pattern,points,phase in itertools.product(range(0,0x164,4),(0,1,2,3),(0,1),(0,8)):
            self.compare(g.Case(layout=layout,pattern=pattern,points=points),phase);count+=1
        for offset,phase in itertools.product((0,0x34,0x140,0x160),(0,8)):
            self.compare(g.Case(layout=g.STEP-(g.STACK+phase-offset)),phase);count+=1
        self.receipt('aliases',dict(cases_per_body=count,aligned_record_layouts=89,private_stack_cases=8,disjoint_also_qualified=True))
    def test_04_original_return_sensitive_registered_caller(self):
        original=list(struct.unpack_from('>16I',self.rom,ray.WINDOW_ROM));count=0;visits=set()
        for slot,expired,phase,zero_return,pattern in itertools.product((0,10),(0,1,128,255),(0,8),(False,True),(0,1,3)):
            c=g.Case(pattern=pattern);initial=g.fixture(c);initial[g.ACTOR+0x70]=slot;initial[g.ACTOR+0x71]=10
            for i in range(42):g.put(initial,g.TABLE+4*i,match.ENTRY if i==10 else 0xABCD0000+4*i)
            expected=dict(initial);sp=g.STACK+phase-32
            if slot:g.put(expected,sp+32,g.ACTOR);g.put(expected,sp+27,expired,1);expected=g.reference(expected,c)
            models=[]
            for body in(self.retail,self.words):
                callback=list(body)
                if zero_return:callback[callback.index(0x24020001)]=0x24020000
                connected=dict(zip(range(match.ENTRY,match.ENTRY+264,4),callback));m=g.Oracle(original,initial,c,phase,entry=ray.WINDOW,connected=connected)
                m.r[29]=sp;m.r[7]=expired;m.code=ray.WindowCode(m.code,m)
                with self.assertRaises(ray.WindowBoundary):m.run()
                self.assertEqual(m.memory,expected);self.assertEqual(m.r[29],sp)
                wanted=(1 if zero_return else((expired^128)-128))if slot else expired
                self.assertEqual(m.r[7],wanted&0xFFFFFFFF);self.assertEqual(m.calls,[(match.ENTRY,(g.ACTOR,))]if slot else[]);visits.update(m.visits);models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(ray.WINDOW,ray.WINDOW_END,4))<=visits)
        self.receipt('caller',dict(cases_per_body=count,words=16,slot=10,entries=42,effective_zero_return_control=True,full_parent_not_claimed=True))
    def test_05_fired_literal_access_prefixes(self):
        count=0
        for layout in(-1,0x34,0x40,0x140,0x144,0x14C):
            c=g.Case(layout=layout);initial=g.fixture(c);done=g.Oracle(self.retail,initial,c).run()
            for cut in range(done.root_accesses):
                models=[]
                for body in(self.retail,self.words):
                    m=g.Oracle(body,initial,c);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].events,models[1].events);count+=1
        self.receipt('fault-prefixes',dict(fired_prefixes=count,complete_private_state_and_events_equal=True))
    def test_06_independent_GNU_links_and_timestep_carries(self):
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        ctx=type('MotionOriginal',(),dict(root=ROOT,out=self.out));original=ViewListSetupTests.original.__func__(ctx,'original-dual-damped',(ROOT/match.ASM).read_text(),match.FUNCTION);links=count=0
        for j,(entry,step)in enumerate(((match.ENTRY,g.STEP),(0x18017FFC,0x800A7FFC),(0x1A028000,0x800A8000))):
            images=[]
            for k,obj in enumerate((original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[match.FUNCTION],rs,match.FUNCTION,{'D_800BE9A4':step});self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(j,k));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,'--defsym=D_800BE9A4=0x%X'%step,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
                images.append(list(struct.unpack_from('>66I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for layout,damping,phase in itertools.product((-1,0x34,0x140,0x144,0x14C,0x150,0x160),map(g.bits,(.5,-.75)),(0,8)):
                self.compare(g.Case(layout=layout,damping=damping),phase,entry,step,images[:2]);count+=1
        self.receipt('rebases',dict(GNU_links=links,cases_per_body=count,both_HI_LO_carry_edges=True))
    def test_07_native32_typed_storage_aliases_and_controls(self):
        p=self.out/'native32.c';p.write_text(native.source(controls()))
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('native32'+opt);built=subprocess.run([*native_command(opt),'-mstackrealign',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            (self.out/('native32'+opt+'-diagnostics.txt')).write_text(built.stdout+built.stderr);self.assertEqual(built.returncode,0,(built.stdout+built.stderr)[:4000])
            self.assertEqual(subprocess.run([str(exe)],timeout=60).returncode,0,opt)
        self.receipt('native-contract',dict(positive_executions=12288,profiles=['O0','O2','O3'],direct_and_typed=True,field_timestep_aliases=15,controls=len(controls()),UBSan=True))
    def test_08_actual_IDO_controls_with_alias_witnesses(self):
        witnesses=[g.Case(layout=at)for at in(-1,0x34,0x38,0x140,0x144,0x14C,0x150)];found={}
        for label,body in controls().items():
            obj,_=candidate.compile_owner(ROOT,self.out,candidate.source_with(body),'negative-'+label);linked,fs=candidate.link_owner(ROOT,self.out,obj,candidate.OWNER);f=fs[match.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(f['size']//4),linked,f['value']));witness=False
            for c in witnesses:
                initial=g.fixture(c);m=g.Oracle(words,initial,c).run()
                if m.memory!=g.reference(initial,c)or m.r[2]!=1:witness=True;break
            self.assertTrue(witness,label);found[label]=True
        self.receipt('compiled-controls',dict(effective_IDO_controls=found))
if __name__=='__main__':unittest.main()
