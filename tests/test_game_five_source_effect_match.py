"""Direct effect constructor, partial descriptors, live homes and original factory."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_five_source_effect_candidates as candidate
from tools.experiments import game_five_source_effect_match as match
from tools.tests import game_five_source_effect_oracle as g
from tools.tests import game_five_source_effect_native as native
from tools.tests import test_game_view_list_setup as view_setup
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary,TrackedCode
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
def state(m):return complete(m),m.current_pc,m.delay_of,m.root_accesses,m.trace,m.packets
class WindowStop(Exception):pass
class WindowCode(TrackedCode):
    def __getitem__(self,pc):
        if pc==0x15029BA4:raise WindowStop
        return super().__getitem__(pc)
class FiveSourceEffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.truth=cls.rom[match.ROM:match.ROM+280];cls.retail=list(struct.unpack('>70I',cls.truth))
        ctx=type('OriginalFiveSourceEffect',(),dict(root=ROOT,out=cls.out));cls.original=view_setup.ViewListSetupTests.original.__func__(ctx,'effect-original',(ROOT/match.ASM).read_text(encoding='utf-8'),match.FUNCTION)
        cls.blobs=[match.function_blob(o)for o in(cls.original,cls.prepared['qualified_compact'],cls.prepared['qualified_owner'])]
        cls.images=[match.bound_blob(b,r,match.symbols())for b,r in cls.blobs];cls.receipts={};assert all(w==cls.retail for w in cls.images)
    @classmethod
    def tearDownClass(cls):(cls.out/'effect-suite-receipt.json').write_text(json.dumps(cls.receipts,indent=2)+'\n',encoding='utf-8')
    def receipt(self,name,**v):self.receipts[name]=v
    def compare(self,c,images=None,factory=g.FACTORY,connected=None):
        initial=g.fixture(c);models=[]
        for words in(images or self.images):
            m=g.Oracle(words,initial,c,factory=factory,connected=connected);before=m.r[:];f=m.f[:]
            want,calls,packets=g.reference(initial,c,ra=before[31],factory=factory,connected=connected is not None);m.run()
            self.assertEqual(g.public(m.memory)if connected is not None else m.memory,g.public(want)if connected is not None else want,c)
            self.assertEqual(m.calls,calls,c);self.assertEqual(m.packets,packets,c)
            self.assertTrue(all(m.r[r]==before[r]for r in(*range(16,24),26,27,28,29,30,31)));self.assertEqual(m.f[20:],f[20:]);models.append(m)
        self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(state(models[0]),state(models[2]));return models
    def test_01_literal_body_bindings_neighbors_and_corruptions(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['neighbors']),(70,144,0,5,5))
        for raw,b in self.blobs:match.checked(raw,b,self.truth)
        raw,b=self.blobs[1]
        for at in range(280):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),b,self.truth)
        with self.assertRaises(ValueError):match.checked(raw,{212:[('R_MIPS_26','foreign')]},self.truth)
        for name in(match.MAKE,match.GUARDS):self.assertEqual((ROOT/name).read_bytes(),(self.out/'match-frozen'/name).read_bytes())
        self.receipt('owner',words=70,frame=144,guards=0,profile_changes=0,bindings=1,raw_padded_neighbors=5,raw_corruptions=280,binding_corruptions=1,Make_and_guard_CSV_unchanged=True)
    def test_02_gates_widths_partial_packet_and_live_home_aliases(self):
        seen=set();count=0
        for c in g.cases():
            for m in self.compare(c):seen.update(m.visits)
            count+=1
        self.assertTrue(set(range(match.ENTRY,match.ENTRY+280,4))<=seen)
        self.receipt('guest',cases_per_body=count,bodies=3,all70_words=True,all32_pointer_gates=True,signed16_duration_and_u8_channel=True,all256_channel_values=True,packet_bytes=88,defined_bytes=len(g.DEFINED),complete_guest_packet_and_memory=True,live_argument_home_mutations=True,output_home_aliases=True,saved_GPR_FPR_SP_RA=True)
    def test_03_every_own_access_cut_and_literal_states(self):
        count=0
        cases=[g.Case(mask=v)for v in(0,1,3,7,15)]+[g.Case(duration=0),g.Case(outcome=False),g.Case(),g.Case(mutation=3),g.Case(output=g.STACK-0x110+4,mutation=1)]
        for c in cases:
            initial=g.fixture(c);done=g.Oracle(self.retail,initial,c).run()
            for cut in range(done.root_accesses):
                models=[]
                for words in self.images:
                    m=g.Oracle(words,initial,c);m.root_fault=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(state(models[0]),state(models[2]));count+=1
        self.receipt('faults',own_access_prefixes=count,all_three_complete_states_equal=True,request_and_saved_RA_and_incoming_homes=True,fifth_pointer_reject_still_reads_sixth_half=True,null_factory_branch_delay_reloads_first_home=True)
    def test_04_original_factory_wrapper_and_core(self):
        code=g.helper_code(self.rom);seen=set();count=0
        for duration,channel,outcome,mutation,phase in itertools.product((1,0x7fff,0x8000,0xffff),(0,128,255,0x123400e1),(False,True),(0,1,2,3),(0,8)):
            c=g.Case(duration=duration,channel=channel,outcome=outcome,mutation=mutation,phase=phase,context=(0,0x7fffffff,0x80000000,0xffffffff)[channel%4]);models=self.compare(c,connected=code)
            for m in models:seen.update(m.visits)
            count+=1
        helper_visited=len(set(code)&seen)
        self.receipt('factory',cases_per_body=count,original_wrapper_words=28,original_core_words=114,helper_words_reached=helper_visited,whole_helper_coverage_claim=False,fixed_root_flags_0x401_and_resource_zero=True,independent_public_output_reference=True,full_guest_descriptor_copy=True,allocator_and_copy_and_zero_and_initializers_bounded=True,private_helper_stack_reference_claim=False)
    def test_05_original_caller_window_ignores_void_result(self):
        words=list(struct.unpack_from('>12I',self.rom,0x5591c));count=0;seen=set()
        for first,duration,channel,outcome,phase in itertools.product((0,0x30000),(0,1,0x8000,0x12340001),(0,0x123400ff),(False,True),(0,8)):
            record=0x35000;c=g.Case(duration=duration,channel=channel,outcome=outcome,phase=phase,context=0,pointers=(first,record+0x10,record+0x18,record+0x1c,record+0x20));initial=g.fixture(c);g.put(initial,g.STACK+phase+0x770,channel)
            want,calls,packets=g.reference(initial,c,ra=0x15028494);models=[]
            for image in self.images:
                code=dict(zip(range(match.ENTRY,match.ENTRY+280,4),image));m=g.Oracle(words,initial,c,entry=0x1502846c,connected=code,arguments=(first,0,0,0));m.r[2]=record;m.r[3]=duration&g.MASK;m.code=WindowCode(dict(m.code),m)
                with self.assertRaises(WindowStop):m.run()
                self.assertEqual(m.memory,want);self.assertEqual(m.calls,[(match.ENTRY,g.args(c)),*calls]);self.assertEqual(m.packets,packets);self.assertEqual(m.r[2],1);seen.update(m.visits);models.append(m)
            self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(state(models[0]),state(models[2]));count+=1
        self.assertTrue(set(range(0x1502846c,0x1502849c,4))<=seen)
        self.receipt('caller',cases_per_body=count,original_window_words=12,all_window_words=True,prior_A0_and_record_and_duration_are_explicit_preconditions=True,original_delay_store_truncation_and_result_one=True,complete_parent_claim=False)
    def test_06_independent_GNU_R26_rebases(self):
        links=0;count=0
        for i,target in enumerate((0x10004000,0x15018000,0x1ffffff0)):
            syms=dict(func_1513D524=target);images=[]
            for j,(raw,b)in enumerate(self.blobs):
                p=self.out/('effect-rebase-%d-%d'%(i,j));s=p.with_suffix('.s');o=p.with_suffix('.o');elf=p.with_suffix('.elf');ld=p.with_suffix('.ld');asm,missing=emit_function(raw,dict(value=0,size=280),b,match.FUNCTION,syms);self.assertFalse(missing);s.write_text(asm,encoding='utf-8')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(o),str(s)],check=True,capture_output=True);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%match.ENTRY,encoding='utf-8')
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',match.FUNCTION,'--defsym=func_1513D524=0x%X'%target,'-o',str(elf),str(o)],check=True,capture_output=True)
                w=list(struct.unpack('>70I',sections(elf)['.text'][1][:280]));self.assertEqual(w,match.bound_blob(raw,b,syms))
                functions,_,addresses=match.load_elf_functions(str(elf),'mips-linux-gnu-objdump');self.assertEqual(addresses[match.FUNCTION],match.ENTRY)
                definitions=[fields for _,name,fields,_ in match.symbol_rows(elf.read_bytes())if name==match.FUNCTION]
                self.assertEqual(len(definitions),1);self.assertEqual(definitions[0][1:3],(match.ENTRY,280))
                self.assertEqual(functions[match.FUNCTION],w+[0,0]);self.assertEqual(sections(elf)['.text'][1][280:],bytes(8));images.append(w);links+=1
            for mask,duration,outcome in itertools.product((0,15,31),(1,0xffff),(False,True)):
                self.compare(g.Case(mask=mask,duration=duration,outcome=outcome,mutation=1),images,factory=target);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,original_object_independent=True,all_R26_bindings=True)
    def test_07_native32_SDK_partial_fields_and_controls(self):
        checks=[]
        for label,b,opt in[('selected',None,o)for o in('-O0','-O2','-O3')]+[(n,b,'-O2')for n,b in native.controls().items()]:
            p=self.out/('effect-native-'+label+opt);s=p.with_suffix('.c');s.write_text(native.program(b),encoding='utf-8');cp=subprocess.run(native_command(opt)+['-o',str(p.relative_to(ROOT)),str(s.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);self.assertEqual((cp.returncode,cp.stdout,cp.stderr),(0,'',''),(label,opt))
            run=subprocess.run([str(p)],cwd=ROOT,capture_output=True,text=True);self.assertEqual((run.returncode,run.stdout,run.stderr),(0 if label=='selected'else 42,'',''),(label,opt));checks.append(dict(label=label,opt=opt,exit=run.returncode))
        self.receipt('native',positive_calls=540672,SDK32_UBSan=True,all65536_duration_patterns=True,all32_pointer_masks=True,all_descriptor_offsets_asserted=True,defined_request_bytes_only=True,reserved_bytes_not_scored=True,complete_output_and_guards=True,direct_and_compatible_callback=True,controls_rejected=10,checks=checks)
    def test_08_literal_image_and_former_placeholder_and_wrong_shape(self):
        q=self.prepared['report'];self.assertEqual((q['strict_changed_bytes'],q['strict_exclusions'],q['functions']),(215,0,6052));self.assertEqual(q['changed_bodies'],[match.FUNCTION])
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();self.assertEqual(match.strict_image(before,after,self.truth),215)
        for at in(0,0x100,match.elf_slot_offset(after,match.ENTRY,280),len(after)//2,len(after)-1):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.truth)
        bs,ns,_=candidate.source_states((ROOT/match.SOURCE).read_text(encoding='utf-8'));old,_=candidate.compile_owner(ROOT,self.out,bs,'effect-former-stub')
        with self.assertRaises(ValueError):match.checked(*match.function_blob(old),self.truth)
        wrong,diag=candidate.compile_owner(ROOT,self.out,ns.replace('request.red = request.green = request.blue = 200;\n        request.alpha = 200;','request.red = request.green = request.blue = request.alpha = 200;'),'effect-wrong-color-shape');self.assertFalse(diag)
        with self.assertRaises(ValueError):match.checked(*match.function_blob(wrong),self.truth)
        self.receipt('image',changed_bytes=215,exclusions=0,all6052_addresses_fixed=True,protected_bytes=189088,protected_owners=720,image_corruptions=5,former_stub_and_equal_length_shape_rejected=True,guard_and_Make_and_conversion_CSV_unchanged=True)
if __name__=='__main__':unittest.main()
