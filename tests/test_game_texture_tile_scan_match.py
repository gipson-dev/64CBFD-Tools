"""Texture scanner contract, alias/access order, real callers and exact image."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_texture_tile_scan_candidates as candidate
from tools.experiments import game_texture_tile_scan_match as match
from tools.tests import game_texture_tile_scan_oracle as g
from tools.tests import game_texture_tile_scan_native as native
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT

class TextureTileScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>71I',cls.rom,match.ROM));cls.words=match.bound_blob(*match.function_blob(cls.prepared['qualified_owner']),dict(D_800B0E58=g.GLOBAL));cls.raw=match.bound_blob(*match.function_blob(cls.prepared['qualified_compact']),dict(D_800B0E58=g.GLOBAL))
        assert cls.retail==cls.words and cls.raw!=cls.words
    def receipt(self,name,**value):(self.out/('match-'+name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    def compare(self,c=g.Case(),images=None,entry=match.ENTRY,global_address=g.GLOBAL):
        initial,p=g.fixture(c,global_address);expected,result=g.reference(initial,c,p,global_address);models=[]
        for words in(self.retail,self.words,self.raw)if images is None else images:
            m=g.Oracle(words,initial,c,pointer=p,entry=entry).run();models.append(m)
            self.assertEqual((g.public(m.memory,c),m.r[2]),(g.public(expected,c),result),c)
        self.assertEqual(g.state(models[0]),g.state(models[1]))
        if len(models)>2:self.assertEqual((models[0].memory,models[0].trace),(models[2].memory,models[2].trace))
        return models
    def test_01_complete_source_derived_guards_and_owner(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors']),(71,8,28,68,68))
        raw,bindings=match.function_blob(self.prepared['qualified_compact']);normalized,moved=match.derive(raw,bindings)
        self.assertEqual((normalized,moved),match.function_blob(self.prepared['qualified_owner']))
        for i in range(284):
            bad=bytearray(raw);bad[i]^=1
            with self.assertRaises(ValueError):match.derive(bytes(bad),bindings)
        for at in bindings:
            bad=dict(bindings);bad[at]=[(bindings[at][0][0],'foreign')]
            with self.assertRaises(ValueError):match.derive(raw,bad)
        base=(self.out/'match-frozen'/match.GUARDS).read_bytes();proposed=(self.out/'proposed-guards.csv').read_bytes();self.assertEqual(match.guard_manifest(base,raw,bindings),proposed);self.assertTrue(proposed.startswith(base))
        rows=list(match.csv.DictReader(match.io.StringIO(proposed.decode())));new=[r for r in rows if r['function']==match.FUNCTION];self.assertEqual(len(new),28)
        self.assertTrue(all(r['omit']=='false'and not r['insert_after']and r['expected_relocations']==r['replacement_relocations']=='-'for r in new))
        item=next(r for r in rows if r['function']==match.FUNCTION);item['expected']='0x%08X'%(int(item['expected'],0)^1)
        stream=match.io.StringIO();w=match.csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows);p=self.out/'match-bad-guard.csv';p.write_text(stream.getvalue())
        with self.assertRaises(ValueError):match.assemble_owner(ROOT,self.out,self.prepared['qualified_compact'],'match-bad-guard-owner',p)
        self.receipt('guards-owner',derived_guards=28,byte_corruptions=284,binding_corruptions=2,expected_word_guard_rejected=True,neighbors=68,all_raw_and_padded_pools_and_metadata_fixed=True,no_frame_branch_access_or_binding_changes=True,insertions=0,omissions=0)
    def test_02_raw_C_and_literal_normalized_guest_contract(self):
        count=0;seen=set()
        for c in g.cases():
            for m in self.compare(c):seen.update(m.visits)
            count+=1
        self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+284,4)))
        self.receipt('guest-contract',cases_per_body=count,bodies=3,all_71_words_reached=True,all_prefix_opcode_bytes=True,full_word_sparse_guest_indices=True,negative_and_extreme_occurrences=True,six_output_aliases=True,all_end_pair_conditions=True,raw_C_public_memory_result_and_access_trace_equal=True,normalized_full_literal_state=True)
    def test_03_wildcard_final_pair_and_access_prefixes(self):
        c=g.Case(asset=0);initial,p=g.fixture(c)
        for i in range(4):del initial[g.GLOBAL+i]
        for words in(self.retail,self.words,self.raw):
            with self.assertRaisesRegex(AssertionError,'unmapped read'):g.Oracle(words,initial,c,pointer=p).run()
        c=g.Case(prefix=0xDF);initial,p=g.fixture(c)
        for i in range(4):del initial[g.GLOBAL+4+i]
        self.assertEqual(g.Oracle(self.words,initial,c,pointer=p).run().r[2],0xFFFFFFFF)
        c=g.Case(mask=1,pairs=1,ending=0);initial,p=g.fixture(c);full=g.Oracle(self.retail,initial,c,pointer=p).run()
        last=next(a for kind,a,n,value in reversed(full.trace)if kind=='R'and g.LIST<=a<g.LIST+2048)
        self.assertEqual(last,g.LIST+8*(4+c.gap));del initial[last]
        for words in(self.retail,self.words,self.raw):
            with self.assertRaisesRegex(AssertionError,'unmapped read'):g.Oracle(words,initial,c,pointer=p).run()
        wrong=list(self.words);wrong[64]=0;g.Oracle(wrong,initial,c,pointer=p).run()
        cuts=0
        for c in(g.Case(prefix=0xDF),g.Case(asset=0),g.Case(occurrence=1,alias=1),g.Case(alias=3),g.Case(alias=5)):
            initial,p=g.fixture(c);full=g.Oracle(self.retail,initial,c,pointer=p).run()
            for cut in range(full.all_accesses):
                pair=[]
                for words in(self.retail,self.words):
                    m=g.Oracle(words,initial,c,pointer=p);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(g.state(pair[0]),g.state(pair[1]));cuts+=1
        self.receipt('faults',fired_access_prefixes=cuts,wildcard_still_reads_resource_table=True,end_marker_skips_table=True,second_pair_byte_read_even_when_first_fails=True,omitted_delay_load_control_effective=True,normalized_full_literal_state=True,portable_C_fault_semantics_not_claimed=True)
    def test_04_both_original_call_windows_and_return_ABI(self):
        words=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(match.ENTRY>>2&0x3FFFFFF)
        self.assertEqual([4*i for i,w in enumerate(words)if w==jal],[0x1C2FC4,0x1C3308]);self.assertFalse(any(w in(match.ENTRY,0x08000000|(match.ENTRY>>2&0x3FFFFFF))for w in words))
        count=contracts=0;seen=set()
        for which,asset,occurrence,mask,phase in itertools.product((0,1),(0,1,7761),(-1,0,1,4),(0,5,15),(0,8)):
            c=g.Case(asset=asset,occurrence=occurrence,mask=mask,phase=phase);pair=[]
            for body in(self.retail,self.words):
                m=g.caller_machine(self.rom,body,c,which)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual(m.completed_contracts,1);a=m.target_contracts[0][0];self.assertEqual(a,(g.LIST,asset,g.u32(occurrence),g.STACK+phase+0x50));seen.update(m.visits);pair.append(m)
            self.assertEqual(g.state(pair[0]),g.state(pair[1]));count+=1;contracts+=pair[0].completed_contracts
        for start in(0x15195B08,0x15195E4C):self.assertTrue(set(range(start,start+36,4))<=seen)
        self.receipt('callers',cases_per_body=count,independent_return_contracts_per_body=contracts,original_call_windows=2,words_per_window=9,all_window_words_reached=True,four_word_arguments=True,caller_stack_output_plus_0x50=True,all_saved_integer_registers_GP_SP_FP_RA_preserved=True,full_parent_bodies_remain_unqualified=True)
    def test_05_independent_GNU_rebases(self):
        links=count=0
        for entry,global_address in((match.ENTRY,g.GLOBAL),(0x17007FFC,0x80117FFC),(0x1A028000,0x80128000)):
            images=[];symbols=dict(D_800B0E58=global_address)
            for j,original in enumerate((True,False)):
                p=self.out/('match-rebase-%X-%d'%(entry,j))
                if original:
                    rows=['.set noreorder','.text','.globl '+match.FUNCTION,match.FUNCTION+':']
                    for i,w in enumerate(self.retail):
                        if 4*i in match.BINDINGS:
                            typ,sym=match.BINDINGS[4*i][0];rows.append('.reloc ., '+typ+', '+sym);w&=0xFFFF0000
                        rows.append('.word 0x%08X'%w)
                    asm='\n'.join(rows)+'\n'
                else:
                    t,fs,rs=match.parse_object(self.prepared['qualified_owner']);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,symbols);self.assertFalse(unknown)
                p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                blob=sections(p.with_suffix('.elf'))['.text'][1];self.assertEqual(blob[284:],bytes(len(blob)-284));images.append(list(struct.unpack_from('>71I',blob)));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],match.bound_blob(*match.function_blob(self.prepared['qualified_owner']),symbols))
            for asset,occurrence,alias in itertools.product((0,1,7761),(-1,0,1,4),(0,1,3)):self.compare(g.Case(asset=asset,occurrence=occurrence,alias=alias),images=images,entry=entry,global_address=global_address);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,both_bindings=True,signed_low16_carry=True,standalone_zero_tail=True)
    def test_06_native32_source_and_effective_controls(self):
        text,controls,count=native.program();p=self.out/'match-native.c';p.write_text(text)
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native'+opt+'.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),opt);self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',cases_per_profile=count,positive_executions=3*count,total_scanner_calls=27*count,controls=controls,checked_mask=255,SDK_native32=True,UBSan=True,valid_finite_display_lists_and_resource_indices=True,host_endian_byte_and_word_alias_reference=True,guest_sparse_indices_and_fault_order_not_portable_C_claims=True)
    def test_07_strict_full_image_and_stub_controls(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+284];delta=match.strict_image(before,after,truth);self.assertEqual(delta,215);at=match.elf_slot_offset(before,match.ENTRY,284)
        for off in(0,at,at+283,at+284,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        initial,p=g.fixture();stub=list(struct.unpack_from('>71I',before,at));m=g.Oracle(stub,initial,pointer=p).run();self.assertEqual(m.r[2],0);self.assertNotEqual(g.reference(initial,pointer=p)[1],0)
        self.receipt('strict-image',changed_bytes=delta,exclusions=0,metadata_permutations=0,target_only=True,symbol_size_12_to_284=True,corruptions_rejected=5,stub_rejected=True)
    def test_08_all_path_symbolic_register_and_memory_closure(self):
        proof=match.role_closure(*match.function_blob(self.prepared['qualified_compact']))
        self.receipt('role-closure',**proof)

if __name__=='__main__':unittest.main()
