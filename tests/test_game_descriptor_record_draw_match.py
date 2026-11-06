"""Derived register/delay-load reorganization, source semantics and exact image."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_descriptor_record_draw_candidates as candidate
from tools.experiments import game_descriptor_record_draw_match as match
from tools.tests import game_descriptor_record_draw_oracle as g
from tools.tests import game_descriptor_record_draw_native as native
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.check_game_data_layout import load_section
ROOT=candidate.ROOT
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.current_pc,m.delay_of,m.all_accesses,m.visits,m.observations,m.target_calls)
class DescriptorRecordDrawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>71I',cls.rom,match.ROM));cls.words=g.bound(cls.prepared['qualified_owner']);cls.raw=g.bound(cls.prepared['qualified_compact'])
        assert cls.retail==cls.words and cls.raw!=cls.words
    def receipt(self,name,**v):(self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c=g.Case(),images=None,s=None,entry=match.ENTRY,include_raw=False):
        initial=g.fixture(c,s);memory,calls,result,obs=g.reference(initial,c,s=s);pair=[]
        for body in(self.retail,self.words)if images is None else images:
            m=g.Oracle(body,initial,c,s=s,entry=entry).run();pair.append(m)
            self.assertEqual((g.public(m.memory,c),m.calls,m.r[2],m.observations),(g.public(memory,c),calls,result,obs),c)
        self.assertEqual(state(pair[0]),state(pair[1]))
        if include_raw:
            m=g.Oracle(self.raw,initial,c).run()
            self.assertEqual((g.public(m.memory,c),m.calls,m.r[2],m.observations),(g.public(memory,c),calls,result,obs),c)
        return pair
    def test_01_derived_guards_owner_metadata_and_corruptions(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors']),(71,104,30,14,14))
        raw,bindings=match.function_blob(self.prepared['qualified_compact']);normalized,moved=match.derive(raw,bindings)
        self.assertEqual((normalized,moved),match.function_blob(self.prepared['qualified_owner']))
        for i in range(284):
            bad=bytearray(raw);bad[i]^=1
            with self.assertRaises(ValueError):match.derive(bytes(bad),bindings)
        for at in bindings:
            bad=dict(bindings);bad[at]=[(bindings[at][0][0],'foreign')]
            with self.assertRaises(ValueError):match.derive(raw,bad)
        base=(self.out/'match-frozen'/match.GUARDS).read_bytes();proposed=(self.out/'proposed-guards.csv').read_bytes();self.assertEqual(match.guard_manifest(base,raw,bindings),proposed);self.assertTrue(proposed.startswith(base))
        rows=list(match.csv.DictReader(match.io.StringIO(proposed.decode())));new=[r for r in rows if r['function']==match.FUNCTION];self.assertEqual(len(new),30)
        self.assertTrue(all(r['omit']=='false'and not r['insert_after']for r in new));self.assertEqual(q['raw_pool_audit']['added_registers'],['S5','S6','S7']);self.assertTrue(q['padded_pool_audit']['all_register_metadata_fixed'])
        # The expected-word and expected-relocation production gates are real.
        badrows=[dict(r)for r in rows];item=next(r for r in badrows if r['function']==match.FUNCTION);item['expected']='0x%08X'%(int(item['expected'],0)^1)
        stream=match.io.StringIO();w=match.csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(badrows);p=self.out/'match-bad-expected-guard.csv';p.write_text(stream.getvalue())
        with self.assertRaises(ValueError):match.assemble_owner(ROOT,self.out,self.prepared['qualified_compact'],'match-bad-expected-owner',p)
        self.receipt('guards-owner',derived_rows=30,raw_byte_corruptions=284,binding_corruptions=3,expected_word_guard_rejected=True,neighbors=14,raw_GPR_delta_only=True,padded_pools_and_all_metadata_fixed=True,insertions=0,omissions=0,frame_guards=0)
    def test_02_raw_C_public_contract_and_literal_normalized_state(self):
        seen=set();count=calls=0
        for c in g.cases():
            for m in self.compare(c,include_raw=True):seen.update(m.visits)
            count+=1;calls+=len(g.reference(g.fixture(c),c)[1])
        dead={match.ENTRY+4*22,match.ENTRY+4*38};self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+284,4))-dead)
        self.receipt('guest-contract',cases_per_body=count,bodies=3,helper_calls_per_body=calls,all_count_bytes=True,all_byte_axes=True,all_64_mutation_modes=True,reachable_words=69,structurally_checked_dead_words=2,raw_C_public_contract=True,normalized_full_literal_state=True,live_actor_and_matrix_pointers=True,original_opacity_restored_to_final_pointer=True,helper_opaque=True)
    def test_03_conditional_load_safety_private_aliases_and_faults(self):
        c=g.Case(count=0);initial=g.fixture(c)
        for p in list(initial):
            if g.DRAW-0x90<=p<g.DRAW+0x70 and p!=g.DRAW+2:del initial[p]
        del initial[g.GLOBAL]
        pair=[g.Oracle(w,initial,c).run()for w in(self.retail,self.words)];self.assertEqual(state(pair[0]),state(pair[1]))
        bad=list(self.words);bad[18]&=~(0x10<<26)
        with self.assertRaisesRegex(AssertionError,'unmapped read'):g.Oracle(bad,initial,c).run()
        count=cuts=0
        for n,mode,phase,off in itertools.product((0,1,2,127),(0,15,31),(0,8),(-100,-92,-36,-28,8,12)):
            c=g.Case(count=n,mode=mode,phase=phase);initial=g.fixture(c);g.put(initial,g.DRAW+16,g.STACK+phase+off-0x8A)
            pair=[g.Oracle(w,initial,c).run()for w in(self.retail,self.words)];self.assertEqual(state(pair[0]),state(pair[1]));count+=1
        for c in(g.Case(count=0),g.Case(count=1,mode=15,phase=8),g.Case(count=2,mode=31)):
            initial=g.fixture(c);full=g.Oracle(self.retail,initial,c).run()
            for cut in range(full.all_accesses):
                pair=[]
                for w in(self.retail,self.words):
                    m=g.Oracle(w,initial,c);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(state(pair[0]),state(pair[1]));cuts+=1
        self.receipt('aliases-faults',private_alpha_aliases_per_body=count,fired_access_prefixes=cuts,conditional_hoist_positive_and_unsafe_negative=True,normalized_full_literal_state=True,portable_private_aliases_not_claimed=True)
    def test_04_original_indirect_caller_and_real_table(self):
        addr,data=load_section(self.prepared['qualified_elf'],'.game_data');self.assertEqual(data[g.TABLE-addr:g.TABLE-addr+16],self.rom[0x232050:0x232060])
        self.assertEqual(struct.unpack('>4I',self.rom[0x232050:0x232060]),(g.OTHER,match.ENTRY,0,0))
        words=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(words)if w==match.ENTRY],[0x232054]);self.assertFalse(any(w in(0x0C000000|(match.ENTRY>>2&0x3FFFFFF),0x08000000|(match.ENTRY>>2&0x3FFFFFF))for w in words))
        parent=list(struct.unpack_from('>82I',self.rom,0x1B61B0));jal=next(i for i,w in enumerate(parent)if w==0x0320F809);prefix=sum(w==0x26310008 for w in parent[:jal])*8
        count=contracts=0;seen=set()
        for n,view,mode,phase,group,nodes,other in itertools.product((0,3),(0,0x7FFF,0x8000,0xABCDFFFF),(0,15),(0,8),(0,1),(0,1,2),(False,True)):
            c=g.Case(count=n,view=view,mode=mode,phase=phase);pair=[]
            for w in(self.retail,self.words):
                m=g.caller_machine(self.rom,w,c,nodes,other,group).run();pair.append(m);seen.update(m.visits)
                self.assertIsNone(m.pending_contract);self.assertEqual(m.completed_contracts,len(m.caller_arguments))
                for a in m.caller_arguments:self.assertIn(a[1],(g.DRAW,g.DRAW2));self.assertEqual(a[2],g.u32(g.sign16(view)))
                if m.caller_arguments:self.assertEqual(m.caller_arguments[0][0],g.CURSOR+prefix+(8 if other else 0))
            self.assertEqual(state(pair[0]),state(pair[1]));count+=1;contracts+=pair[0].completed_contracts
        self.assertTrue(set(range(g.PARENT,g.PARENT+328,4))<=seen)
        self.receipt('caller',cases_per_body=count,complete_parent_words=82,all_parent_words_visited=True,independent_target_contract_returns_per_body=contracts,live_cursor_and_signed_view_ABI=True,original_callback_table_fixed=True,other_callback_opaque=True,current_parent_and_helper_still_unmatched=True)
    def test_05_independent_GNU_rebases(self):
        links=count=0
        for k,entry in enumerate((match.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:s=dict(D_800BE9C0=0x80107FFC+0x10000*k,func_151137D4=entry+0x10000)
            images=[]
            for j,original in enumerate((True,False)):
                p=self.out/('match-rebase-%d-%d'%(k,j))
                if original:
                    rows=['.set noreorder','.text','.globl '+match.FUNCTION,match.FUNCTION+':']
                    for i,w in enumerate(self.retail):
                        if 4*i in match.OUTPUT_BINDINGS:
                            typ,sym=match.OUTPUT_BINDINGS[4*i][0];rows.append('.reloc ., '+typ+', '+sym);w&=0xFC000000 if typ=='R_MIPS_26'else 0xFFFF0000
                        rows.append('.word 0x%08X'%w)
                    asm='\n'.join(rows)+'\n'
                else:
                    t,fs,rs=match.parse_object(self.prepared['qualified_owner']);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                blob=sections(p.with_suffix('.elf'))['.text'][1];self.assertEqual(blob[284:],bytes(len(blob)-284));images.append(list(struct.unpack_from('>71I',blob)));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],g.bound(self.prepared['qualified_owner'],s))
            for n,view,mode in itertools.product((0,1,3,255),(0,0x8000),(0,15,31)):self.compare(g.Case(count=n,view=view,mode=mode),images=images,entry=entry,s=s);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,all_three_bindings=True,signed_low16_carry=True,standalone_zero_tail=True)
    def test_06_SDK_native32_and_effective_controls(self):
        text,controls,count=native.program();p=self.out/'match-native-contract.c';p.write_text(text)
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native-contract'+opt+'.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing','-Wno-unused-but-set-variable',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),opt);self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native-controls',cases_per_profile=count,positive_executions=3*count,total_callback_calls=39*count,controls=controls,checked_control_mask=4095,SDK_native32=True,UBSan=True,raw_C_semantics=True,typed_3_argument_entry_and_6_argument_provider=True,matrix_arrays_cover_all_valid_byte_products=True,portable_stack_aliases_not_claimed=True)
    def test_07_strict_image_symbol_and_stub_controls(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+284];delta=match.strict_image(before,after,truth);self.assertEqual(delta,224);at=match.elf_slot_offset(before,match.ENTRY,284)
        for off in(0,at,at+283,at+284,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        stub=list(struct.unpack_from('>71I',before,at));m=g.Oracle(stub,g.fixture()).run();self.assertEqual(m.r[2],0);self.assertFalse(m.calls)
        self.receipt('image-controls',literal_changed_bytes=224,old_symbol_bytes=12,new_symbol_bytes=284,exclusions=0,metadata_permutations=0,corruptions=5,old_stub_rejected=True,protected_data_bytes=189088,protected_owners=720)
    def test_08_normalizer_is_input_derived_and_phase_closed(self):
        raw,b=match.function_blob(self.prepared['qualified_compact']);normalized,moved=match.derive(raw,b)
        self.assertEqual(len(raw),len(normalized));self.assertEqual(moved,match.OUTPUT_BINDINGS);self.assertEqual(set(b),{0x44,0x58,0xC4});self.assertEqual(set(moved),{0x44,0x5C,0xC4})
        old,new=struct.unpack('>71I',raw),struct.unpack('>71I',normalized);self.assertEqual(old[:16],new[:16]);self.assertEqual(old[60:],new[60:]);self.assertEqual(old[49],new[49])
        self.assertEqual((old[29]>>26,old[29]&65535),(12,255));self.assertEqual(new[22],new[19]);self.assertEqual(new[18]>>26,21);self.assertEqual(new[18]&65535,4)
        self.receipt('derivation',raw_code_SHA=match.sha(raw),no_retail_words_are_derivation_inputs=True,byte_LBU_makes_count_mask_redundant=True,conditional_stride_hoist_and_dead_sibling=True,MFLO_and_saved_copy_preserve_product=True,closed_register_role_cycles=True,frame_call_and_epilogue_unchanged=True,no_source_assembly=True)
if __name__=='__main__':unittest.main()
