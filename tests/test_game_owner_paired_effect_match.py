"""Two-channel updater: semantic roles, connected helpers and literal image."""
import itertools,json,struct,subprocess,unittest
from unittest.mock import patch
from tools.experiments import game_owner_paired_effect_candidates as candidate
from tools.experiments import game_owner_paired_effect_match as match
from tools.tests import game_owner_paired_effect_oracle as g
from tools.tests import game_owner_paired_effect_native as native
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowBoundary,WindowCode
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
class OwnerPairedEffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>214I',cls.rom,0x1B9210));cls.words=match.bound_blob(*match.function_blob(cls.prepared['qualified_owners'][0]),g.symbols());cls.raw=match.bound_blob(*match.function_blob(cls.prepared['qualified_compacts'][0]),g.symbols());assert cls.words==cls.retail
        before=cls.prepared['predecessor_elf'].read_bytes();g.LOOKUP=struct.unpack_from('>65I',before,match.elf_slot_offset(before,g.TABLE,260));assert struct.unpack_from('>I',before,match.elf_slot_offset(before,g.UNIT,4))[0]==0x37800080
    def receipt(self,name,**v):(self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    def compare(self,c=g.Case(),images=None,s=None,entry=g.ENTRY,initial=None):
        s=g.symbols()if s is None else s;initial=g.fixture(c,s)if initial is None else initial;e=g.reference(initial,c,s);pair=[]
        for w in(self.retail,self.words,self.raw)if images is None else images:
            m=g.Oracle(w,initial,c,s=s,entry=entry,connected=g.helper_code(self.rom,c,s)).run();self.assertEqual((g.public(m.memory,c),m.calls,m.packets,m.ni,m.nf,m.nc),(g.public(e['memory'],c),e['calls'],e['packets'],e['integers'],e['floats'],e['factories']),c);pair.append(m)
        self.assertEqual(g.state(pair[0]),g.state(pair[1]))
        for m in pair[1:]:self.assertEqual(pair[0].memory,m.memory);self.assertEqual(pair[0].r[16:24]+pair[0].r[28:32],m.r[16:24]+m.r[28:32]);self.assertEqual(pair[0].f[20:],m.f[20:])
        return pair
    def test_01_complete_owner_schedule_and_fail_closed_controls(self):
        q=self.prepared['report']['targets'][0];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings'],q['raw_neighbors'],q['padded_neighbors']),(214,288,58,13,8,8));self.assertEqual((q['diagnostics']['before'],q['diagnostics']['after']),(0,0));raw,b=match.function_blob(self.prepared['qualified_compacts'][0]);updated,nb=match.derive(raw,b);self.assertEqual((updated,nb),match.function_blob(self.prepared['qualified_owners'][0]));proof=match.audit_schedule(raw,updated,b,nb)
        for at in range(856):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.derive(bytes(bad),b)
        for at in b:
            bad=dict(b);bad[at]=[(b[at][0][0],'foreign')]
            with self.assertRaises(ValueError):match.derive(raw,bad)
        words=list(struct.unpack('>214I',updated));active=next(i for i in range(120,169)if words[i]==0x24070005)
        for i,new in((active,0x24070004),(120,words[120]^4),(194,words[194]^1),(0,0x27BDFED8)):
            v=words[:];v[i]=new;bad=struct.pack('>214I',*v);t=dict(candidate.TARGETS[0]);a=struct.unpack('>214I',raw);t['patches']={4*k:(x,y)for k,(x,y)in enumerate(zip(a,v))if x!=y}
            with patch.object(candidate,'TARGETS',[t]):
                with self.assertRaises(ValueError):match.audit_schedule(raw,bad,b,nb)
        old=(self.out/'match-frozen'/match.GUARDS).read_bytes();new=(self.out/'proposed-guards.csv').read_bytes();self.assertTrue(new.startswith(old));self.assertEqual(new,match.guard_manifest(old));self.receipt('owner',words=214,frame=288,guards=58,bindings=13,raw_and_padded_neighbors=8,raw_byte_corruptions_rejected=856,binding_corruptions_rejected=13,independent_role_controls_rejected=4,role_proof=proof,whole_raw_pools_fixed_except_explicit_GPR_FPR_masks=True,whole_padded_pools_fixed=True,Makefile_unchanged=True)
    def test_02_complete_guest_reference_and_covered_domain(self):
        seen=set();count=0
        for c in g.cases():pair=self.compare(c);seen.update(pair[0].visits);count+=1
        missing=[i for i in range(214)if g.ENTRY+4*i not in seen];self.assertEqual(missing,[i for i,w in enumerate(self.retail)if w==0x0007000D]);self.assertEqual(len(missing),4)
        self.receipt('guest',cases_per_body=count,bodies=3,reachable_words=210,unexecuted_divide_zero_traps=missing,zero_modulus_outside_defined_C_domain=True,both_channels_and_all_unsigned_angle_bytes=True,all_five_owner_gates=True,timer_wrap_and_signed16_unsigned_modulo=True,captured_kind_and_threshold_and_live_tick=True,live_post_factory_owner_and_copied_next_pointer=True,backlink_aliases_into_owner_and_second_timer=True,all_private_bytes_and_callee_saved_registers_equal_on_return=True,raw_mid_instruction_fault_state_not_equated=True)
    def test_03_original_RNG_angle_factory_and_copy(self):
        before=self.prepared['predecessor_elf'].read_bytes();desc=((g.INTEGER,0xDAED0,18),(g.FLOAT,0xDAF18,25),(g.ANGLE,0x16F888,27),(g.CREATE,0x175250,70),(g.COPY,0x22EC0,11));seen={e:set()for e,p,n in desc};count=0
        for e,p,n in desc:
            at=match.elf_slot_offset(before,e,4*n);self.assertEqual(before[at:at+4*n],self.rom[p:p+4*n])
        for angle in range(256):
            c=g.Case(connected=31,limits=(32767,32767),randoms=(angle,0xFFFFFFFF,angle,0xFFFFFFFE,angle+64,23,angle+1,21),mutation=8,seed=g.SEEDS[angle%len(g.SEEDS)],outcome=angle%4);pair=self.compare(c)
            # Connected RNG chooses the actual angles from its shared seed.
            for e,p,n in desc:seen[e].update(v for v in pair[0].visits if e<=v<e+4*n)
            count+=1
        # Cover every lookup branch independently of seeded RNG distributions.
        for angle in range(256):
            c=g.Case(connected=4,limits=(32767,32767),randoms=(angle,0,0,0,angle+64,0,0,0));pair=self.compare(c);seen[g.ANGLE].update(v for v in pair[0].visits if g.ANGLE<=v<g.ANGLE+108);count+=1
        coverage={hex(e):len(v)for e,v in seen.items()};self.assertEqual(coverage,{hex(e):n for e,p,n in desc});self.receipt('providers',cases_per_body=count,retained_helper_words=151,coverage=coverage,actual_65_word_lookup_sha256=match.sha(struct.pack('>65I',*g.LOOKUP)),integer_and_float_draws_share_64bit_seed=True,all15_high_level_and11_allocator_arguments=True,NULL_and_successful_factory=True,descriptor_and_render_copies_and_backlink=True,allocator_is_bounded=True,no_additional_helper_C_credit=True)
    def test_04_fired_access_cuts_and_minimal_gate_mappings(self):
        c=g.Case(gate=1);initial=g.fixture(c)
        for p in range(g.OWNER,g.OWNER+512):initial.pop(p)
        self.compare(c,initial=initial)
        cuts=delays=0
        for c in(g.Case(gate=4),g.Case(mutation=15,alias=2),g.Case(connected=31,mutation=8,outcome=3)):
            initial=g.fixture(c);full=g.Oracle(self.retail,initial,c,connected=g.helper_code(self.rom,c)).run()
            for cut in range(full.all_accesses):
                pair=[]
                for w in(self.retail,self.words):
                    m=g.Oracle(w,initial,c,connected=g.helper_code(self.rom,c));m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(g.state(pair[0]),g.state(pair[1]));cuts+=1;delays+=pair[0].delay_of is not None
        self.receipt('faults',fired_access_cuts=cuts,delay_slot_cuts=delays,complete_normalized_state_trace_PC_and_private_bytes_equal=True,all_owned_RNG64_accesses_tracked=True,lazy_NULL_owner=True,raw_instruction_fault_identity_not_claimed=True,private_homes_not_portable_alias_claims=True)
    def test_05_actual_type31_dispatch_and_empty_chain(self):
        allwords=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([i*4 for i,w in enumerate(allwords)if w==g.ENTRY],[0x2305B4]);self.assertNotIn(0x0C000000|(g.ENTRY>>2&0x3FFFFFF),allwords);self.assertNotIn(0x08000000|(g.ENTRY>>2&0x3FFFFFF),allwords);self.assertEqual(0x8008B4A8+31*52,0x8008BAF4)
        window=struct.unpack_from('>10I',self.rom,0x194600);count=0
        for enabled,connected,outcome,gate in itertools.product((0,1),(0,31),(0,3),(0,4)):
            c=g.Case(connected=connected,outcome=outcome,gate=gate);initial=g.fixture(c);initial[0x800DD190]=2;g.put(initial,0x8008BAF4,g.ENTRY);g.put(initial,0x800DD1A0,0xDEADBEEF);expected=dict(initial)
            if enabled:g.put(expected,0x800DD1A0,g.read(expected,g.RECORD+8));e=g.reference(expected,c)
            else:e=dict(memory=expected,calls=[],packets=[])
            pair=[]
            for w in(self.retail,self.words):
                code=g.helper_code(self.rom,c);code.update(zip(range(g.ENTRY,g.ENTRY+856,4),w));code[0x15167178]=0;code[0x15167194]=0;m=g.Oracle(window,initial,c,entry=0x15167150,connected=code,arguments_override=());m.r[16]=g.RECORD if enabled else 0;m.r[18]=0x8008BAF4;m.r[19]=0x800DD190;m.r[20]=0x800DD198;m.code=WindowCode(m.code,m);m.code.ends=(0x15167178,0x15167194)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual((g.public(m.memory,c),m.calls,m.packets),(g.public(e['memory'],c),([(g.ENTRY,(g.RECORD,))]if enabled else[])+e['calls'],e['packets']));pair.append(m)
            self.assertEqual(g.state(pair[0]),g.state(pair[1]));count+=1
        self.receipt('callers',window_words=10,cases_per_body=count,registry='D_8008B4A8[31] at 0x8008BAF4',stride=52,one_record_pointer_void_callback=True,next_saved_in_JALR_delay=True,empty_chain_skip=True,complete_parent_not_claimed=True)
    def test_06_independent_GNU_links_and_low16_carries(self):
        links=count=0;t=candidate.TARGETS[0];refs=match.derive(*match.function_blob(self.prepared['qualified_compacts'][0]))[1]
        for k,entry in enumerate((g.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:s.update(D_800BE9E4=0x81237FFC,D_800A7440=0x81248000,func_150ADA20=entry+0x10000,func_150ADA68=entry+0x20000,func_151423D8=entry+0x30000,func_15147DA0=entry+0x40000)
            images=[]
            for j,original in enumerate((True,False)):
                p=self.out/('match-rebase-%d-%d'%(k,j));rows=['.set noreorder','.text','.globl '+t['function'],t['function']+':']
                if original:
                    for i,w in enumerate(self.retail):
                        if 4*i in refs:typ,sym=refs[4*i][0];rows.append('.reloc ., '+typ+', '+sym);w&=0xFC000000 if typ=='R_MIPS_26'else 0xFFFF0000
                        rows.append('.word 0x%08X'%w)
                    asm='\n'.join(rows)+'\n'
                else:text,fs,rs=match.parse_object(self.prepared['qualified_owners'][0]);asm,unknown=emit_function(text,fs[t['function']],rs,t['function'],s);self.assertFalse(unknown)
                p.with_suffix('.s').write_text(asm,encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',t['function'],*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);blob=sections(p.with_suffix('.elf'))['.text'][1];self.assertEqual(blob[856:],bytes(len(blob)-856));images.append(list(struct.unpack_from('>214I',blob)));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[1],match.bound_blob(*match.derive(*match.function_blob(self.prepared['qualified_compacts'][0])),s))
            for c in(g.Case(),g.Case(gate=1),g.Case(timers=(100,-1),outcome=0),g.Case(mutation=15)):self.compare(c,images=images,s=s,entry=entry);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,all13_bindings_and9_JAL_sites=True,signed_low16_carries=True,original_and_padded_agree=True)
    def test_07_SDK_native32_and_effective_controls(self):
        text,controls,count=native.program();p=self.out/'match-native.c';p.write_text(text,encoding='utf-8')
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native'+opt+'.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);(self.out/('match-native'+opt+'-compile.log')).write_text(r.stdout+r.stderr,encoding='utf-8');self.assertEqual((r.returncode,bool(r.stdout),bool(r.stderr)),(0,False,False),(r.stdout+r.stderr)[-4000:]);self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',cases_per_profile=count,profiles=3,negative_controls=controls,all_controls_effective=True,SDK_native32_UBSan=True,record68_request28_descriptor32_render32_ABI=True,all256_angle_and_wrapped_count_bytes=True,defined_packet_fields_and_all15_arguments=True,all_heap_fences_and_both_backlinks=True,callee_checks_defined_fields_before_initializing_only_holes=True,finite_FP_intermediates_no_FCSR_claim=True)
    def test_08_literal_whole_image_and_former_stub(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();self.assertEqual(match.strict_image(before,after,self.rom),661);at=match.elf_slot_offset(before,g.ENTRY,856);loc=[0,at,at+855,at+856,len(after)-1,next(p+8 for p,n,f,s in match.symbol_rows(before)if n=='func_1518BD60')]
        for p in loc:
            b=bytearray(after);b[p]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(b),self.rom)
        c=g.Case();initial=g.fixture(c);stub=g.Oracle(struct.unpack_from('>214I',before,at),initial,c).run();e=g.reference(initial,c);self.assertNotEqual((g.public(stub.memory,c),stub.calls),(g.public(e['memory'],c),e['calls']));self.receipt('image',strict_changed_bytes=661,exclusions=0,explicit_metadata_permutation=match.METADATA_GROUPS,only_target_body_size_and_named_metadata_changed=True,all_addresses=6052,protected_Game_bytes=189088,protected_Game_owners=720,corruptions_rejected=6,former_stub_rejected=True)
if __name__=='__main__':unittest.main()
