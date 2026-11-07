"""Closed branch-edge guards, big-endian aliases, indirect ABI and full image."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_linked_event_callback_candidates as candidate
from tools.experiments import game_linked_event_callback_match as match
from tools.tests import game_linked_event_callback_oracle as g
from tools.tests import game_linked_event_callback_native as native
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowBoundary,WindowCode
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
class LinkedEventCallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>72I',cls.rom,match.ROM));cls.words=match.bound_blob(*match.function_blob(cls.prepared['qualified_owner']),g.symbols());cls.raw=match.bound_blob(*match.function_blob(cls.prepared['qualified_compact']),g.symbols());assert cls.words==cls.retail
    def receipt(self,name,**v):(self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c=g.Case(),images=None,s=None,entry=match.ENTRY,connected=None):
        s=g.symbols()if s is None else s;initial=g.fixture(c,s);expected,calls,obs=g.reference(initial,c,s);pair=[]
        for w in(self.retail,self.words,self.raw)if images is None else images:
            m=g.Oracle(w,initial,c,s=s,entry=entry,connected=connected).run();pair.append(m)
            self.assertEqual((g.public(m.memory,c),m.calls,m.observations),(g.public(expected,c),calls,obs),c)
            self.assertEqual(tuple(m.r[i]for i in(*range(16,24),28,29,30)),tuple(m.before[i]for i in(*range(16,24),28,29,30)))
        for m in pair[1:]:self.assertEqual(g.semantic_state(pair[0],c),g.semantic_state(m,c))
        if len(pair)>1 and list(images or())[0:1]!=[self.raw] and len(pair[0].code)==len(pair[1].code):self.assertEqual(g.literal_state(pair[0]),g.literal_state(pair[1]))
        return pair
    def test_01_derived_branch_edge_owner_and_fail_closed_controls(self):
        q=self.prepared['report'];self.assertEqual((q['raw_words'],q['words'],q['frame'],q['guards'],q['inserted_words'],q['raw_neighbors'],q['padded_neighbors'],q['bindings']),(71,72,48,5,1,30,30,3));raw,bindings=match.function_blob(self.prepared['qualified_compact']);self.assertEqual(match.derive(raw,bindings),match.function_blob(self.prepared['qualified_owner']))
        for i in range(284):
            b=bytearray(raw);b[i]^=1
            with self.assertRaises(ValueError):match.derive(bytes(b),bindings)
        for at in bindings:
            b=dict(bindings);b[at]=[(bindings[at][0][0],'foreign')]
            with self.assertRaises(ValueError):match.derive(raw,b)
        rows=list(match.csv.DictReader(match.io.StringIO((self.out/'proposed-guards.csv').read_text())));new=[r for r in rows if r['function']==match.FUNCTION]
        self.assertEqual([int(r['offset'],0)for r in new],[0x58,0x7C,0x88,0x98,0x9C]);self.assertEqual([int(r['offset'],0)for r in new if r['insert_after']],[0x9C]);self.assertTrue(all(r['omit']=='false'and r['expected_relocations']==r['replacement_relocations']=='-'for r in new));self.assertTrue((self.out/'proposed-guards.csv').read_bytes().startswith((self.out/'match-frozen'/match.GUARDS).read_bytes()))
        for changed in new:
            bad=[dict(r)for r in rows];at=rows.index(changed);bad[at]['expected']='0x%08X'%(int(changed['expected'],0)^1);stream=match.io.StringIO();writer=match.csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(bad);path=self.out/'stale-guard.csv';path.write_text(stream.getvalue())
            with self.assertRaisesRegex(ValueError,'stale word patch'):match.emit_padded_assembly(self.prepared['qualified_compact'],ROOT/match.ASM,filename=match.FILENAME,word_patches_path=path)
        self.receipt('owner',raw_words=71,normalized_words=72,frame=48,guards=5,insertions=1,byte_corruptions_rejected=284,binding_corruptions_rejected=3,actual_padder_stale_expected_words_rejected=5,neighbors=30,existing_Warning712=2,new_diagnostics=0,existing_store_then_one_flags_load_preserved=True,BNEL_operands_commute=True,all_local_branches_and_bindings_relocated=True)
    def test_02_all_byte_events_flags_keys_tags_and_mutable_callbacks(self):
        count=0;seen=set()
        for c in g.cases():
            for m in self.compare(c):seen.update(m.visits)
            count+=1
        # Original's unreachable duplicate load and common-path redundant store
        # are retained; do not manufacture execution to claim source coverage.
        missing=[i for i in range(72)if match.ENTRY+4*i not in seen];self.assertEqual(missing,[33])
        self.receipt('guest',cases_per_body=count,bodies=3,all_256_event_and_index_bytes=True,upper_argument_bits_truncated=True,all_three_key_matches=True,byte4_big_endian_clear_tag=True,live_flags_table_and_payload_after_helper=True,opaque_callback_clobbers=True,unreachable_word=33,raw_semantic_state_equal=True)
    def test_03_aliases_access_order_and_fault_prefixes(self):
        count=cuts=0;pc_differences=0
        for alias,event,match,tag,callback,mutation in itertools.product(range(6),(0,27,45,1),range(3),(0x87,0xA5),(0,1),(0,3,12,16)):
            self.compare(g.Case(alias=alias,event=event,match=match,tag=tag,callback=callback,mutation=mutation));count+=1
        for c in(g.Case(),g.Case(match=1),g.Case(event=0,match=2,tag=0x87),g.Case(event=27,mutation=15),g.Case(alias=2,match=1)):
            initial=g.fixture(c);full=g.Oracle(self.retail,initial,c).run()
            for cut in range(full.all_accesses):
                pair=[]
                for w in(self.retail,self.words,self.raw):
                    m=g.Oracle(w,initial,c);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(g.literal_state(pair[0]),g.literal_state(pair[1]))
                self.assertEqual((pair[0].memory,pair[0].trace,pair[0].calls,pair[0].observations),(pair[2].memory,pair[2].trace,pair[2].calls,pair[2].observations))
                pc_differences+=int((pair[0].current_pc,pair[0].delay_of)!=(pair[2].current_pc,pair[2].delay_of));cuts+=1
        self.assertGreater(pc_differences,0)
        self.receipt('faults',alias_cases_per_body=count,fired_access_cuts=cuts,raw_PC_or_delay_differences=pc_differences,owner_pair_flags_key_tags_and_table_aliases=True,store_then_one_flags_load_order_exact=True,normalized_literal_fault_state_equal=True,raw_memory_access_prefix_equal=True,raw_literal_PC_parity_and_portable_C_faults_not_claimed=True)
    def test_04_original_float_helper_and_real_inner_table(self):
        actual=list(struct.unpack_from('>10I',self.rom,0x22E4B8));self.assertEqual(actual,[0,0x151C1814,0,0,0,0x15133DE8,0x1513B0B8,0,0x150F4CFC,0]);count=0
        for kind,index,flags,alias,phase in itertools.product((0,34,0x8022),(0,1,5,6,8,9),(0,256),range(4),(0,8)):
            c=g.Case(event=27,kind=kind,index=index,flags=flags,alias=alias,phase=phase);self.compare(c,connected=g.helper_code(self.rom));count+=1
        self.receipt('helper',cases_per_body=count,bodies=3,original_helper_words=11,actual_inner_table_entries=10,three_float_stores_and_two_live_constants=True,outer_dispatch_table_is_separate=True,inner_callback_bodies_not_recovered_here=True)
    def test_05_class_slots_and_three_original_dispatch_windows(self):
        r=self.rom;words=struct.unpack('>%dI'%(len(r)//4),r);self.assertEqual([4*i for i,w in enumerate(words)if w==match.ENTRY],[0x230498,0x230E24]);self.assertNotIn(0x0C000000|(match.ENTRY>>2&0x3FFFFFF),words);self.assertNotIn(0x08000000|(match.ENTRY>>2&0x3FFFFFF),words);count=0
        for cls,offset in((25,0x230498),(72,0x230E24)):self.assertEqual(0x8008B4A8+52*cls+28,0x8008B4D0+offset-0x22FF90)
        # Start once the descriptor pointer/owner/payload are selected. Preserve
        # the exact original register moves, byte narrowing and JALR delay slot.
        for site,cls,event,matched in itertools.product((0x1516916C,0x15169360,0x15169520),(25,72),(0,27,45,0x11B,0x12D),range(3)):
            c=g.Case(event=event,match=matched);initial=g.fixture(c);o,p=g.addresses(c);descriptor=0x8008B4A8+52*cls;g.put(initial,descriptor+28,candidate.ENTRY)
            start=site-12 if site!=0x15169360 else site-28;end=site+8;window=struct.unpack_from('>%dI'%((end-start)//4),r,start-0x15000000+0x2D4B0);expected,calls,obs=g.reference(initial,c);pair=[]
            for w in(self.retail,self.words,self.raw):
                code=dict(zip(range(candidate.ENTRY,candidate.ENTRY+4*len(w),4),w));code[end]=0;m=g.Oracle(window,initial,c,entry=start,connected=code);m.r[16]=o;m.r[18]=p;m.r[19]=p if site==0x15169520 else event;m.r[20]=event;m.r[22]=descriptor;m.r[23]=0x8008B4A8;m.r[25]=cls;m.r[30]=52;m.r[4]=o;m.r[5]=p;m.r[6]=event&255;m.code=WindowCode(m.code,m);m.code.ends=(end,)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual(m.root_args,[(o,p,event&255)]);self.assertEqual((g.public(m.memory,c),m.calls,m.observations),(g.public(expected,c),[(candidate.ENTRY,(o,p,event&255))]+calls,obs));pair.append(m)
            count+=1
        self.receipt('callers',cases_per_body=count,bodies=3,class_entries=[25,72],descriptor_base='0x8008B4A8',stride=52,event_callback_offset=28,three_original_JALR_sites=True,owner_payload_and_unsigned_byte_ABI=True,void_return_not_consumed=True,full_list_dispatch_parents_not_claimed=True)
    def test_06_independent_GNU_links_all_bindings_and_signed_low_carry(self):
        links=count=0;raw,bindings=match.function_blob(self.prepared['qualified_compact']);normalized,moved=match.derive(raw,bindings)
        for k,entry in enumerate((match.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:s=dict(func_151B9660=entry+0x10000,D_800899F8=0x81007FFC+0x10000*(k-1))
            images=[]
            for j,original in enumerate((True,False)):
                p=self.out/('match-rebase-%d-%d'%(k,j))
                if original:
                    rows=['.set noreorder','.text','.globl '+match.FUNCTION,match.FUNCTION+':']
                    for i,w in enumerate(self.retail):
                        if 4*i in moved:
                            typ,sym=moved[4*i][0];rows.append('.reloc ., '+typ+', '+sym);w&=0xFC000000 if typ=='R_MIPS_26'else 0xFFFF0000
                        rows.append('.word 0x%08X'%w)
                    asm='\n'.join(rows)+'\n'
                else:
                    t,fs,rs=match.parse_object(self.prepared['qualified_owner']);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);blob=sections(p.with_suffix('.elf'))['.text'][1];self.assertEqual(blob[288:],bytes(len(blob)-288));images.append(list(struct.unpack_from('>72I',blob)));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],match.bound_blob(normalized,moved,s))
            for event,matched,mutation in itertools.product((0,27,45,0x11B),range(3),(0,15)):self.compare(g.Case(event=event,match=matched,mutation=mutation),images=images,s=s,entry=entry);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,all_three_bindings=True,signed_low16_carry=True,JAL_region=True,inserted_word_relocates_both_table_bindings=True)
    def test_07_SDK_native32_and_effective_controls(self):
        text,controls,count=native.program();p=self.out/'match-native.c';p.write_text(text)
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native'+opt+'.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);(self.out/('match-native'+opt+'-compile.log')).write_text(r.stdout+r.stderr);self.assertEqual((r.returncode,bool(r.stdout),bool(r.stderr)),(0,False,False),(opt,(r.stdout+r.stderr)[-3500:]));self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',cases_per_profile=count,positive_executions=3*count,negative_controls=controls,checked_mask=511,SDK_native32_UBSan=True,numeric_word_and_byte_results_and_call_observations=True,second_key_equal_bytes_avoid_host_endian_ambiguity=True,big_endian_alias_and_fault_proof_is_guest_only=True)
    def test_08_strict_image_unchanged_pools_and_stub_rejection(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+288];self.assertEqual(match.strict_image(before,after,truth),211);at=match.elf_slot_offset(before,match.ENTRY,288)
        for off in(0,at,at+287,at+288,0x2D1072,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        c=g.Case();initial=g.fixture(c);m=g.Oracle(struct.unpack_from('>72I',before,at),initial,c).run();self.assertFalse(m.calls);self.assertEqual(g.public(initial,c),g.public(m.memory,c));self.assertNotEqual(g.public(m.memory,c),g.public(g.reference(initial,c)[0],c));self.receipt('image',strict_changed_bytes=211,exclusions=0,all_addresses=6052,protected_Game_bytes=189088,protected_Game_owners=720,corruptions_rejected=6,stub_rejected=True,two_absolute_symbol_serialization_swap_predicted=True,all_named_definitions_preserved=True)
if __name__=='__main__':unittest.main()
