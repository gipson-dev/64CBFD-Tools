"""Direct raw C, queued reader ABI, original caller and complete image gates."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_channel_command_poller_candidates as candidate
from tools.experiments import game_channel_command_poller_match as match
from tools.experiments import game_channel_command_poller_header_audit as header_audit
from tools.tests import game_channel_command_poller_oracle as g
from tools.tests import game_channel_command_poller_native as native
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT


class ChannelCommandPollerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>72I',cls.rom,match.ROM));cls.words=match.bound_blob(*match.function_blob(cls.prepared['qualified_owner']),g.symbols())
        assert cls.words==cls.retail==match.bound_blob(*match.function_blob(cls.prepared['qualified_compact']),g.symbols())
    def receipt(self,name,**v):(self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c=g.Case(),images=None,s=None,entry=match.ENTRY):
        s=g.symbols()if s is None else s;initial=g.fixture(c,s);e=g.reference(initial,c,s);pair=[]
        for words in(self.retail,self.words)if images is None else images:
            m=g.Oracle(words,initial,c,s=s,entry=entry,connected=g.helper_code(self.rom,c)).run();pair.append(m)
            self.assertEqual((g.public(m.memory,c),m.submissions,m.n),(g.public(e['memory'],c),e['actions'],e['reads']),c)
            if not c.connected&1:self.assertEqual(m.calls,e['calls'])
            else:
                self.assertEqual([v for v in m.calls if v[0]in(s['func_100126E8'],s['func_15080430'],g.COUNT,g.APPLY)],e['calls'])
        self.assertEqual(g.state(pair[0]),g.state(pair[1]));return pair
    def test_01_direct_body_bindings_owner_and_reader_ABI(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors']),(72,312,0,3,3));self.assertTrue(q['Init_complete_padded_owner_fixed']);self.assertEqual(q['Init_raw_functions_fixed'],7)
        raw,bindings=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+288]
        for i in range(288):
            bad=bytearray(raw);bad[i]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),bindings,truth)
        for at in bindings:
            bad=dict(bindings);bad[at]=[(bindings[at][0][0],'foreign')]
            with self.assertRaises(ValueError):match.checked(raw,bad,truth)
        self.assertEqual((ROOT/match.GUARDS).read_bytes(),(self.out/'match-frozen'/match.GUARDS).read_bytes())
        self.receipt('owner-ABI',raw_words=72,guards=0,byte_corruptions=288,binding_corruptions=7,neighbors=3,Init_functions_fixed=7,Init_complete_object_identical=True,unchanged_Init_warning=1,raw_GPR_only_delta=['A300CF7E','A33FFF7E'])
    def test_02_packet_widths_statuses_mutability_and_empty(self):
        count=0;seen=set()
        for c in g.cases():
            for m in self.compare(c):seen.update(m.visits)
            count+=1
        missing=[i for i in range(72)if match.ENTRY+4*i not in seen]
        self.assertEqual(missing,[39,43,44,45])
        # Empty queue must not touch uninitialized buffer bytes.
        c=g.Case(messages=());initial=g.fixture(c)
        for i in range(256):del initial[g.buffer(g.STACK)+i]
        m=g.Oracle(self.words,initial,c).run();self.assertEqual(m.n,1);self.assertFalse(m.submissions)
        self.receipt('guest',cases_per_body=count,bodies=2,all_256_opcodes_channels_indices=True,nonzero_fullword_statuses=True,masked_28bit_duration=True,divisor=367,zero_fallback=20,live_escaped_buffer_and_index=True,empty_unmapped_buffer=True,unreachable_constant_divisor_guard_word_indices=missing,raw_C_literal_identity=True)
    def test_03_original_ring_reader_dispatcher_and_alias(self):
        count=0;seen=set()
        for connected,active,phase,cursor,length,command in itertools.product((1,2,3),(0,1,0xFFFFFFFF),(0,8),(0,2041),(8,256,260),(0,1,2,255)):
            # Opaque reader is bounded to its actual 256-byte output buffer.
            if not connected&1 and length>256:continue
            c=g.Case(messages=(g.packet(command=command,length=length,high=128),g.packet(value=0)),connected=connected,active=active,phase=phase,cursor=cursor,mode=7)
            for m in self.compare(c):seen.update(m.visits)
            count+=1
        for c in(g.Case(messages=(),connected=3),g.Case(messages=(b'',g.packet()),connected=3),g.Case(messages=(g.packet(),),connected=3,alias=True,cursor=0,mode=7)):
            self.compare(c);count+=1
        self.assertTrue(set(range(g.READER,g.READER+48,4))<=seen)
        self.receipt('connected',cases_per_body=count,original_Init_reader_words=12,ring_receive_words=58,transfer_words=42,skip_words=18,memcpy_words=11,dispatcher_words=51,empty_zero_length_wrap_oversize=True,signed_COUNT_results=True,forward_copy_guest_alias=True,opaque_COUNT_APPLY_hardware_not_claimed=True)
    def test_04_literal_access_prefixes_and_stub_control(self):
        cuts=0
        for c in(g.Case(),g.Case(mode=7),g.Case(messages=(g.packet(),),connected=3,alias=True,cursor=0),g.Case(messages=(g.packet(length=260),),connected=3,cursor=2041)):
            initial=g.fixture(c);code=g.helper_code(self.rom,c);full=g.Oracle(self.retail,initial,c,connected=code).run()
            for cut in range(full.all_accesses):
                pair=[]
                for w in(self.retail,self.words):
                    m=g.Oracle(w,initial,c,connected=code);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(g.state(pair[0]),g.state(pair[1]));cuts+=1
        before=(self.out/'match-frozen'/match.ELF).read_bytes();at=match.elf_slot_offset(before,match.ENTRY,288);m=g.Oracle(struct.unpack_from('>72I',before,at),g.fixture()).run();self.assertFalse(m.calls)
        self.receipt('faults',fired_access_cuts=cuts,literal_full_state_equal=True,stub_rejected=True,portable_C_fault_or_uninitialized_first_short_packet_not_claimed=True)
    def test_05_original_conditional_caller_window(self):
        allwords=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(match.ENTRY>>2&0x3FFFFFF)
        self.assertEqual([4*i for i,w in enumerate(allwords)if w==jal],[0x4B9B0]);self.assertFalse(any(w in(match.ENTRY,0x08000000|(match.ENTRY>>2&0x3FFFFFF))for w in allwords))
        count=0;start,end=0x1501E4EC,0x1501E510
        for gate,phase,mode in itertools.product((0,1,2,0xFFFFFFFF),(0,8),(0,7)):
            c=g.Case(phase=phase,mode=mode);initial=g.fixture(c);g.put(initial,g.STACK+phase+0x1C,0x12345678);g.put(initial,g.STACK+phase+0x24,0x87654321);pair=[]
            for w in(self.retail,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+288,4),w));code[end]=0;m=g.Oracle(struct.unpack_from('>9I',self.rom,start-0x15000000+0x2D4B0),initial,c,entry=start,connected=code);m.r[2]=gate;m.r[3]=0x12345678;m.r[6]=0x87654321;m.code=WindowCode(m.code,m);m.code.ends=(end,);saved=tuple(m.r[i]for i in(*range(16,24),28,29,30))
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual(tuple(m.r[i]for i in(*range(16,24),28,29,30)),saved);self.assertEqual((m.r[3],m.r[6]),(0x12345678,0x87654321));self.assertEqual(bool(m.submissions),gate==1)
                if gate==1:self.assertEqual(m.calls[0],(match.ENTRY,()));self.assertEqual(m.r[31],0x1501E508)
                pair.append(m)
            self.assertEqual(g.state(pair[0]),g.state(pair[1]));count+=1
        self.receipt('caller',cases_per_body=count,original_window_words=9,gate_exactly_one=True,no_arguments=True,result_unused_by_caller=True,saved_GPR_GP_SP_FP_fixed=True,complete_parent_not_claimed=True)
    def test_06_independent_GNU_links_and_rebases(self):
        links=count=0
        for k,entry in enumerate((match.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:s={n:(entry+0x10000*(j+1)if n.startswith('func_')else 0x81007FFC+0x10000*j)for j,n in enumerate(s)}
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
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                blob=sections(p.with_suffix('.elf'))['.text'][1];self.assertEqual(blob[288:],bytes(len(blob)-288));images.append(list(struct.unpack_from('>72I',blob)));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],match.bound_blob(*match.function_blob(self.prepared['qualified_owner']),s))
            for mode,phase in itertools.product(range(8),(0,8)):self.compare(g.Case(mode=mode,phase=phase),images=images,s=s,entry=entry);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,all_seven_bindings=True,signed_low16_carry=True,JAL_region=True,zero_standalone_tail=True)
    def test_07_SDK_native32_typed_reader_and_controls(self):
        text,controls,count=native.program();p=self.out/'match-native.c';p.write_text(text)
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native'+opt+'.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);(self.out/('match-native'+opt+'-compile.log')).write_text(r.stdout+r.stderr)
            self.assertEqual((r.returncode,bool(r.stdout),bool(r.stderr)),(0,False,False),(opt,(r.stdout+r.stderr)[-2000:]));self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',cases_per_profile=count,positive_executions=3*count,negative_controls=controls,checked_mask=255,SDK_native32_UBSan=True,actual_typed_Init_wrapper=True,fullword_return_preserved=True,initialized_C_domains_only=True)
    def test_08_header_consumers_strict_image_and_corruptions(self):
        q=header_audit.audit_phase(ROOT,self.out,production=self.prepared['report']['source_installed']);self.assertEqual((q['owners'],q['strict_full_image_changed_bytes'],q['strict_exclusions']),(201,220,0))
        for r in q['records']:self.assertEqual(match.sha((ROOT/r['shadow']).read_bytes()),r['after_sha256'])
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+288];self.assertEqual(match.strict_image(before,after,truth),220);self.assertEqual(match.sha(after),q['qualified_elf_sha256']);self.assertEqual((self.out/'header-linked/conker.us.elf').read_bytes(),after)
        at=match.elf_slot_offset(before,match.ENTRY,288)
        for off in(0,at,at+287,at+288,0x29D100,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        self.receipt('header-image',active_header_owners=201,strict_changed_bytes=220,strict_exclusions=0,all_addresses=6052,protected_Game_bytes=189088,protected_Game_owners=720,corruptions_rejected=6,CSV_and_Make_profile_fixed=True)

if __name__=='__main__':unittest.main()
