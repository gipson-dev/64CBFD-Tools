"""Direct owner request: literal words, ABI, partial records and production image."""
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_owner_position_request_candidates as candidate
from tools.experiments import game_owner_position_request_match as match
from tools.tests import game_owner_position_request_oracle as g
from tools.tests import game_owner_position_request_native as native
from tools.tests import test_game_view_list_setup as view_setup
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary,TrackedCode
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
def state(m):return complete(m),m.current_pc,m.delay_of,m.root_accesses,m.trace,m.requests,m.payloads
class WindowStop(Exception):pass
class WindowCode(TrackedCode):
    def __getitem__(self,pc):
        if pc in(0x151A3454,0x151A4F50):raise WindowStop
        return super().__getitem__(pc)
class CallerOracle(g.Oracle):
    def record_call(self,t):
        if t==0x151A4590:
            a=tuple(self.arguments(2));self.calls.append((t,a));self.events.append(('CALL',t,a))
        else:super().record_call(t)
    def hook(self,t):
        if t==0x151A4590:self.r[2]=0x2468
        else:super().hook(t)
class OwnerPositionRequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.truth=cls.rom[match.ROM:match.ROM+280];cls.retail=list(struct.unpack('>70I',cls.truth))
        ctx=type('OriginalOwnerRequest',(),dict(root=ROOT,out=cls.out));cls.original=view_setup.ViewListSetupTests.original.__func__(ctx,'request-original',(ROOT/match.ASM).read_text(encoding='utf-8'),match.FUNCTION)
        cls.blobs=[match.function_blob(o)for o in(cls.original,cls.prepared['qualified_compact'],cls.prepared['qualified_owner'])]
        cls.images=[match.bound_blob(b,r,match.symbols())for b,r in cls.blobs];cls.receipts={};assert all(w==cls.retail for w in cls.images)
    @classmethod
    def tearDownClass(cls):(cls.out/'request-suite-receipt.json').write_text(json.dumps(cls.receipts,indent=2)+'\n',encoding='utf-8')
    def receipt(self,name,**v):self.receipts[name]=v
    def compare(self,c,images=None,s=g.SYMS,connected=None):
        initial=g.fixture(c);models=[]
        for words in(images or self.images):
            m=g.Oracle(words,initial,c,s=s,connected=connected);before=m.r[:];f=m.f[:]
            want,calls,requests,payloads,answer=g.reference(initial,c,ra=before[31],s=s,connected=connected is not None);m.run()
            self.assertEqual(g.public(m.memory)if connected is not None else m.memory,g.public(want)if connected is not None else want,c)
            self.assertEqual((m.calls,m.requests,m.payloads,m.r[2]),(calls,requests,payloads,answer),c)
            self.assertTrue(all(m.r[r]==before[r]for r in(*range(16,24),26,27,28,29,30,31)));self.assertEqual(m.f[20:],f[20:]);models.append(m)
        self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(state(models[0]),state(models[2]));return models
    def test_01_literal_body_bindings_neighbors_and_corruptions(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['neighbors']),(70,168,0,22,22))
        self.assertEqual(q['compact_GPR_mask'],dict(GPR_before='E3FFFFFE',GPR_after='E3FFFFFE',FPR_before='00075757',FPR_after='00075757',body_derived=True))
        for raw,b in self.blobs:match.checked(raw,b,self.truth)
        raw,b=self.blobs[1]
        for at in range(280):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),b,self.truth)
        for at in b:
            bad=dict(b);bad[at]=[('R_MIPS_26','foreign')]
            with self.assertRaises(ValueError):match.checked(raw,bad,self.truth)
        for name in(match.MAKE,match.GUARDS):self.assertEqual((ROOT/name).read_bytes(),(self.out/'match-frozen'/name).read_bytes())
        self.receipt('owner',words=70,frame=168,guards=0,profile_changes=0,bindings=4,raw_padded_neighbors=22,raw_corruptions=280,binding_corruptions=4,all_pools_and_metadata_unchanged=True,existing_C_caller_and_ASM_neighbor_preserved=True)
    def test_02_snapshot_partial_records_and_live_home_aliases(self):
        seen=set();count=0
        for c in g.cases():
            for m in self.compare(c):seen.update(m.visits)
            count+=1
        self.assertTrue(set(range(match.ENTRY,match.ENTRY+280,4))<=seen)
        self.receipt('guest',cases_per_body=count,bodies=3,all70_words=True,all256_channel_values=True,payload_bytes=80,request_bytes=28,full_guest_memory_and_records=True,query_factory_mutations=True,live_channel_home=True,forward_alias_copies_and_saved_result_reload=True,saved_GPR_FPR_SP_RA=True)
    def test_03_every_own_access_cut_and_literal_states(self):
        count=0
        cases=[g.Case(active=False),g.Case(query=0),g.Case(outcome=False),g.Case(),g.Case(mutation=15),g.Case(destination=g.STACK-0x70),g.Case(input=g.STACK+4)]
        for c in cases:
            initial=g.fixture(c);done=g.Oracle(self.retail,initial,c).run()
            for cut in range(done.root_accesses):
                models=[]
                for words in self.images:
                    m=g.Oracle(words,initial,c);m.root_fault=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(state(models[0]),state(models[2]));count+=1
        self.receipt('faults',own_access_prefixes=count,all_three_complete_states_equal=True,first_word_not_pointer_null_gate=True,query_and_saved_result_and_channel_homes=True)
    def test_04_original_query_copy_and_factory(self):
        code=g.helper_code(self.rom);seen=set();count=0
        for query,outcome,mutation,slot,flags,phase in itertools.product((0,1),(False,True),(0,2,8,14),(0,128,255),(0,15),(0,8)):
            c=g.Case(query=query,outcome=outcome,mutation=mutation,slot=slot,actor_flags=flags,phase=phase,points=g.POINTS[slot%4])
            for m in self.compare(c,connected=code):seen.update(m.visits)
            count+=1
        self.receipt('helpers',cases_per_body=count,original_query_words=26,original_copy_words=11,original_factory_words=115,helper_words_reached=len(set(code)&seen),whole_helper_coverage_claim=False,independent_public_output_reference=True,resource_zero_optional_null=True,transform_allocator_zero_bounded=True,private_helper_stack_reference_claim=False)
    def test_05_both_original_caller_windows(self):
        count=0;seen=set()
        for which,active,query,outcome,channel,mutation in itertools.product((0,1),(False,True),(0,1),(False,True),(0,255),(0,4)):
            parent=0x90000;c=g.Case(active=active,query=query,outcome=outcome,channel=channel,mutation=mutation,input=g.STACK+0x68 if which==0 else parent+0x28)
            initial=g.fixture(c);initial.update({parent+i:0x59 for i in range(0x28)});initial[parent+12]=channel;initial[g.STACK+0x9f]=channel
            if which==0:
                start,rom,n,ra=0x151A3440,0x1D08F0,5,0x151A3448;g.put(initial,g.STACK+0x8c,c.points[2])
            else:
                start,rom,n,ra=0x151A4F34,0x1D23E4,7,0x151A4F48;initial[g.STACK+0x1b]=1;g.put(initial,g.STACK+0x20,parent)
            want,calls,requests,payloads,answer=g.reference(initial,c,ra=ra);models=[];window=list(struct.unpack_from('>%dI'%n,self.rom,rom))
            for words in self.images:
                code=dict(zip(range(match.ENTRY,match.ENTRY+280,4),words));m=CallerOracle(window,initial,c,entry=start,connected=code,arguments=(c.input,channel,parent,0));m.r[16]=parent;m.f[8]=c.points[2];m.code=WindowCode(dict(m.code),m)
                with self.assertRaises(WindowStop):m.run()
                expected=[(match.ENTRY,(c.input,channel)),*calls]
                if which==0:expected.append((0x151A4590,(parent,channel)));self.assertEqual(m.r[2],0x2468)
                else:self.assertEqual((m.r[3],m.r[6],m.r[2]),(1,parent,answer))
                self.assertEqual(m.memory,want);self.assertEqual(m.calls,expected);self.assertEqual((m.requests,m.payloads),(requests,payloads));seen.update(m.visits);models.append(m)
            self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(state(models[0]),state(models[2]));count+=1
        self.assertTrue(set(range(0x151A3440,0x151A3454,4))|set(range(0x151A4F34,0x151A4F50,4))<=seen)
        self.receipt('callers',cases_per_body=count,original_window_words=[5,7],all_window_words=True,explicit_prior_arguments_parent_F8_and_stack_preconditions=True,second_caller_flag_and_owner_restored=True,complete_parent_claim=False,followup_provider_bounded=True)
    def test_06_independent_GNU_R26_rebases(self):
        links=count=0
        for i,base in enumerate((0x10004000,0x15018000,0x1fff0000)):
            syms=dict(memcpy=base,func_151A4E34=base+0x40,func_15147A80=base+0x80);images=[]
            for j,(raw,b)in enumerate(self.blobs):
                p=self.out/('request-rebase-%d-%d'%(i,j));s=p.with_suffix('.s');o=p.with_suffix('.o');elf=p.with_suffix('.elf');ld=p.with_suffix('.ld');asm,missing=emit_function(raw,dict(value=0,size=280),b,match.FUNCTION,syms);self.assertFalse(missing);s.write_text(asm,encoding='utf-8')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(o),str(s)],check=True,capture_output=True);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%match.ENTRY,encoding='utf-8')
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,a)for n,a in syms.items()],'-o',str(elf),str(o)],check=True,capture_output=True)
                w=list(struct.unpack('>70I',sections(elf)['.text'][1][:280]));self.assertEqual(w,match.bound_blob(raw,b,syms));functions,_,addresses=match.load_elf_functions(str(elf),'mips-linux-gnu-objdump');self.assertEqual(addresses[match.FUNCTION],match.ENTRY)
                definitions=[f for _,n,f,_ in match.symbol_rows(elf.read_bytes())if n==match.FUNCTION];self.assertEqual(len(definitions),1);self.assertEqual(definitions[0][1:3],(match.ENTRY,280));self.assertEqual(functions[match.FUNCTION],w+[0,0]);self.assertEqual(sections(elf)['.text'][1][280:],bytes(8));images.append(w);links+=1
            for query,outcome,mutation in itertools.product((0,1),(False,True),(0,15)):
                self.compare(g.Case(query=query,outcome=outcome,mutation=mutation),images,s=syms);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,all4_R26_bindings=True,entry_and_size_and_alignment_tail_pinned=True)
    def test_07_native32_SDK_defined_fields_and_controls(self):
        checks=[]
        for label,b,opt in[('selected',None,o)for o in('-O0','-O2','-O3')]+[(n,b,'-O2')for n,b in native.controls().items()]:
            p=self.out/('request-native-'+label+opt);s=p.with_suffix('.c');s.write_text(native.program(b),encoding='utf-8');cp=subprocess.run(native_command(opt)+['-o',str(p.relative_to(ROOT)),str(s.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);self.assertEqual((cp.returncode,cp.stdout,cp.stderr),(0,'',''),(label,opt))
            run=subprocess.run([str(p)],cwd=ROOT,capture_output=True,text=True);self.assertEqual((run.returncode,run.stdout,run.stderr),(0 if label=='selected'else 42,'',''),(label,opt));checks.append(dict(label=label,opt=opt,exit=run.returncode))
        self.receipt('native',positive_calls=393216,SDK32_UBSan=True,all256_channels=True,all_used_offsets_asserted=True,payload_defined_bytes=[59,71],request_defined_bytes=[9,21],reserved_bytes_not_scored=True,complete_output_guards=True,direct_and_compatible_callback=True,controls_rejected=10,checks=checks)
    def test_08_literal_image_and_rejected_stub_and_shape(self):
        q=self.prepared['report'];self.assertEqual((q['strict_changed_bytes'],q['strict_exclusions'],q['functions']),(204,0,6052));self.assertEqual(q['changed_bodies'],[match.FUNCTION]);before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();self.assertEqual(match.strict_image(before,after,self.truth),204)
        for at in(0,0x100,match.elf_slot_offset(after,match.ENTRY,280),len(after)//2,len(after)-1):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.truth)
        bs,ns,_=candidate.source_states((ROOT/match.SOURCE).read_text(encoding='utf-8'));old,_=candidate.compile_owner(ROOT,self.out,bs,'request-former-stub')
        with self.assertRaises(ValueError):match.checked(*match.function_blob(old),self.truth)
        wrong,diag=candidate.compile_owner(ROOT,self.out,ns.replace('payload.value40 = 0.0f;\n    payload.value48 = 0.0f;','payload.value40 = payload.value48 = 0.0f;'),'request-wrong-zero-shape');self.assertFalse(diag)
        with self.assertRaises(ValueError):match.checked(*match.function_blob(wrong),self.truth)
        self.receipt('image',changed_bytes=204,exclusions=0,all6052_addresses_fixed=True,protected_bytes=189088,protected_owners=720,image_corruptions=5,former_stub_and_wrong_zero_assignment_shape_rejected=True,guard_Make_conversion_CSV_unchanged=True)
if __name__=='__main__':unittest.main()
