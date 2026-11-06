"""Keyed registration: signed widths, rollback, exact shared helper and caller window."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_keyed_buffer_registration_candidates as candidate
from tools.experiments import game_keyed_buffer_registration_match as match
from tools.tests import game_keyed_buffer_registration_oracle as g
from tools.tests import game_keyed_buffer_registration_native as native
from tools.tests import test_game_view_list_setup as view_setup
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary,TrackedCode
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
WINDOW,RETURN,RECORD=0x1502A774,0x1502A79C,0x70000

def state(m):return complete(m),m.current_pc,m.delay_of,m.root_accesses
class WindowStop(Exception):pass
class WindowCode(TrackedCode):
    def __getitem__(self,pc):
        if pc in(0x1502A7A4,0x1502A7B4,0x1502A88C):raise WindowStop
        if pc==RETURN:self.owner.r[2]=self.owner.poison
        return super().__getitem__(pc)

class KeyedBufferRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.truth=cls.rom[match.ROM:match.ROM+268]
        cls.retail=list(struct.unpack('>67I',cls.truth));ctx=type('OriginalKeyedRegistration',(),dict(root=ROOT,out=cls.out))
        cls.original=view_setup.ViewListSetupTests.original.__func__(ctx,'registration-original',(ROOT/match.ASM).read_text(encoding='utf-8'),match.FUNCTION)
        cls.blobs=[match.function_blob(o)for o in(cls.original,cls.prepared['qualified_compact'],cls.prepared['qualified_owner'])]
        cls.images=[match.bound_blob(raw,b,g.SYMS)for raw,b in cls.blobs];assert all(w==cls.retail for w in cls.images)
    def receipt(self,n,**v):(self.out/('registration-'+n+'.json')).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    def compare(self,c=g.Case(),s=g.SYMS,images=None,entry=match.ENTRY,initial=None):
        initial=g.fixture(c,s)if initial is None else initial;models=[]
        for w in(self.images if images is None else images):
            m=g.Oracle(w,initial,c,entry,s);want,calls=g.reference(initial,c,s,saved={r:m.before[r]for r in(16,17,31)})
            m.run();self.assertEqual((m.memory,m.calls),(want,calls),c);self.assertEqual(m.f[20:],m.before_f[20:]);models.append(m)
        self.assertEqual(state(models[0]),state(models[-1]));return models

    def test_01_direct_owner_shared_type_and_masks(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings'],q['neighbors']),(67,32,0,9,14));self.assertTrue(q['compact_GPR_mask_body_derived'])
        raw,b=self.blobs[1]
        for at in range(268):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),b,self.truth)
        for at in b:
            bad=dict(b);bad[at]=[('R_MIPS_LO16','foreign')]
            with self.assertRaises(ValueError):match.checked(raw,bad,self.truth)
        t,fs,rs=match.parse_object(self.prepared['qualified_owner']);f=fs['func_15188A58'];a,n=f['value'],f['size']
        self.assertEqual((n,t[a:a+n]),(68,self.rom[0x1B5F08:0x1B5F4C]))
        self.receipt('owner',raw_and_padded_neighbors=14,raw_corruptions=268,binding_corruptions=9,guards=0,shared_node20_next_offset12=True,append_original17_words_unchanged=True,compact_GPR_mask_before='A01F407C',compact_GPR_mask_after='A31FDFFE',complete_body_mask_union=True)

    def test_02_independent_signed_reference_and_state_transitions(self):
        count=0;seen=set()
        for c in g.cases():
            m=self.compare(c)[0];seen.update(m.visits);count+=1
        self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+268,4))-{match.ENTRY+0x60})
        self.receipt('guest',cases_per_body=count,bodies=3,reachable_words=66,unreachable_duplicate_next_load=1,all67_literal=True,signed16_vs_full_signed32=True,all256_mode_bytes=True,first_duplicate_match_only=True,both_allocation_failures_and_rollback=True,all384_bytes_cleared=True,retained_byte5_preserved=True,provider_mutations_and_saved_ABI=True)

    def test_03_live_homes_head_and_output_aliases_and_faults(self):
        count=0
        for phase,off,mutation in itertools.product((0,8),(0,4,8,12,16),(0,15)):
            c=g.Case(node=g.STACK+phase+off,phase=phase,mutation=mutation);self.compare(c);count+=1
        for phase,off,timer in itertools.product((0,8),(0,4,8,12),(-32769,32768,65535)):
            c=g.Case(1,0,timer=timer,phase=phase);initial=g.fixture(c);p=g.STACK+phase+off
            for i in range(20):initial[p+i]=initial[g.NODES+i]
            g.put(initial,p+12,0);g.put(initial,g.HEAD,p);self.compare(c,initial=initial);count+=1
        for buf,count_nodes,mutation in itertools.product((g.NEW,g.NEW+4,g.NEW+8,g.NODES),(0,4),(0,7)):
            self.compare(g.Case(count_nodes,buffer=buf,mutation=mutation));count+=1
        for phase,field in itertools.product((0,8),('timer','mode','buffer','old_buffer')):
            at=g.STACK+phase+(4 if field=='timer'else 8)if field in('timer','mode')else g.NEW+8 if field=='buffer'else g.NODES+8
            s=dict(g.SYMS,D_800DF7CC=at);c=g.Case(1,0,phase=phase)
            if field=='timer':c=replace(c,timer=g.NODES)
            if field=='mode':c=replace(c,mode=g.NODES)
            if field=='buffer':c=replace(c,count=0,match=-1)
            images=[match.bound_blob(raw,b,s)for raw,b in self.blobs];self.compare(c,s,images);count+=1
        cuts=0
        for c in(g.Case(4,2,timer=65535),g.Case(outcome=0),g.Case(outcome=1),g.Case(mutation=7,residue=3),g.Case(node=g.STACK,mutation=15)):
            initial=g.fixture(c);done=g.Oracle(self.retail,initial,c).run()
            for cut in range(done.root_accesses):
                models=[]
                for w in(self.retail,self.images[2]):
                    m=g.Oracle(w,initial,c);m.root_fault=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(state(models[0]),state(models[1]));cuts+=1
        self.receipt('aliases',cases_per_body=count,incoming_timer_and_mode_homes=True,head_relocations_and_late_reads=True,overlapping_returned_node_buffer_and_old_list=True,fault_prefixes=cuts,literal_full_fault_states_equal=True,private_aliases_guest_only=True)

    def test_04_complete_original_helpers(self):
        zero=list(struct.unpack_from('>40I',self.rom,0x226F0));wrapper=list(struct.unpack_from('>11I',self.rom,0x3C40));append=list(struct.unpack_from('>17I',self.rom,0x1B5F08))
        before=(self.out/'match-frozen'/match.ELF).read_bytes()
        for va,raw in((g.ZERO,self.rom[0x226F0:0x22790]),(g.ALLOC,self.rom[0x3C40:0x3C6C]),(g.APPEND,self.rom[0x1B5F08:0x1B5F4C])):
            at=match.elf_slot_offset(before,va,len(raw));self.assertEqual(before[at:at+len(raw)],raw)
        seen=set();count=0
        for n,outcome,mutation,residue,phase in itertools.product((0,1,4),range(3),(0,3),range(4),(0,8)):
            c=g.Case(n,-1,outcome=outcome,mutation=mutation,residue=residue,phase=phase);initial=g.fixture(c);models=[]
            for w in self.images:
                code=dict(zip(range(g.ZERO,g.ZERO+160,4),zero));code.update(zip(range(g.ALLOC,g.ALLOC+44,4),wrapper));code.update(zip(range(g.APPEND,g.APPEND+68,4),append))
                m=g.Oracle(w,initial,c,connected=code);want,calls=g.reference(initial,c,saved={r:m.before[r]for r in(16,17,31)});m.run()
                self.assertEqual(g.public(m.memory),g.public(want));self.assertEqual([(t,a)for t,a in m.calls if t!=g.CORE],calls)
                roots=[a for t,a in m.calls if t==g.ALLOC];cores=[a for t,a in m.calls if t==g.CORE];self.assertEqual(cores,[(a[0],a[1],a[2],0,a[3])for a in roots]);models.append(m);seen.update(m.visits)
            self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(state(models[0]),state(models[2]));count+=1
        self.assertTrue(set(range(g.ZERO,g.ZERO+156,4))<=seen);self.assertTrue(set(range(g.ALLOC,g.ALLOC+44,4))<=seen)
        self.assertEqual(seen&set(range(g.APPEND,g.APPEND+68,4)),set(range(g.APPEND,g.APPEND+68,4))-{g.APPEND+56})
        self.receipt('helpers',cases_per_body=count,original_allocator_wrapper_words=11,original_bzero_slot_words=40,all39_bzero_body_words=True,original_append_words=17,append_reachable_words=16,unreachable_append_store_preserved=True,wrapper_five_argument_core_ABI=True,allocator_core_and_free_bounded=True)

    def test_05_original_caller_window_and_ignored_return(self):
        window=list(struct.unpack_from('>12I',self.rom,0x57C24));count=0;seen=set()
        for key,gate,timer,byte,outcome,phase,poison in itertools.product((0,0x81234567),(0,1),(-32769,-1,32768,65535),(0,127,128,255),range(3),(0,8),(0,0xFFFFFFFF)):
            c=g.Case(1,-1,timer=timer,mode=(byte^128)-128,outcome=outcome,phase=phase,key=key);initial=g.fixture(c);home=g.STACK+phase
            initial.update({RECORD+i:0 for i in range(8)});initial[RECORD+4]=gate;initial[RECORD+5]=byte
            for off,v in((0xE8,key),(0xDC,0x70000000),(0xF4,0)):g.put(initial,home+off,v)
            models=[]
            for w in(self.retail,self.images[2]):
                m=g.Oracle(window,initial,c,entry=WINDOW,connected=dict(zip(range(match.ENTRY,match.ENTRY+268,4),w)));m.r[16]=m.before[16]=RECORD;m.r[2]=(0x70000000+timer)&0xFFFFFFFF;m.poison=poison;m.code=WindowCode(dict(m.code),m)
                want,calls=g.reference(initial,c,saved={16:RECORD,17:m.before[17],31:RETURN})if key and not gate else(initial,[])
                with self.assertRaises(WindowStop):m.run()
                self.assertEqual(g.public(m.memory),g.public(want));self.assertEqual(m.calls,[(match.ENTRY,(key,timer&0xFFFFFFFF,c.mode&0xFFFFFFFF)),*calls]if key and not gate else[])
                if key and not gate:self.assertEqual(m.r[2],1)
                self.assertEqual(m.r[16],RECORD);self.assertEqual(m.r[17],m.before[17]);models.append(m);seen.update(m.visits)
            self.assertEqual(state(models[0]),state(models[1]));count+=1
        self.assertTrue(set(range(WINDOW,WINDOW+48,4))<=seen)
        self.receipt('caller',cases_per_body=count,original_window_words=12,all_window_words=True,containing_parent_words=826,complete_parent_claim=False,key_reload_duration_subtraction_and_signed_mode_delay=True,return_poison_values=2,return1_after_call=True)

    def test_06_independent_GNU_rebases(self):
        count=links=0
        layouts=((match.ENTRY,g.SYMS),(0x18017FFC,dict(D_800DF7CC=0x89007FFC,allocate_memory=0x18028000,func_10004074=0x18038000,bzero=0x18048000,func_15188A58=0x18058000)),(0x1A028000,dict(D_800DF7CC=0x89008000,allocate_memory=0x1A038004,func_10004074=0x1A048008,bzero=0x1A05800C,func_15188A58=0x1A068010)))
        for k,(entry,s)in enumerate(layouts):
            images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                t,fs,rs=match.parse_object(obj);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('registration-rebase-%d-%d'%(k,j));p.with_suffix('.s').write_text(asm,encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,v)for n,v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
                images.append(list(struct.unpack_from('>67I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for c in list(g.cases())[::61]:self.compare(c,s,images,entry);count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,both_HI_LO_pairs_and_five_R26_sites=True,carry_boundaries=True)

    def test_07_native32_shared_append_and_effective_controls(self):
        text,n=native.program(ROOT);p=self.out/'registration-native.c';p.write_text(text,encoding='utf-8')
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('registration-native'+opt);r=subprocess.run([*native_command(opt),'-mstackrealign',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),opt);self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',rows_per_path_profile=n,positive_calls=n*6,profiles=['O0','O2','O3'],SDK_native32=True,UBSan=True,node_size20=True,actual_shared_append_C=True,all_node_fields_padding_links_and_buffer_sentinels=True,direct_and_three_word_callback_ABI=True,effective_controls=list(g.controls()),guest_private_alias_claim=False)

    def test_08_literal_image_controls_and_stub(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();delta=match.strict_image(before,after,self.truth);at=match.elf_slot_offset(after,match.ENTRY,268)
        for off in(0,at,at+267,at+268,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.truth)
        stub=list(struct.unpack_from('>67I',before,at));m=g.Oracle(stub,g.fixture()).run();self.assertNotEqual(m.calls,g.reference(g.fixture())[1])
        self.receipt('image',changed_bytes=delta,exclusions=0,metadata_permutations=0,corruptions=5,stub_rejected=True)

if __name__=='__main__':unittest.main()
