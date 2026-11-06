"""Asset walker: commutative guard, exact caller ABI and live byte/table effects."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_asset_block_walker_candidates as candidate
from tools.experiments import game_asset_block_walker_match as match
from tools.tests import game_asset_block_walker_oracle as g
from tools.tests import game_asset_block_walker_native as native
from tools.tests import test_game_view_list_setup as view_setup
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary,TrackedCode
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
def state(m):return complete(m),m.current_pc,m.delay_of,m.root_accesses
def saved(m,ra=None):return {r:(ra if r==31 and ra is not None else m.before[r]) for r in (16,17,18,19,20,31)}
class WindowStop(Exception):pass
class WindowCode(TrackedCode):
    def __getitem__(self,pc):
        if pc==0x15007900:raise WindowStop
        return super().__getitem__(pc)
class StartupOracle(g.Oracle):
    def record_call(self,t):
        if t==0x15008A60:self.calls.append((t,()));self.events.append(('CALL',t,()));return
        super().record_call(t)
    def hook(self,t):
        if t==0x15008A60:self.r[2]=0x12345678;return
        super().hook(t)

class AssetBlockWalkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.truth=cls.rom[match.ROM:match.ROM+280]
        cls.retail=list(struct.unpack('>70I',cls.truth));ctx=type('OriginalAssetWalker',(),dict(root=ROOT,out=cls.out))
        cls.original=view_setup.ViewListSetupTests.original.__func__(ctx,'walker-original',(ROOT/match.ASM).read_text(encoding='utf-8'),match.FUNCTION)
        cls.blobs=[match.function_blob(o) for o in (cls.original,cls.prepared['qualified_compact'],cls.prepared['qualified_owner'])]
        cls.images=[match.bound_blob(raw,b,g.SYMS) for raw,b in cls.blobs]
        assert cls.images[0]==cls.images[2]==cls.retail
        assert [i for i,(a,b) in enumerate(zip(cls.images[1],cls.retail)) if a!=b]==[0xC0//4]
    def receipt(self,n,**v):(self.out/('walker-'+n+'.json')).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    def compare(self,c=g.Case(),s=g.SYMS,images=None,entry=match.ENTRY):
        initial=g.fixture(c,s);models=[]
        for w in (self.images if images is None else images):
            m=g.Oracle(w,initial,c,entry,s);want,calls,_,_=g.reference(initial,c,s,saved=saved(m));m.run()
            self.assertEqual((m.memory,m.calls),(want,calls),c);self.assertEqual(m.r[2],c.poison&g.MASK)
            self.assertEqual(m.r[16:24],m.before[16:24]);self.assertEqual(m.r[28:32],m.before[28:32]);self.assertEqual(m.f[20:],m.before_f[20:]);models.append(m)
        self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(state(models[0]),state(models[2]));return models
    def test_01_owner_caller_guard_and_corruptions(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings'],q['neighbors']),(70,56,1,6,2));self.assertEqual(q['raw_word_differences'],1)
        self.assertEqual(q['caller_ABI']['raw_functions'],1);self.assertTrue(q['compact_GPR_mask_body_derived'])
        raw,b=self.blobs[1]
        for at in range(280):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),b,self.truth)
        for at in b:
            bad=dict(b);bad[at]=[('R_MIPS_26','foreign')]
            with self.assertRaises(ValueError):match.checked(raw,bad,self.truth)
        old=(self.out/'match-frozen'/match.GUARDS).read_bytes();new=match.proposed_guards(old)
        self.assertTrue(new.startswith(old));self.assertEqual(len(new.splitlines())-len(old.splitlines()),1)
        for at in (0,len(old)//2,len(old)-1):
            bad=bytearray(old);bad[at]^=1
            with self.assertRaises(ValueError):match.proposed_guards(bytes(bad))
        self.receipt('owner',words=70,raw_differences=1,frame=56,guards=1,bindings=6,raw_and_padded_neighbors=2,pure_addu_operand_exchange=True,caller_raw_and_padded_unchanged=True,guard_rows_added=1,raw_corruptions=280,binding_corruptions=6,guard_prefix_corruptions=3)
    def test_02_live_reference_argument_widths_and_byte_steps(self):
        count=0;seen=set()
        for c in g.cases():seen.update(self.compare(c)[0].visits);count+=1
        self.assertTrue(set(range(match.ENTRY,match.ENTRY+280,4))<=seen)
        self.receipt('guest',cases_per_body=count,bodies=3,all70_words=True,signed16_raw_word_selector=True,all256_values_in_four_size_bytes=True,live_bounds_after_allocation_and_copy=True,post_consumer_length_and_bound_reads=True,unsigned_wrap_and_signed_limit_edges=True,null_guest_allocation_has_no_added_gate=True,saved_GPR_FPR_SP_ABI=True)
    def test_03_output_table_home_aliases_and_fault_prefixes(self):
        count=0
        for phase,offset,selector in itertools.product((0,8),(0,4,8,12,16),(0,1,0xFFFF,0x8000)):
            c=g.Case(base=g.STACK+phase+offset,selector=selector,steps=(16,),size=16,copy_limit=0);self.compare(c);count+=1
            c=g.Case(selector=selector,steps=(16,),size=16,copy_limit=0);s=dict(g.SYMS,D_80082F80=(g.BUFFER+offset-8*g.narrow(selector))&g.MASK)
            images=[match.bound_blob(raw,b,s) for raw,b in self.blobs];self.compare(c,s,images);count+=1
            c=replace(c,copy_error=True,phase=phase);s=dict(g.SYMS,D_80082F80=(g.STACK+phase+offset-8*g.narrow(selector))&g.MASK)
            images=[match.bound_blob(raw,b,s) for raw,b in self.blobs];self.compare(c,s,images);count+=1
        cuts=0
        for c in (g.Case(),g.Case(steps=()),g.Case(copy_limit=16),g.Case(steps=(0x80000010,),size=16,stop_after=1),g.Case(base=g.STACK+8,steps=(16,),copy_limit=0)):
            initial=g.fixture(c);done=g.Oracle(self.retail,initial,c).run()
            for cut in range(done.root_accesses):
                models=[]
                for w in self.images:
                    m=g.Oracle(w,initial,c);m.root_fault=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(state(models[0]),state(models[2]));cuts+=1
        self.receipt('aliases',cases_per_body=count,output_overwrites_incoming_home=True,table_output_and_home_relocations=True,private_aliases_guest_only=True,fault_prefixes=cuts,literal_full_fault_states_all_three_bodies=True)
    def test_04_original_consumer_texture_expansion(self):
        words=list(struct.unpack_from('>273I',self.rom,0x42EE8));connected=dict(zip(range(g.CONSUME,g.CONSUME+1092,4),words));count=0;seen=set()
        for selector,width,height,run in itertools.product((0,1,0xFFFF),(0,1,2,5,8,9,16,32),(0,1,2),(1,4,7,16)):
            c=g.Case(selector=selector,steps=(128,128),consumer=True,width=width,height=height,run=run);initial=g.fixture(c);models=[]
            for w in self.images:
                m=g.Oracle(w,initial,c,connected=connected);want,calls,_,_=g.reference(initial,c,saved=saved(m));m.run()
                self.assertEqual((g.public(m.memory),m.calls),(g.public(want),calls),c);models.append(m);seen.update(m.visits)
            self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(state(models[0]),state(models[2]));count+=1
        reached=seen&set(range(g.CONSUME,g.CONSUME+1092,4))
        writes=[]
        for i,w in enumerate(words):
            op,fn=w>>26,w&63
            if op==0:
                if fn in (8,25):r=None
                elif fn in (0,3,18,33,35,37,38,42):r=w>>11&31
                else:raise AssertionError(('Unclassified original consumer operation',hex(w)))
            elif op in (9,10,12,15,35,36):r=w>>16&31
            elif op in (4,5,6,20,21,22,40,43):r=None
            else:raise AssertionError(('Unclassified original consumer opcode',hex(w)))
            if r==11:writes.append(i*4)
        self.assertEqual(writes,[0xB0,0xBC]);self.assertEqual((words[0xB0//4],words[0xB4//4],words[0xBC//4]),(0x26AB0007,0x3178FFF8,0x03005825))
        self.assertEqual((words[0x34C//4],words[0x35C//4]),(0x31630003,0x5060000E))
        self.assertTrue(all((((width+7)&0xFFF8)&3)==0 for width in range(256)))
        unseen=[pc-g.CONSUME for pc in range(g.CONSUME,g.CONSUME+1092,4) if pc not in reached]
        self.assertEqual(unseen,list(range(0x364,0x394,4)))
        self.receipt('consumer',cases_per_body=count,original_body_words=273,body_words_reached=len(reached),unreached_offsets=[hex(a) for a in unseen],twelve_unreachable_remainder_words_proven_by_rounded_stride=True,independent_RLE_reference=True,descriptor_fields_and_complete_pixel_backing=True,source_stride_and_odd_row_xor4=True,production_consumer_remains_unconverted=True,allocator_and_IO_and_free_bounded=True)
    def test_05_original_startup_window_ignores_void_return(self):
        window=list(struct.unpack_from('>4I',self.rom,0x34DA0));count=0;seen=set()
        for steps,tail,mutation,phase,poison in itertools.product(((),(16,),(16,16),(16,24,32)),(0,15),(0,1,4,16),(0,8),(0,0xFFFFFFFF)):
            c=g.Case(steps=steps,tail=tail,mutation=mutation,phase=phase,poison=poison);initial=g.fixture(c);models=[]
            for w in (self.retail,self.images[2]):
                m=StartupOracle(window,initial,c,entry=0x150078F0,connected=dict(zip(range(match.ENTRY,match.ENTRY+280,4),w)));m.r[4]=0xA5A5FFFF;m.code=WindowCode(dict(m.code),m)
                want,calls,_,_=g.reference(initial,c,saved=saved(m,0x150078F8))
                with self.assertRaises(WindowStop):m.run()
                self.assertEqual(g.public(m.memory),g.public(want));self.assertEqual(m.calls,[(match.ENTRY,(0,)),*calls,(0x15008A60,())]);self.assertEqual(m.r[2],0x12345678);models.append(m);seen.update(m.visits)
            self.assertEqual(state(models[0]),state(models[1]));count+=1
        self.assertTrue(set(range(0x150078F0,0x15007900,4))<=seen)
        self.receipt('caller',cases_per_body=count,original_window_words=4,all_window_words=True,containing_parent_words=124,complete_parent_claim=False,delay_zero_selector=True,two_free_return_poisons_ignored=True,following_call_overwrites_result=True)
    def test_06_independent_GNU_binding_rebases(self):
        links=count=0
        layouts=((match.ENTRY,g.SYMS),(0x18017FFC,dict(D_80082F80=0x89007FFC,func_10003C6C=0x18028000,func_10004514=0x18038000,func_15015A38=0x18048000,func_10004074=0x18058000)),(0x1A028000,dict(D_80082F80=0x89008000,func_10003C6C=0x1A038004,func_10004514=0x1A048008,func_15015A38=0x1A05800C,func_10004074=0x1A068010)))
        for k,(entry,s) in enumerate(layouts):
            images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                t,fs,rs=match.parse_object(obj);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('walker-rebase-%d-%d'%(k,j));p.with_suffix('.s').write_text(asm,encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,v) for n,v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
                images.append(list(struct.unpack_from('>70I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            normalized=images[1][:];normalized[0xC0//4]=0x020E7821;self.assertEqual(images[0],normalized);self.assertEqual(images[0],images[2])
            for c in list(g.cases())[::79]:self.compare(c,s,images,entry);count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,HI_LO_carry_boundaries=True,four_R26_sites=True,guard_remains_nonrelocated_pure_operand_exchange=True)
    def test_07_native32_exact_deltas_ABI_and_controls(self):
        text,n,names=native.program();p=self.out/'walker-native.c';p.write_text(text,encoding='utf-8')
        for opt in ('-O0','-O2','-O3'):
            exe=self.out/('walker-native'+opt);r=subprocess.run([*native_command(opt),'-mstackrealign',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),opt);self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        effective=[]
        for k,name in enumerate(names[1:],1):
            exe=self.out/('walker-native-control-'+name);r=subprocess.run([*native_command('-O2'),'-mstackrealign','-DVARIANT_INDEX=%d'%k,str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),name);r=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual((r.returncode,r.stdout,r.stderr),(1,'',''),name);effective.append(name)
        self.receipt('native',rows_per_path_profile=n,positive_calls=n*6,profiles=['O0','O2','O3'],SDK_native32=True,UBSan=True,direct_and_compatible_s16_callback_ABI=True,complete_buffer_and_sentinels_exact=True,exact_provider_call_traces=True,live_bounds_and_post_consumer_byte_sizes=True,effective_controls=effective,controls_exit1_without_faults=True,private_and_sparse_aliases_guest_only=True)
    def test_08_whole_image_corruptions_and_stub(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();delta=match.strict_image(before,after,self.truth);at=match.elf_slot_offset(after,match.ENTRY,280)
        for off in (0,at,at+279,at+280,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.truth)
        stub=list(struct.unpack_from('>70I',before,at));m=g.Oracle(stub,g.fixture()).run();_,calls,_,_=g.reference(g.fixture());self.assertNotEqual(m.calls,calls)
        self.receipt('image',changed_bytes=delta,exclusions=0,metadata_permutations=0,corruptions=5,stub_rejected=True,caller_owner_unchanged=True)
if __name__=='__main__':unittest.main()
