"""Two quad banks: exact owner, signed-halfword state, factory and caller ABI."""
import itertools, json, struct, subprocess, unittest
from dataclasses import replace
from tools.experiments import game_double_bank_record_constructor_candidates as candidate
from tools.experiments import game_double_bank_record_constructor_match as match
from tools.tests import game_double_bank_record_constructor_oracle as g
from tools.tests import game_double_bank_record_constructor_native as native
from tools.tests import test_game_view_list_setup as view_setup
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary, TrackedCode
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT

def state(m):return complete(m),m.current_pc,m.delay_of,m.root_accesses
class WindowStop(Exception):pass
class WindowCode(TrackedCode):
    def __getitem__(self,pc):
        if pc in (0x1502C33C,0x15113E08):raise WindowStop
        return super().__getitem__(pc)

class DoubleBankRecordConstructorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.truth=cls.rom[match.ROM:match.ROM+276]
        cls.retail=list(struct.unpack('>69I',cls.truth));ctx=type('OriginalQuadConstructor',(),dict(root=ROOT,out=cls.out))
        cls.original=view_setup.ViewListSetupTests.original.__func__(ctx,'constructor-original',(ROOT/match.ASM).read_text(encoding='utf-8'),match.FUNCTION)
        cls.blobs=[match.function_blob(o) for o in (cls.original,cls.prepared['qualified_compact'],cls.prepared['qualified_owner'])]
        cls.images=[match.bound_blob(raw,b,g.SYMS) for raw,b in cls.blobs];assert all(w==cls.retail for w in cls.images)
    def receipt(self,name,**v):(self.out/('constructor-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    def compare(self,c=g.Case(),s=g.SYMS,images=None,entry=match.ENTRY):
        initial=g.fixture(c);models=[]
        for words in (self.images if images is None else images):
            m=g.Oracle(words,initial,c,entry,s);want,calls,result=g.reference(initial,c,s,ra=m.before[31]);m.run()
            self.assertEqual((m.memory,m.calls,m.r[2]),(want,calls,result),c)
            self.assertEqual(m.r[16:24],m.before[16:24]);self.assertEqual(m.r[28:32],m.before[28:32]);self.assertEqual(m.f[20:],m.before_f[20:]);models.append(m)
        self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(state(models[0]),state(models[2]));return models
    def test_01_direct_owner_sdk_layout_and_corruptions(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings'],q['neighbors']),(69,48,0,1,4));self.assertTrue(q['compact_GPR_mask_body_derived'])
        raw,b=self.blobs[1]
        for at in range(276):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),b,self.truth)
        with self.assertRaises(ValueError):match.checked(raw,{76:[('R_MIPS_26','foreign')]},self.truth)
        self.receipt('owner',words=69,frame=48,guards=0,bindings=1,raw_and_padded_neighbors=4,raw_corruptions=276,binding_corruptions=1,SDK_Vtx=True,owner_pointer_ABI=True,compact_GPR_mask_before='A000C074',compact_GPR_mask_after='A300DFFE',body_derived_mask=True)
    def test_02_independent_byte_reference_and_argument_widths(self):
        count=0;seen=set()
        for c in g.cases():seen.update(self.compare(c)[0].visits);count+=1
        self.assertTrue(set(range(match.ENTRY,match.ENTRY+276,4))<=seen)
        self.receipt('guest',cases_per_body=count,bodies=3,all69_words=True,all256_bytes_for_three_fields=True,full_word_owner_and_flags=True,base_and_optional_sizes=True,all48_vertex_bytes_and18_tail_bytes=True,all_retained_bytes=True,allocation_failure_and_pointer_return=True,live_homes_and_saved_flag_mutations=True,saved_GPR_FPR_SP_ABI=True)
    def test_03_private_aliases_and_fault_prefixes(self):
        count=0
        offsets=[*g.HALVES,0x110,0x111,0x112,0x113,0x120,0x121,0x124,*range(0x128,0x13A)]
        written={x+j for x in g.HALVES for j in range(2)}|set(offsets)
        for delta,flags,phase,mutation in itertools.product(range(-0x150,0x41,4),(0,1),(0,8),(0,2,4)):
            if any(0x1C<=delta+x<0x20 for x in written):continue
            c=g.Case(flags=flags,phase=phase,mutation=mutation,record=g.STACK+phase-0x30+delta)
            self.compare(c);count+=1
        cuts=0
        for c in (g.Case(),g.Case(flags=0),g.Case(outcome=0),g.Case(mutation=15),g.Case(record=g.STACK-0x30-0xE0)):
            initial=g.fixture(c);done=g.Oracle(self.retail,initial,c).run()
            for cut in range(done.root_accesses):
                models=[]
                for words in (self.retail,self.images[2]):
                    m=g.Oracle(words,initial,c);m.root_fault=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(state(models[0]),state(models[1]));cuts+=1
        self.receipt('aliases',cases_per_body=count,returned_record_aliases_live_homes=True,saved_return_address_preserved_for_complete_runs=True,fault_prefixes=cuts,literal_complete_fault_states=True,private_aliases_guest_only=True)
    def test_04_original_factory_and_actual_six_argument_ABI(self):
        raw=self.rom[0x194F18:0x194F88];factory=list(struct.unpack('>28I',raw));count=0;seen=set()
        before=(self.out/'match-frozen'/match.ELF).read_bytes();at=match.elf_slot_offset(before,g.FACTORY,112);production_exact=before[at:at+112]==raw
        for flags,outcome,mutation,phase in itertools.product((0,1,2,0xFFFFFFFF),(0,1),(0,1,8,9),(0,8)):
            c=g.Case(flags=flags,outcome=outcome,mutation=mutation,phase=phase,factory=True);initial=g.fixture(c);models=[]
            for words in self.images:
                m=g.Oracle(words,initial,c,connected=dict(zip(range(g.FACTORY,g.FACTORY+112,4),factory)));want,calls,result=g.reference(initial,c);m.run()
                self.assertEqual((g.public(m.memory),m.calls,m.r[2]),(g.public(want),calls,result));models.append(m);seen.update(m.visits)
            self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(state(models[0]),state(models[2]));count+=1
        self.assertTrue(set(range(g.FACTORY,g.FACTORY+112,4))<=seen)
        self.receipt('factory',cases_per_body=count,original_words=28,all_factory_words=True,production_factory_original_literal=production_exact,fifth_and_sixth_byte_homes=True,five_argument_allocator_core_ABI=True,header_bytes1_and12=True,allocator_core_and_initializer_bounded=True)
    def test_05_two_original_caller_windows_store_return_pointer(self):
        count=0;seen=[set(),set()]
        for which,typ,existing,outcome,phase in itertools.chain(
            ((0,t,e,o,p) for t,e,o,p in itertools.product(range(256),(0,g.RESULT),(0,1),(0,8))),
            ((1,0,e,o,p) for e,o,p in itertools.product((0,g.RESULT),(0,1),(0,8)))):
            entry,rom,n,ret,field=(0x1502C2DC,0x5978C,18,0x1502C318,0x2D4) if which==0 else (0x15113DC8,0x141278,10,0x15113DE8,0x94)
            words=list(struct.unpack_from('>%dI'%n,self.rom,rom));c=g.Case(kind=which,mode=2 if which==0 and typ==0x4D else 0,flags=which,variant=int(which==0 and typ==0x4D),outcome=outcome,phase=phase)
            initial=g.fixture(c);initial[g.OWNER+4]=typ;g.put(initial,g.OWNER+field,existing);models=[]
            for target in (self.retail,self.images[2]):
                m=g.Oracle(words,initial,c,entry=entry,connected=dict(zip(range(match.ENTRY,match.ENTRY+276,4),target)));m.r[17]=m.before[17]=g.OWNER;m.code=WindowCode(dict(m.code),m)
                want,calls,result=g.reference(initial,c,ra=ret) if not existing else (dict(initial),[],None)
                if not existing:g.put(want,g.OWNER+field,result)
                with self.assertRaises(WindowStop):m.run()
                self.assertEqual(g.public(m.memory),g.public(want))
                self.assertEqual(m.calls,[(match.ENTRY,(c.kind,c.owner,c.mode,c.flags,c.variant)),*calls] if not existing else [])
                self.assertEqual(m.r[17],g.OWNER);models.append(m);seen[which].update(m.visits)
            self.assertEqual(state(models[0]),state(models[1]));count+=1
        for k,(entry,n) in enumerate(((0x1502C2DC,18),(0x15113DC8,10))):self.assertTrue(set(range(entry,entry+4*n,4))<=seen[k])
        self.receipt('callers',cases_per_body=count,window_words=[18,10],all_window_words=True,complete_parents_claim=False,all256_first_caller_type_bytes=True,existing_pointer_gate=True,fifth_argument_delay_store=True,return_pointer_stored_at=[0x2D4,0x94])
    def test_06_independent_GNU_relocations(self):
        count=links=0
        for k,(entry,s) in enumerate(((match.ENTRY,g.SYMS),(0x18017FFC,dict(func_15167A68=0x18038000)),(0x1A028000,dict(func_15167A68=0x1A038004)))):
            images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                t,fs,rs=match.parse_object(obj);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('constructor-rebase-%d-%d'%(k,j));p.with_suffix('.s').write_text(asm,encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,'--defsym=func_15167A68=0x%X'%s['func_15167A68'],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
                images.append(list(struct.unpack_from('>69I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for c in list(g.cases())[::173]:self.compare(c,s,images,entry);count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,R26_factory_binding=True,independent_entry_and_provider_addresses=True)
    def test_07_native32_SDK_layout_factory_and_controls(self):
        text,n=native.program(ROOT);p=self.out/'constructor-native.c';p.write_text(text,encoding='utf-8')
        for opt in ('-O0','-O2','-O3'):
            exe=self.out/('constructor-native'+opt);r=subprocess.run([*native_command(opt),'-mstackrealign',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),opt);self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',rows_per_path_profile=n,positive_calls=n*6,profiles=['O0','O2','O3'],SDK_native32=True,UBSan=True,actual_Vtx_layout=True,actual_factory_C=True,direct_and_five_argument_callback_ABI=True,complete_record_and_sentinels=True,effective_controls=list(g.controls()),private_aliases_guest_only=True)
    def test_08_literal_whole_image_and_stub_controls(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();delta=match.strict_image(before,after,self.truth);at=match.elf_slot_offset(after,match.ENTRY,276)
        for off in (0,at,at+275,at+276,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.truth)
        stub=list(struct.unpack_from('>69I',before,at));m=g.Oracle(stub,g.fixture()).run();want,calls,result=g.reference(g.fixture())
        self.assertNotEqual((m.memory,m.calls,m.r[2]),(want,calls,result))
        self.receipt('image',changed_bytes=delta,exclusions=0,metadata_permutations=0,corruptions=5,stub_rejected=True)

if __name__=='__main__':unittest.main()
