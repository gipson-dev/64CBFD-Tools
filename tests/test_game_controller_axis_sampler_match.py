"""Controller sampler qualification: independent C/guest semantics and literal image."""
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_controller_axis_sampler_candidates as candidate
from tools.experiments import game_controller_axis_sampler_match as match
from tools.tests import game_controller_axis_sampler_oracle as g
from tools.tests import game_controller_axis_sampler_native as native
from tools.tests import test_game_view_list_setup as view_setup
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary,TrackedCode
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
class WindowStop(Exception):pass
class WindowCode(TrackedCode):
    def __getitem__(self,pc):
        if pc==0x1503FCFC:raise WindowStop
        return super().__getitem__(pc)
class CallerOracle(g.AxisOracle):
    def record_call(self,t):
        if t!=match.ENTRY:raise AssertionError(('Unexpected caller helper',hex(t)))
        a=tuple(self.arguments(3));self.calls.append((t,a));self.events.append(('CALL',t,a))
def state(m):return complete(m),m.current_pc,m.delay_of,m.root_accesses
class ControllerAxisSamplerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.truth=cls.rom[match.ROM:match.ROM+280]
        cls.retail=list(struct.unpack('>70I',cls.truth));ctx=type('OriginalAxisSampler',(),dict(root=ROOT,out=cls.out))
        cls.original=view_setup.ViewListSetupTests.original.__func__(ctx,'axis-original',(ROOT/match.ASM).read_text(encoding='utf-8'),match.FUNCTION)
        cls.blobs=[match.function_blob(o)for o in(cls.original,cls.prepared['qualified_compact'],cls.prepared['qualified_owner'])]
        cls.images=[match.bound_blob(b,r,match.symbols())for b,r in cls.blobs];cls.receipts={}
        assert cls.images[0]==cls.retail==cls.images[2]
    @classmethod
    def tearDownClass(cls):(cls.out/'sampler-suite-receipt.json').write_text(json.dumps(cls.receipts,indent=2)+'\n',encoding='utf-8')
    def receipt(self,name,**v):self.receipts[name]=v
    def compare(self,initial,args,phase=0,images=None):
        want,trace=g.reference(initial,args,phase);models=[]
        for words in(images or self.images):
            m=g.AxisOracle(words,initial,args,phase);before=m.r[:];f=m.f[:];m.run()
            self.assertEqual(m.memory,want);self.assertEqual(m.trace,trace);self.assertFalse(m.calls)
            self.assertTrue(all(m.r[r]==before[r]for r in(*range(16,24),26,27,28,29,30,31)));self.assertEqual(m.f,f);models.append(m)
        self.assertEqual(state(models[0]),state(models[-1]));return models
    def test_01_owner_closed_recipe_and_corruption_rejection(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['guards'],q['raw_neighbors'],q['neighbors']),(70,9,2,2))
        raw,b=self.blobs[1];literal,r=match.recipe(raw,b);self.assertEqual((literal,r),self.blobs[2])
        for i in range(280):
            bad=bytearray(raw);bad[i]^=1
            with self.assertRaises(ValueError):match.recipe(bytes(bad),b)
        for at in b:
            bad=dict(b);bad[at]=[('R_MIPS_LO16','foreign')]
            with self.assertRaises(ValueError):match.recipe(raw,bad)
        old=(self.out/'match-frozen'/match.GUARDS).read_bytes();new=match.proposed_guards(old,raw,b)
        self.assertTrue(new.startswith(old));self.assertEqual(len(new.splitlines())-len(old.splitlines()),9)
        for at in(0,len(old)//2,len(old)-1):
            bad=bytearray(old);bad[at]^=1
            with self.assertRaises(ValueError):match.proposed_guards(bytes(bad),raw,b)
        # Each rewritten constant has one definition and one use, pinned by full body SHA.
        words=struct.unpack('>70I',raw)
        for reg,definition,use in((11,20,22),(12,25,49),(13,44,61)):
            self.assertEqual(words[definition]>>16&31,reg);self.assertEqual(words[use]>>16&31,reg)
            self.assertEqual(words[definition]>>26,9);self.assertEqual(words[use]>>26,41)
        self.receipt('owner',words=70,raw_differences=9,frame=0,guards=9,bindings=8,raw_padded_neighbors=2,raw_corruptions=280,binding_corruptions=8,guard_prefix_corruptions=3,independent_opening_rotation_and_three_closed_constant_lifetimes=True)
    def test_02_signed_widths_complete_memory_and_access_order(self):
        seen=[set(),set(),set()];count=0
        for initial,args,phase in g.cases():
            for i,m in enumerate(self.compare(initial,args,phase)):seen[i].update(m.visits)
            count+=1
        for words,visits in zip(self.images,seen):
            missing=[hex(pc-match.ENTRY)for pc in range(match.ENTRY,match.ENTRY+280,4)if pc not in visits]
            self.assertEqual(missing,['0x7c','0xa0','0xc8','0xf8']);self.assertEqual(missing,g.control_flow(words))
        self.receipt('guest',cases_per_body=count,bodies=3,all256_values_per_axis=True,signed16_countdown_wrap_and_raw_selector=True,complete_memory_and_access_trace=True,alias_cases=363,unreachable_words_proven=4,all66_reachable_words=True,saved_GPR_FPR_SP=True)
    def test_03_alias_fault_prefixes_and_literal_padded_states(self):
        count=0
        for initial,args,phase in(g.fixture(1),g.fixture(2),g.fixture(0x8000),g.fixture(1,ox=g.PAD+2,oy=g.PAD),g.fixture(1,ox=g.STACK,oy=g.STACK)):
            _,trace=g.reference(initial,args,phase)
            for cut in range(len(trace)):
                models=[]
                for words in self.images:
                    m=g.AxisOracle(words,initial,args,phase);m.root_fault=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    self.assertEqual(m.trace,trace[:cut]);models.append(m)
                self.assertEqual(models[0].memory,models[1].memory);self.assertEqual(state(models[0]),state(models[2]));count+=1
        self.receipt('faults',access_cuts=count,all_three_memory_and_trace_equal=True,retail_padded_full_states_equal=True,raw_private_GPR_PC_state_claim=False,output_input_global_home_aliases=True)
    def test_04_original_caller_window_ignores_incidental_result(self):
        count=0;window=list(struct.unpack_from('>6I',self.rom,0x6D194));seen=set()
        for countdown,x,y,phase,poison in itertools.product((0,1,2,0x8000),(-128,0,127),(-128,0,127),(0,8),(0,0xffffffff)):
            initial,args,phase=g.fixture(countdown,0,x,y,ox=g.STACK+phase+0xe2,oy=g.STACK+phase+0xe0,phase=phase)
            for i in range(128,256):initial[g.STACK+phase+i]=(i*17+0xa5)&255
            g.put(initial,0x80084488,0x12345678);want,trace=g.reference(initial,args,phase);models=[]
            for words in self.images:
                connected=dict(zip(range(match.ENTRY,match.ENTRY+280,4),words))
                m=CallerOracle(window,initial,(0,g.X,g.Y),phase,entry=0x1503FCE4,connected=connected);m.r[2]=poison;m.code=WindowCode(dict(m.code),m)
                with self.assertRaises(WindowStop):m.run()
                self.assertEqual(m.memory,want);self.assertEqual(m.trace,trace+[('R',0x80084488,4,0x12345678)])
                self.assertEqual(m.calls,[(match.ENTRY,args)]);self.assertEqual(m.r[2],0x12345678);seen.update(m.visits);models.append(m)
            self.assertEqual(state(models[0]),state(models[2]));count+=1
        self.assertTrue(set(range(0x1503FCE4,0x1503FCFC,4))<=seen)
        self.receipt('caller',cases_per_body=count,original_window_words=6,all_window_words=True,slot_zero_precondition_verified_in_parent=True,result_overwritten_by_following_global_load=True,complete_parent_claim=False)
    def test_05_independent_GNU_rebases_and_carry_boundaries(self):
        count=0;links=0
        for i,(counter,table)in enumerate(itertools.product((0x80087ffc,0x80088000,0x8008fffc),(0x800b7ffc,0x800b8000,0x800bfffc))):
            syms=dict(D_80084484=counter,D_800BE728=table);images=[]
            for j,(raw,bindings)in enumerate(self.blobs):
                label='sampler-rebase-%d-%d'%(i,j);s=self.out/(label+'.s');o=s.with_suffix('.o');elf=s.with_suffix('.elf');ld=s.with_suffix('.ld')
                assembly,missing=emit_function(raw,dict(value=0,size=280),bindings,match.FUNCTION,syms);self.assertFalse(missing)
                s.write_text(assembly,encoding='utf-8')
                subprocess.run(['mips-linux-gnu-as','-EB','-mabi=32','-march=vr4300','-o',str(o),str(s)],check=True,capture_output=True)
                ld.write_text('SECTIONS { .text 0x%X : { *(.text) } }\n'%match.ENTRY,encoding='utf-8')
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in syms.items()],'-o',str(elf),str(o)],check=True,capture_output=True)
                literal=sections(elf)['.text'][1][:280];words=list(struct.unpack('>70I',literal));self.assertEqual(words,match.bound_blob(raw,bindings,syms));images.append(words);links+=1
            self.assertEqual(images[0],images[2])
            for c in(0,1,2,0x8000):
                initial,args,phase=g.fixture(c,0xffff,127,-128)
                moved=dict(initial)
                for old,new in((g.COUNTDOWN,counter),(g.TABLEPTR,table)):
                    values={new+d:initial[old+d]for d in range(-8,16)}
                    for d in range(-8,16):moved.pop(old+d,None)
                    moved.update(values)
                # Run the independent reference at the equivalent original addresses,
                # then rename only the two disjoint global regions in its final state.
                want,trace=g.reference(initial,args,phase)
                def rename(p):
                    for old,new in((g.COUNTDOWN,counter),(g.TABLEPTR,table)):
                        if old-8<=p<old+16:return p-old+new
                    return p
                expected={rename(p):v for p,v in want.items()};trace=[(kind,rename(p),n,v)for kind,p,n,v in trace]
                models=[]
                for words in images:
                    m=g.AxisOracle(words,moved,args,phase);m.run();self.assertEqual(m.memory,expected);self.assertEqual(m.trace,trace);models.append(m)
                self.assertEqual(state(models[0]),state(models[2]));count+=1
        self.receipt('rebases',GNU_links=links,layouts=9,cases_per_body=count,independent_original_object=True,HI_LO_carry_edges=True,all8_bindings=True)
    def test_06_native32_SDK_UBSan_and_effective_controls(self):
        checks=[]
        for label,b,opt in[('selected',None,o)for o in('-O0','-O2','-O3')]+[(n,b,'-O2')for n,b in native.controls().items()]:
            p=self.out/('sampler-native-'+label+opt);src=p.with_suffix('.c');src.write_text(native.program(b),encoding='utf-8')
            cp=subprocess.run(native_command(opt)+['-o',str(p.relative_to(ROOT)),str(src.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((cp.returncode,cp.stdout,cp.stderr),(0,'',''),(label,opt))
            run=subprocess.run([str(p)],cwd=ROOT,capture_output=True,text=True);self.assertEqual((run.returncode,run.stdout,run.stderr),(0 if label=='selected'else 42,'',''),(label,opt));checks.append(dict(label=label,opt=opt,exit=run.returncode))
        self.receipt('native',positive_calls=786462,all65536_countdowns=True,all65536_axis_pairs=True,direct_and_compatible_callback=True,SDK32_UBSan=True,controls_rejected=10,checks=checks)
    def test_07_literal_whole_image_addresses_and_protected_data(self):
        q=self.prepared['report'];self.assertEqual((q['strict_exclusions'],q['strict_changed_bytes'],q['functions']),(0,206,6052));self.assertEqual(q['changed_bodies'],[match.FUNCTION])
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes()
        self.assertEqual(match.strict_image(before,after,self.truth),206)
        for at in(0,0x100,match.elf_slot_offset(after,match.ENTRY,280),len(after)//2,len(after)-1):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.truth)
        self.receipt('image',changed_bytes=206,exclusions=0,all6052_addresses_fixed=True,protected_bytes=189088,protected_owners=720,corruptions_rejected=5,conversion_rows_unchanged=True)
    def test_08_profile_and_former_stub_fail_closed(self):
        bs,ns,installed=candidate.source_states((ROOT/match.SOURCE).read_text(encoding='utf-8'));bm,nm,profile=candidate.make_states((ROOT/match.MAKE).read_text(encoding='utf-8'));self.assertEqual(installed,profile)
        self.assertIn('generated_6CEA0.c.o: CFLAGS += -Wo,-no_const_in_reg',nm)
        old,_=candidate.compile_owner(ROOT,self.out,bs,'sampler-former-stub')
        with self.assertRaises(ValueError):match.recipe(*match.function_blob(old))
        wrong,diag=candidate.compile_owner(ROOT,self.out,ns,'sampler-default-profile',flags=('-O2','-g3'));self.assertFalse(diag)
        with self.assertRaises(ValueError):match.recipe(*match.function_blob(wrong))
        self.receipt('profile',scoped_CFLAGS_only=True,default_profile_rejected=True,former_stub_rejected=True,caller_census=match.census(ROOT))
if __name__=='__main__':unittest.main()
