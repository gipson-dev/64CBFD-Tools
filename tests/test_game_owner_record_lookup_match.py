"""Ordered owner/tag lookup, original switch/constructor and literal ELF gates."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_owner_record_lookup_candidates as candidate
from tools.experiments import game_owner_record_lookup_match as match
from tools.tests import game_owner_record_lookup_oracle as g
from tools.tests import game_owner_record_lookup_native as native
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowBoundary,WindowCode
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
class OwnerRecordLookupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>89I',cls.rom,0x1B8F40));cls.words=match.bound_blob(*match.function_blob(cls.prepared['qualified_owners'][0],0),g.symbols());cls.raw=match.bound_blob(*match.function_blob(cls.prepared['qualified_compacts'][0],0),g.symbols());assert cls.words==cls.retail
    def receipt(self,name,**v):(self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    def compare(self,c=g.Case(),images=None,s=None,entry=g.ENTRY,initial=None):
        s=g.symbols()if s is None else s;initial=g.fixture(c,s,entry)if initial is None else initial;e=g.reference(initial,c,s);pair=[]
        for w in(self.retail,self.words,self.raw)if images is None else images:
            m=g.Oracle(w,initial,c,s=s,entry=entry,connected=g.helper_code(self.rom,c,s)).run();self.assertEqual((g.public(m.memory,c),m.calls,m.packets,m.r[2]),(g.public(e['memory'],c),e['calls'],e['packets'],e['value']),c);pair.append(m)
        for m in pair[1:]:self.assertEqual(g.state(pair[0]),g.state(m))
        return pair
    def test_01_owner_frame_guards_and_complete_switch_pool(self):
        q=self.prepared['report']['targets'][0];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings'],q['raw_neighbors'],q['padded_neighbors']),(89,72,2,13,8,8));self.assertEqual((q['diagnostics']['before'],q['diagnostics']['after']),(0,0));raw,b=match.function_blob(self.prepared['qualified_compacts'][0],0);normalized,nb=match.derive(raw,b,0);self.assertEqual((normalized,nb),match.function_blob(self.prepared['qualified_owners'][0],0));self.assertEqual(struct.unpack_from('>I',raw)[0],0x27BDFFB8)
        for at in range(356):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.derive(bytes(bad),b,0)
        for at in b:
            bad=dict(b);bad[at]=[(b[at][0][0],'foreign')]
            with self.assertRaises(ValueError):match.derive(raw,bad,0)
        old=(self.out/'match-frozen'/match.GUARDS).read_bytes();new=(self.out/'proposed-guards.csv').read_bytes();self.assertTrue(new.startswith(old));self.assertEqual(new,match.guard_manifest(old));mb,ma,mi=candidate.make_states((ROOT/match.MAKE).read_text(encoding='utf-8'));self.assertEqual(mb,(self.out/'match-frozen'/match.MAKE).read_text(encoding='utf-8'));self.assertEqual(ma,(self.out/'proposed-Makefile').read_text(encoding='utf-8'))
        self.assertEqual(struct.unpack_from('>9I',self.rom,0x24BED0),tuple(g.ENTRY+i for i in g.JUMPS));self.assertEqual(struct.unpack_from('>3I',self.rom,0x24BEF4),g.Case().constants)
        for field,offset in(('.rodata',0),('.rodata',35)):
            pools=match.alloc_pools(self.prepared['qualified_compacts'][0]);v=list(pools[field]);data=bytearray(v[4]);data[offset]^=1;v[4]=bytes(data);bad=dict(pools);bad[field]=tuple(v)
            from unittest.mock import patch
            real=match.alloc_pools
            with patch.object(match,'alloc_pools',side_effect=lambda p:bad if p==self.prepared['qualified_compacts'][0]else real(p)):
                with self.assertRaises(ValueError):match.pools(self.out/'match-predecessor-0.o',self.prepared['qualified_compacts'][0])
        self.receipt('owner',words=89,frame=72,guards=2,bindings=13,raw_and_padded_neighbors=8,byte_corruptions_rejected=356,binding_corruptions_rejected=13,complete_48_byte_raw_pool_checked=True,nine_original_table_entries_and_three_adjacent_constants=True,Make_only_binds_preserved_table=True,two_independent_ADDIU_words_and_LO16_bindings_exchange=True)
    def test_02_complete_guest_reference(self):
        seen=set();count=0
        for c in g.cases():pair=self.compare(c);seen.update(pair[0].visits);count+=1
        missing=[i for i in range(89)if g.ENTRY+4*i not in seen];self.assertEqual(missing,[26,41,42]);self.receipt('guest',cases_per_body=count,bodies=3,visited_words=86,unreachable_words=missing,all_256_unsigned_kinds=True,both_rows_and_all_six_hit_positions=True,pointer_and_tag_first_match_order=True,owner_node_aliases=True,full_raw_and_padded_private_state_equal=True,retained_packet_byte_seeded_only_in_guest=True,no_portable_uninitialized_byte_claim=True)
    def test_03_lazy_reads_and_fired_access_cuts(self):
        null=g.Case(null=1);self.compare(null,initial={p:v for p,v in g.fixture(null).items()if g.STACK-512<=p<g.STACK+256})
        c=g.Case(pointers=1,kind=255);initial=g.fixture(c)
        for p in range(g.OWNER,g.OWNER+80):initial.pop(p,None)
        initial.pop(g.NODES+40);self.compare(c,initial=initial)
        c=g.Case(tags=1,kind=255);initial=g.fixture(c);initial.pop(g.OWNER+4)
        for p in g.CONSTANTS:
            for i in range(4):initial.pop(p+i)
        self.compare(c,initial=initial)
        c=g.Case(kind=255,heads=(-1,-1));initial=g.fixture(c);initial.pop(g.OWNER+59)
        for p in g.CONSTANTS:
            for i in range(4):initial.pop(p+i)
        self.compare(c,initial=initial)
        cuts=delays=0
        for c in(g.Case(),g.Case(tags=32),g.Case(kind=7,connected=7,alias=3,mutation=3)):
            initial=g.fixture(c);full=g.Oracle(self.retail,initial,c,connected=g.helper_code(self.rom,c)).run()
            for cut in range(full.all_accesses):
                pair=[]
                for w in(self.retail,self.words,self.raw):
                    m=g.Oracle(w,initial,c,connected=g.helper_code(self.rom,c));m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                for m in pair[1:]:self.assertEqual(g.state(pair[0]),g.state(m))
                cuts+=1;delays+=pair[0].delay_of is not None
        self.receipt('faults',fired_access_cuts=cuts,delay_slot_cuts=delays,lazy_NULL_pointer_hit_tag_hit_and_unsupported_kind=True,all_three_complete_states_equal=True,guest_homes_are_not_portable_C_aliases=True)
    def test_04_original_constructor_copy_and_integer_RNG(self):
        before=self.prepared['predecessor_elf'].read_bytes();descriptions=((g.CREATE,0x1B9180,36),(g.COPY,0x22EC0,11),(g.RANDOM,0xDAED0,18));seen={e:set()for e,p,n in descriptions};count=0
        for entry,offset,n in descriptions:
            at=match.elf_slot_offset(before,entry,4*n);self.assertEqual(before[at:at+4*n],self.rom[offset:offset+4*n])
        for connected,kind,outcome,alias,seed in itertools.product((1,3,5,7),(0,7),(0,1),range(4),g.SEEDS):
            c=g.Case(connected=connected,kind=kind,outcome=outcome,alias=alias,seed=seed,priority=0xABCDEF81,context=0x80000000,mutation=3);pair=self.compare(c)
            for e,p,n in descriptions:seen[e].update(v for v in pair[0].visits if e<=v<e+4*n)
            count+=1
        coverage={hex(e):len(v)for e,v in seen.items()};self.assertEqual(coverage,{hex(e):n for e,p,n in descriptions});self.receipt('providers',cases_per_body=count,coverage=coverage,retained_helper_words=65,NULL_and_successful_allocation=True,allocation_size=68,copied_bytes=28,two_original_64bit_seed_draws_masked_to31=True,allocator_home_mutations_and_redirected_copy=True,no_additional_helper_C_credit=True)
    def test_05_actual_single_caller_and_skip(self):
        allwords=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([i*4 for i,w in enumerate(allwords)if w==0x0C000000|(g.ENTRY>>2&0x3FFFFFF)],[0xC5A0C]);self.assertNotIn(g.ENTRY,allwords);self.assertNotIn(0x08000000|(g.ENTRY>>2&0x3FFFFFF),allwords);window=struct.unpack_from('>8I',self.rom,0xC59FC);count=0
        for enabled,kind,outcome,connected in itertools.product((0,1),(0,7,255),(0,1),(0,7)):
            c=g.Case(kind=kind,outcome=outcome,connected=connected);initial=g.fixture(c);e=g.reference(initial,c)if enabled else dict(memory=initial,calls=[],packets=[]);pair=[]
            for w in(self.retail,self.words):
                code=g.helper_code(self.rom,c);code.update(zip(range(g.ENTRY,g.ENTRY+356,4),w));m=g.Oracle(window,initial,c,entry=0x1509854C,connected=code,arguments_override=());m.r[17]=g.OWNER;m.r[25]=enabled;m.code=WindowCode(m.code,m);m.code.ends=(0x1509856C,0x15099C00)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual((g.public(m.memory,c),m.calls,m.packets),(g.public(e['memory'],c),([(g.ENTRY,g.arguments(c))]if enabled else[])+e['calls'],e['packets']))
                if enabled:self.assertEqual(m.r[2],1)
                pair.append(m)
            self.assertEqual(g.state(pair[0]),g.state(pair[1]));count+=1
        self.receipt('callers',window_words=8,cases_per_body=count,JAL_ROM='0xC5A0C',owner_priority255_context0=True,enabled_delay_returns_one=True,zero_guard_skips_call=True,complete_parent_not_claimed=True)
    def test_06_independent_GNU_links_and_switch_entries(self):
        links=count=0;t=candidate.TARGETS[0]
        for k,entry in enumerate((g.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:s.update(D_800DCE50=0x81237FF0,D_800DD190=0x81238330,jtbl_800A7410=0x81278004,D_800A7434=0x812A7FFC,D_800A7438=0x812A8000,D_800A743C=0x812A8004,func_1518BCD0=entry+0x10000)
            s['.rodata']=s['jtbl_800A7410'];images=[]
            for j,original in enumerate((True,False)):
                p=self.out/('match-rebase-%d-%d'%(k,j));rows=['.set noreorder','.text','.globl '+t['function'],t['function']+':']
                if original:
                    for at,w in enumerate(self.retail):
                        if 4*at in t['bindings']:
                            typ,sym=match.derive(*match.function_blob(self.prepared['qualified_compacts'][0],0),0)[1][4*at][0];rows.append('.reloc ., '+typ+', '+sym);w&=0xFC000000 if typ=='R_MIPS_26'else 0xFFFF0000
                        rows.append('.word 0x%08X'%w)
                    asm='\n'.join(rows)+'\n'
                else:
                    text,fs,rs=match.parse_object(self.prepared['qualified_owners'][0]);asm,unknown=emit_function(text,fs[t['function']],rs,t['function'],s);self.assertFalse(unknown)
                asm+='\n.section .lookup_table,"a"\n'+''.join('.word '+t['function']+'+'+str(off)+'\n'for off in g.JUMPS)
                p.with_suffix('.s').write_text(asm,encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .lookup_table 0x%X : { *(.lookup_table) } }\n'%(entry,s['jtbl_800A7410']),encoding='utf-8');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',t['function'],*['--defsym=%s=0x%X'%v for v in s.items()if v[0]!='.rodata'],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);sec=sections(p.with_suffix('.elf'));blob=sec['.text'][1];self.assertEqual(blob[356:],bytes(len(blob)-356));self.assertEqual(struct.unpack('>9I',sec['.lookup_table'][1]),tuple(entry+off for off in g.JUMPS));images.append(list(struct.unpack_from('>89I',blob)));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[1],match.bound_blob(*match.derive(*match.function_blob(self.prepared['qualified_compacts'][0],0),0),s))
            for c in(g.Case(),g.Case(kind=7),g.Case(kind=255),g.Case(tags=32)):self.compare(c,images=images,s=s,entry=entry);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,all_13_bindings=True,signed_low16_carries=True,nine_linked_table_entries_per_image=True,table_end_is_rebased_pointer_sentinel=True)
    def test_07_SDK_native32_and_effective_controls(self):
        text,controls,count=native.program();p=self.out/'match-native.c';p.write_text(text,encoding='utf-8')
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native'+opt+'.elf');r=subprocess.run([*native_command(opt),'-Wno-switch-outside-range','-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);(self.out/('match-native'+opt+'-compile.log')).write_text(r.stdout+r.stderr,encoding='utf-8');self.assertEqual((r.returncode,bool(r.stdout),bool(r.stderr)),(0,False,False),(r.stdout+r.stderr)[-4000:]);self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',cases_per_profile=count,profiles=3,negative_controls=controls,all_controls_effective=True,SDK_native32_UBSan=True,all_27_defined_request_bytes_and_all_public_fences=True,retained_byte_initialized_only_after_defined_field_checks=True,NaN_payloads_copied_by_bits=True)
    def test_08_literal_image_metadata_and_former_stub(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();self.assertEqual(match.strict_image(before,after,self.rom),324);at=match.elf_slot_offset(before,g.ENTRY,356);loc=[0,at,at+355,at+356,len(after)-1,next(p+8 for p,n,f,s in match.symbol_rows(before)if n=='func_1518BA90')]
        for p in loc:
            b=bytearray(after);b[p]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(b),self.rom)
        c=g.Case();initial=g.fixture(c);stub=g.Oracle(struct.unpack_from('>89I',before,at),initial,c).run();e=g.reference(initial,c);self.assertNotEqual((g.public(stub.memory,c),stub.r[2]),(g.public(e['memory'],c),e['value']));self.receipt('image',strict_changed_bytes=324,exclusions=0,explicit_metadata_permutations=match.METADATA_GROUPS,only_target_body_and_size_and_named_metadata_changes=True,all_addresses=6052,protected_Game_bytes=189088,protected_Game_owners=720,corruptions_rejected=6,former_stub_rejected=True)
if __name__=='__main__':unittest.main()
