"""Direct damped records, no-unroll owner, callback ABI and literal whole ELF."""
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_damped_record_lifetime_candidates as candidate
from tools.experiments import game_damped_record_lifetime_match as match
from tools.tests import game_damped_record_lifetime_oracle as g
from tools.tests import game_damped_record_lifetime_native as native
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowBoundary,WindowCode
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
class DampedRecordLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>72I',cls.rom,match.ROM));cls.words=match.bound_blob(*match.function_blob(cls.prepared['qualified_owner']),g.symbols());cls.raw=match.bound_blob(*match.function_blob(cls.prepared['qualified_compact']),g.symbols());assert cls.words==cls.raw==cls.retail
    def receipt(self,name,**v):(self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    def compare(self,c=g.Case(),images=None,s=None,entry=match.ENTRY,initial=None):
        s=g.symbols()if s is None else s;initial=g.fixture(c,s)if initial is None else initial;expected,calls,obs=g.reference(initial,c,s);pair=[]
        for w in(self.retail,self.words)if images is None else images:
            m=g.Oracle(w,initial,c,s=s,entry=entry,connected=g.helper_code(self.rom,c)).run();pair.append(m);self.assertEqual((g.public(m.memory,c),m.calls,m.observations),(g.public(expected,c),calls,obs),c)
        for m in pair[1:]:self.assertEqual(g.state(pair[0]),g.state(m))
        return pair
    def test_01_direct_owner_profile_bindings_and_fail_closed_controls(self):
        q=self.prepared['report'];self.assertEqual((q['raw_words'],q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['bindings']),(72,72,24,0,31,31,4));self.assertEqual(q['raw_metadata_changes'],['T2 mask 0xA37FFBFE to 0xA37FFFFE']);self.assertEqual(q['padded_metadata_changes'],[]);self.assertEqual((q['profile_predecessor_functions_fixed'],q['default_profile_unrolled_words']),(32,110));raw,bindings=match.function_blob(self.prepared['qualified_compact']);self.assertEqual(match.derive(raw,bindings),match.function_blob(self.prepared['qualified_owner']))
        for i in range(288):
            b=bytearray(raw);b[i]^=1
            with self.assertRaises(ValueError):match.derive(bytes(b),bindings)
        for at in bindings:
            b=dict(bindings);b[at]=[(bindings[at][0][0],'foreign')]
            with self.assertRaises(ValueError):match.derive(raw,b)
        with self.assertRaises(ValueError):match.emit_padded_assembly(self.out/'match-unrolled-control.o',ROOT/match.ASM,filename=match.FILENAME,word_patches_path=ROOT/match.GUARDS)
        before,after,installed=candidate.make_states((ROOT/match.MAKE).read_text(encoding='utf-8'));self.assertEqual(before,(self.out/'match-frozen'/match.MAKE).read_text(encoding='utf-8'));self.assertEqual(after,(self.out/'proposed-Makefile').read_text(encoding='utf-8'))
        with self.assertRaises(ValueError):candidate.make_states(after.replace('-O2 -g3 -Wo,-loopunroll,0\n','-O1\n'))
        self.assertEqual((ROOT/match.GUARDS).read_bytes(),(self.out/'proposed-guards.csv').read_bytes());self.receipt('owner',raw_words=72,guards=0,bindings=4,neighbors=31,frame=24,baseline_profile_functions_fixed=32,default_unrolled_words_rejected=110,only_owner_no_unroll_flag_added=True,byte_corruptions_rejected=288,binding_corruptions_rejected=4)
    def test_02_signed_wrap_clamps_staged_float_and_delayed_expiry(self):
        count=0;seen=set()
        for c in g.cases():
            for m in self.compare(c):seen.update(m.visits)
            count+=1
        self.assertEqual([i for i in range(72)if match.ENTRY+4*i not in seen],[15]);self.receipt('guest',cases_per_body=count,bodies=2,raw_C_identical=True,all_reachable_words_visited=True,unreachable_duplicate_clock_load_word=15,signed16_actor_and_record_wrap=True,threshold_and_clamp_boundaries=True,float32_divide_multiply_divide_subtract_add_order=True,clock_reloaded_per_active_record=True,negative_age_frees_on_following_call=True,NaN_infinity_and_division_by_zero_are_model_checks_not_FCSR_acceptance=True)
    def test_03_clock_aliases_lazy_reads_and_fired_access_cuts(self):
        count=cuts=0;raw,bindings=match.function_blob(self.prepared['qualified_compact'])
        for address,age,ticks,phase in itertools.product((g.ACTOR+0xA8,g.STACK,g.RECORDS+0x8C,g.RECORDS+0x90,g.RECORDS+0x94,g.RECORDS+5*160+0x94,g.RECORDS+11*160+0x94),(-1,0,1),(0,1,20,0x80000000),(0,8)):
            c=g.Case(age=age,ticks=ticks,phase=phase);s=g.symbols();s['D_800BE9E4']=address+(phase if address==g.STACK else 0);w=match.bound_blob(raw,bindings,s);self.compare(c,images=(w,w),s=s);count+=1
        for c in(g.Case(),g.Case(age=0,lifetime=0,ticks=1),g.Case(age=32767,ticks=1),g.Case(pattern=2),g.Case(age=-1,mutation=7),g.Case(age=-1,connected=3)):
            initial=g.fixture(c);full=g.Oracle(self.retail,initial,c,connected=g.helper_code(self.rom,c)).run()
            for cut in range(full.all_accesses):
                pair=[]
                for w in(self.retail,self.words):
                    m=g.Oracle(w,initial,c,connected=g.helper_code(self.rom,c));m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(g.state(pair[0]),g.state(pair[1]));cuts+=1
        c=g.Case(age=-1,payload=0);initial=g.fixture(c)
        for p in range(g.CLOCK,g.CLOCK+4):initial.pop(p)
        for p in range(g.RECORDS-12,g.RECORDS+0x790):initial.pop(p)
        self.compare(c,initial=initial);self.receipt('faults',clock_alias_cases_per_body=count,fired_access_cuts=cuts,literal_state_PC_delay_and_private_bytes_equal=True,expiry_target_needs_no_clock_or_record_reads=True,live_clock_changes_from_record_stores=True,guest_stack_and_overlap_checks_not_portable_C_alias_claims=True)
    def test_04_original_allocator_and_actor_release_chain(self):
        count=0;before=(self.out/'match-frozen'/match.ELF).read_bytes()
        for entry,offset,n in((g.FREE,0x4074,119),(g.RELEASE,0x196BDC,28),(g.SCAN,0x196B8C,20),(g.ADAPTER,0x196CB4,8)):
            at=match.elf_slot_offset(before,entry,n*4);self.assertEqual(before[at:at+n*4],self.rom[offset:offset+n*4])
        for connected,payload,category,depth,callback,phase,seed in itertools.product((1,2,3),(0,g.RECORDS),(1,6),(0,2),(0,1),(0,8),(0,1)):
            self.compare(g.Case(age=-1,connected=connected,payload=payload,category=category,depth=depth,callback=callback,phase=phase,seed=seed));count+=1
        self.receipt('providers',cases_per_body=count,allocator_words=119,release_words=28,active_scan_words=20,adapter_words=8,retained_helpers_equal_installed_ELF=True,NULL_and_single_block_heap_free=True,head_tail_and_largest_block_updates=True,active_next_slots_repaired=True,default_and_optional_release_callback=True,osSetIntMask_and_final_unlink_are_bounded_providers=True,no_extra_helper_C_credit=True)
    def test_05_actual_registry_and_dispatch_window(self):
        words=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([i*4 for i,w in enumerate(words)if w==match.ENTRY],[0x2300A0]);self.assertNotIn(0x0C000000|(match.ENTRY>>2&0x3FFFFFF),words);self.assertNotIn(0x08000000|(match.ENTRY>>2&0x3FFFFFF),words);self.assertEqual(g.REGISTRY+6*52,0x8008B5E0);count=0;start,end=0x15167158,0x15167184;window=struct.unpack_from('>11I',self.rom,start-0x14FD2B50)
        for age,ticks,pattern,mutation,phase in itertools.product((-1,0,10),(0,1,20),(0,2),(0,3),(0,8)):
            c=g.Case(age=age,ticks=ticks,pattern=pattern,mutation=mutation,phase=phase,connected=2);initial=g.fixture(c);initial[g.DEPTH]=1;g.put(initial,g.REGISTRY+6*52,match.ENTRY);expected_initial=dict(initial);g.put(expected_initial,g.SLOTS+4,g.read(initial,g.ACTOR+8));expected,calls,obs=g.reference(expected_initial,c);pair=[]
            for w in(self.retail,self.words):
                code=g.helper_code(self.rom,c);code.update(zip(range(match.ENTRY,match.ENTRY+288,4),w));code[end]=0;m=g.Oracle(window,initial,c,entry=start,connected=code);m.r[16]=g.ACTOR;m.r[18]=g.REGISTRY+6*52;m.r[19]=g.DEPTH;m.r[20]=g.SLOTS;m.code=WindowCode(m.code,m);m.code.ends=(end,)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual(m.root_args,[(g.ACTOR,)]);self.assertEqual((g.public(m.memory,c),m.calls,m.observations),(g.public(expected,c),[(match.ENTRY,(g.ACTOR,))]+calls,obs));pair.append(m)
            self.assertEqual(g.state(pair[0]),g.state(pair[1]));count+=1
        self.receipt('callers',cases_per_body=count,registry='D_8008B4A8',category=6,record_stride=52,registered_callback_VA=0x8008B5E0,registered_callback_ROM=0x2300A0,window_words=11,next_queued_before_call_and_repaired_by_release=True,void_struct102_callback_ABI=True,whole_parent_stub_unchanged=True)
    def test_06_independent_GNU_links_all_four_bindings(self):
        links=count=0
        for k,entry in enumerate((match.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:s={n:entry+0x10000*(i+1)if n.startswith('func_')else 0x81007FFC+0x10000*(k-1)for i,n in enumerate(s)}
            images=[]
            for j,original in enumerate((True,False)):
                p=self.out/('match-rebase-%d-%d'%(k,j))
                if original:
                    rows=['.set noreorder','.text','.globl '+match.FUNCTION,match.FUNCTION+':']
                    for i,w in enumerate(self.retail):
                        if 4*i in match.BINDINGS:
                            typ,sym=match.BINDINGS[4*i][0];rows.append('.reloc ., '+typ+', '+sym);w&=0xFC000000 if typ=='R_MIPS_26'else 0xFFFF0000
                        rows.append('.word 0x%08X'%w)
                    asm='\n'.join(rows)+'\n'
                else:
                    t,fs,rs=match.parse_object(self.prepared['qualified_owner']);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);blob=sections(p.with_suffix('.elf'))['.text'][1];self.assertEqual(blob[288:],bytes(len(blob)-288));images.append(list(struct.unpack_from('>72I',blob)));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],match.bound_blob(*match.function_blob(self.prepared['qualified_compact']),s))
            for age,ticks,pattern in itertools.product((-1,0,32767),(0,1,20),(0,2)):self.compare(g.Case(age=age,ticks=ticks,pattern=pattern),images=images,s=s,entry=entry);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,all_four_bindings=True,two_JALs_and_clock_HI_LO=True,signed_low16_carries=True)
    def test_07_SDK_native32_rounding_callback_and_effective_controls(self):
        text,controls,count=native.program();p=self.out/'match-native.c';p.write_text(text,encoding='utf-8')
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native'+opt+'.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);(self.out/('match-native'+opt+'-compile.log')).write_text(r.stdout+r.stderr);self.assertEqual((r.returncode,bool(r.stdout),bool(r.stderr)),(0,False,False),(opt,(r.stdout+r.stderr)[-3500:]));self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',cases_per_profile=count,positive_executions=3*count,negative_controls=controls,checked_mask=(1<<len(controls))-1,SDK_native32_UBSan=True,canonical_struct115_void_callback=True,actor_and_160_byte_record_layout_asserted=True,whole_owner_and_both_buffer_fences=True,finite_active_floats_and_inactive_raw_NaNs=True,guest_incoming_home_redirect_excluded=True)
    def test_08_literal_full_image_and_former_stub_rejection(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+288];self.assertEqual(match.strict_image(before,after,truth),224);at=match.elf_slot_offset(before,match.ENTRY,288);locations=[0,at,at+287,at+288,len(after)-1,next(p+8 for p,n,f,loc in match.symbol_rows(before)if n==match.FUNCTION)]
        for off in locations:
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        c=g.Case();initial=g.fixture(c);m=g.Oracle(struct.unpack_from('>72I',before,at),initial,c).run();self.assertNotEqual(g.public(m.memory,c),g.public(g.reference(initial,c)[0],c));self.receipt('image',strict_changed_bytes=224,exclusions=0,metadata_permutations=0,only_target_body_and_symbol_size_change=True,all_addresses=6052,protected_Game_bytes=189088,protected_Game_owners=720,corruptions_rejected=len(locations),former_stub_rejected=True,guards_unchanged=True)
if __name__=='__main__':unittest.main()
