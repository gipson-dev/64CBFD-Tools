"""Direct extent C: ordered boundaries, independent axes, setter ABI and image."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_dual_extent_approach_candidates as candidate
from tools.experiments import game_dual_extent_approach_match as match
from tools.tests import game_dual_extent_approach_oracle as g
from tools.tests import game_dual_extent_approach_native as native
from tools.tests import test_game_view_list_setup as view_setup
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT

def state(m):return complete(m),m.current_pc,m.delay_of,m.root_accesses

class DualExtentApproachTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT)
        cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.truth=cls.rom[match.ROM:match.ROM+280]
        cls.retail=list(struct.unpack('>70I',cls.truth))
        ctx=type('OriginalExtent',(),dict(root=ROOT,out=cls.out))
        cls.original=view_setup.ViewListSetupTests.original.__func__(ctx,'extent-original',(ROOT/match.ASM).read_text(encoding='utf-8'),match.FUNCTION)
        cls.raw=match.bound_blob(*match.function_blob(cls.prepared['qualified_compact']),match.symbols())
        cls.words=match.bound_blob(*match.function_blob(cls.prepared['qualified_owner']),match.symbols())
        assert cls.retail==cls.raw==cls.words==match.bound_blob(*match.function_blob(cls.original),match.symbols())

    def receipt(self,n,**v):(self.out/('extent-'+n+'.json')).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')

    def compare(self,c=g.Case(),constants=g.CONSTANT,images=None,entry=match.ENTRY,setter=g.SETTER):
        initial=g.fixture(c,constants);expected,calls=g.reference(initial,c,constants);models=[]
        if setter!=g.SETTER:calls=[(setter,a) for t,a in calls]
        for w in ((self.retail,self.raw,self.words)if images is None else images):
            m=g.Oracle(w,initial,c,entry=entry,setter=setter).run()
            self.assertTrue(g.equivalent(m.memory,expected,c),(c,hex(constants)))
            self.assertEqual((m.calls,m.r[2]),(calls,1))
            self.assertEqual(m.f[20:],m.before_f[20:]);models.append(m)
        self.assertEqual(state(models[0]),state(models[-1]));return models

    def test_01_owner_and_fail_closed_literal_words(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings'],q['neighbors']),(70,32,0,9,35))
        raw,b=match.function_blob(self.prepared['qualified_compact'])
        for at in range(280):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),b,self.truth)
        for at in b:
            bad=dict(b);bad[at]=[('R_MIPS_LO16','foreign')]
            with self.assertRaises(ValueError):match.checked(raw,bad,self.truth)
        self.receipt('owner',raw_and_padded_neighbors=35,raw_corruptions=280,binding_corruptions=9,guards=0,complete_70_words=True)

    def test_02_independent_rounded_reference_and_flag_coverage(self):
        seen=set();count=0
        for c in g.cases():
            models=self.compare(c);seen.update(models[0].visits);count+=1
        unreachable={match.ENTRY+0x7C,match.ENTRY+0xE4}
        self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+280,4))-unreachable)
        self.receipt('guest',cases_per_body=count,bodies=3,all_256_flag_values=True,reachable_words=68,unreachable_duplicate_words=2,all_70_words_literal=True,ordered_NaN_and_equality_boundaries=True,return1_and_callee_saved_ABI=True)

    def test_03_live_constant_aliases_and_private_fault_prefixes(self):
        count=0
        for off,flags,x,y,phase in itertools.product(range(0,0x12C,4),(0,2,8,10),(0,1),(0,1),(0,8)):
            self.compare(g.Case(flags,x,y,phase,g.CONSTANT-off));count+=1
        cuts=0;private=0
        for c in (g.Case(),g.Case(flags=10),g.Case(at=g.CONSTANT-0x2C),
                  g.Case(flags=0,x=0,y=0,at=g.STACK-0x20-0x2C),
                  g.Case(flags=0,x=0,y=0,phase=8,at=g.STACK+8-4-0x128)):
            initial=g.fixture(c);models=[]
            for w in(self.retail,self.words):
                m=g.Oracle(w,initial,c)
                try:m.run();outcome='returned'
                except AssertionError as e:outcome=str(e)
                models.append((m,outcome))
            self.assertEqual((state(models[0][0]),models[0][1]),(state(models[1][0]),models[1][1]));private+=1
            for cut in range(models[0][0].root_accesses):
                pair=[]
                for w in(self.retail,self.words):
                    m=g.Oracle(w,initial,c);m.root_fault=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(state(pair[0]),state(pair[1]));cuts+=1
        self.receipt('aliases',cases_per_body=count,constant_owner_offsets=75,private_terminal_cases=private,fault_prefixes=cuts,literal_fault_states_equal=True,portable_C_private_fault_claim=False)

    def test_04_actual_setter_and_complete_registered_parent(self):
        va=0x1513CFE4;body=list(struct.unpack_from('>195I',self.rom,0x16A494))
        helper=list(struct.unpack_from('>16I',self.rom,0x16CB30));seen=set();count=0
        for active,slot,flags,x,y,phase in itertools.product((0,1),(0,5),(0,10),(0,1),(0,1),(0,8)):
            c=g.Case(flags,x,y,phase,selectors=(0,0,255));initial=g.fixture(c);a=c.at
            for off,v in((0x10,active),(0x58,0),(0x24,0)):g.put(initial,a+off,v)
            initial[a+0x70]=initial[a+0x72]=0;initial[a+0x71]=slot;g.put(initial,g.TABLE+20,match.ENTRY)
            pair=[]
            expected,calls=g.reference(initial,c)
            for w in(self.retail,self.words):
                connected=dict(zip(range(match.ENTRY,match.ENTRY+280,4),w));connected.update(zip(range(g.SETTER,g.SETTER+64,4),helper))
                m=g.Oracle(body,initial,c,entry=va,connected=connected).run()
                if active and slot:
                    public=lambda mm:{k:v for k,v in mm.items()if not g.STACK-1024<=k<g.STACK+1024}
                    self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,[(match.ENTRY,(a,)),*calls])
                else:self.assertEqual(m.calls,[])
                pair.append(m);seen.update(m.visits)
            self.assertEqual(state(pair[0]),state(pair[1]));count+=1
        c=g.Case(flags=10,selectors=(0,0,255));initial=g.fixture(c)
        for off,v in((0x10,1),(0x58,0),(0x24,0)):g.put(initial,c.at+off,v)
        g.put(initial,g.TABLE+20,match.ENTRY);bad=list(self.words)
        for i,w in enumerate(bad):
            if w==0x24020001:bad[i]=0x24020000
        connected=dict(zip(range(match.ENTRY,match.ENTRY+280,4),bad));connected.update(zip(range(g.SETTER,g.SETTER+64,4),helper))
        m=g.Oracle(body,initial,c,entry=va,connected=connected).run()
        self.assertEqual([t for t,a in m.calls],[match.ENTRY,g.SETTER,0x1516972C])
        self.assertTrue(set(range(g.SETTER,g.SETTER+64,4))<=seen)
        self.receipt('caller',cases_per_body=count,whole_parent_words=195,parent_covered_words=len(seen&set(range(va,va+780,4))),original_setter_words=16,secondary_slot=5,next_secondary_slot=4,fifth_argument_255=True,false_return_cleanup_control=True,cleanup_opaque=True)

    def test_05_GNU_rebases_at_HI_LO_carries(self):
        links=0;count=0
        for k,(entry,constants,setter)in enumerate(((match.ENTRY,g.CONSTANT,g.SETTER),(0x18017FFC,0x89007FF8,0x18028000),(0x1A028000,0x89008000,0x1A038004))):
            syms={**{'D_%08X'%(g.CONSTANT+4*i):constants+4*i for i in range(4)},'func_1513F680':setter};images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                t,fs,rs=match.parse_object(obj);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,syms);self.assertFalse(unknown)
                p=self.out/('extent-rebase-%d-%d'%(k,j));p.with_suffix('.s').write_text(asm,encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,v)for n,v in syms.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
                images.append(list(struct.unpack_from('>70I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for c in list(g.cases())[::211]:self.compare(c,constants,images,entry,setter);count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,all_four_HI_LO_pairs_and_R26=True,carry_boundaries=True)

    def test_06_native_SDK_and_seven_effective_controls(self):
        p=self.out/'extent-native.c';p.write_text(native.program(),encoding='utf-8')
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('extent-native'+opt);r=subprocess.run([*native_command(opt),'-mstackrealign',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),opt);self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',positive_calls=12288,rows_per_profile=2048,profiles=['O0','O2','O3'],SDK_prefix_size=128,owner_size=300,byte_flags=True,real_float_alias_fields=4,independent_constant_alias_choices=4,direct_and_callback_ABI=True,UBSan=True,effective_controls=list(g.controls()),NaN_classes_only=True)

    def test_07_literal_image_controls_and_stub_rejection(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes()
        delta=match.strict_image(before,after,self.truth);at=match.elf_slot_offset(after,match.ENTRY,280)
        for off in(0,at,at+279,at+280,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.truth)
        stub=list(struct.unpack_from('>70I',before,at));m=g.Oracle(stub,g.fixture()).run();self.assertEqual(m.r[2],0)
        self.receipt('image',changed_bytes=delta,exclusions=0,corruptions=5,old_stub_rejected=True)

if __name__=='__main__':unittest.main()
