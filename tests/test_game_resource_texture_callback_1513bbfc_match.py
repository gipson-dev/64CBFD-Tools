"""Texture callback: float32 model, original helpers/caller, padding and full image."""
from collections import Counter
from dataclasses import replace
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_resource_texture_callback_1513bbfc_candidates as c
from tools.experiments import game_resource_texture_callback_1513bbfc_match as m
from tools.tests import game_resource_texture_callback_1513bbfc_oracle as g
from tools.tests.game_resource_texture_callback_1513bbfc_native import harness,cases as native_cases,LINK_FLAGS
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

class ResourceTextureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes();cls.truth=list(struct.unpack_from('>173I',cls.rom,0x1690AC));cls.raw,cls.refs=m.function_blob(cls.q['qualified_compacts'][0]);cls.normal,cls.nr=m.derive(cls.raw,cls.refs);cls.words=m.bound_blob(cls.normal,cls.nr,g.symbols());cls.compact=m.bound_blob(cls.raw,cls.refs,g.symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def compare(self,case,raw=True):
        initial=g.fixture(case);expected=g.reference(initial,case);machines=[]
        for body in(self.truth,self.words,*([self.compact]if raw else [])):
            machine=g.Oracle(body,initial,case,connected=g.helpers(self.rom,case)).run();self.assertEqual((g.public(machine.memory,case),machine.calls,machine.r[2]),(expected['observed'],expected['calls'],expected['value']),case);machines.append(machine)
        self.assertEqual(g.state(machines[0]),g.state(machines[1]),case);return machines
    def test_01_complete_owner_guard_proof_and_FP_metadata(self):
        q=self.q['report'];t=q['targets'][0];self.assertEqual((q['frozen_inputs'],q['functions'],q['strict_changed_bytes'],q['strict_exclusions']),(149,6052,590,0));self.assertEqual((t['words'],t['frame'],t['guards'],t['bindings'],t['raw_neighbors'],t['padded_neighbors']),(173,88,60,20,12,12));self.assertEqual(t['diagnostics'],dict(before=4,after=4,new=[]));self.assertEqual(self.words,self.truth)
        normal,refs,proof=m.normalization(self.raw,self.refs);rows=m.guard_rows();self.assertEqual((sum(bool(r[8])for r in rows),sum(r[10]=='true'for r in rows)),(2,1))
        fp=lambda blob:Counter(w for w, in struct.iter_unpack('>I',blob)if w>>26==17 and w>>21&31!=8)
        self.assertEqual(fp(self.raw),fp(self.normal));self.assertEqual(sorted(i for i in proof['order']if isinstance(i,int)),[i for i in range(172)if i!=27]);self.assertEqual(proof['reused_NOP_words'],[103,155])
        for offset in(0,64,76,104,108,112,336,408,600,684):
            bad=bytearray(self.raw);bad[offset+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),self.refs)
        with self.assertRaises(ValueError):m.derive(self.raw,{**self.refs,108:[('R_MIPS_LO16','D_800A4A78')]})
        old=self.out/'match-predecessor-0.o';new=self.q['qualified_compacts'][0];blob=new.read_bytes()
        for section in('.reginfo','.options'):
            shape,data=m.dependent_sections(blob)[section];bad=bytearray(blob);bad[shape[4]+len(data)-1]^=1;p=self.out/('bad'+section+'.o');p.write_bytes(bad)
            with self.assertRaises(ValueError):m.pools(old,p)
        self.receipts['owner']=q;self.receipts['normalization']=dict(guards=60,raw_words=172,retail_words=173,folded_dead_address_word=27,reused_existing_NOPs=[103,155],path_duplicated_loads=[107,113],FP_operation_words_preserved=True,no_FP_register_or_arithmetic_replacements=True,closed_T4_T5_pair_and_commutative_integer_adds=True,raw_private_PC_FCSR_fault_identity_not_claimed=True)
    def test_02_independent_float32_vertices_live_aliases_and_bounds(self):
        seen=set();count=0;cases=list(g.cases())
        cases.extend(g.Case(layout=layout,geometry=geom,positions=1)for layout,geom in itertools.product((0,4),(0,1)))
        cases.extend(g.Case(layout=4,base=base)for base in(0x7FFFFFF0,0x80000000,0xFFFFFFF0))
        for case in cases:seen.update(self.compare(case)[0].visits);count+=1
        self.assertEqual(set(range(g.ENTRY,g.ENTRY+692,4))-seen,{g.ENTRY+105*4})
        self.receipts['guest']=dict(cases_per_body=count,bodies=3,reachable_words=172,literal_unreachable_word=105,all_173_words_compared=True,retained_nine_groups_140_vertices=True,negative_zero_scroll_and_1024_truncation=True,signed_vertices_and_low16_output=True,live_page_buffer_range_and_center_aliases=True,signed_view_and_wrapped_resource_addresses_guest_only=True,raw_public_model_only=True,normalized_retail_full_private_machine_states=True,nonfinite_conversion_cases_use_bounded_word_convention_not_FCSR_or_hardware_proof=True)
    def test_03_original_matrix_and_view_helpers(self):
        seen={1:set(),2:set()};count=0
        for connected,view,geometry,mutation in itertools.product((1,2,3),(0,1,3),(0,1),(0,1)):
            case=g.Case(layout=4,connected=connected,view=view,geometry=geometry,mutation=mutation);machines=self.compare(case)
            for bit in seen:
                if connected&bit:seen[bit].update(machines[0].visits)
            count+=1
        before=self.q['predecessor_elf'].read_bytes()
        for bit,entry,offset,n in((1,g.MATRIX,0x168E18,16),(2,g.VIEW,0x171FE4,13)):
            at=m.elf_slot_offset(before,entry,n*4);self.assertEqual(before[at:at+n*4],self.rom[offset:offset+n*4]);self.assertEqual(set(range(entry,entry+n*4,4))-seen[bit],set())
        self.receipts['helpers']=dict(cases_per_body=count,original_matrix_words=16,original_view_words=13,all_helper_words_executed=True,production_helpers_already_exact=True,view_state_stride=0x9A0,view_position_offset=0x2F8,matrix_and_sine_services_bounded=True)
    def test_04_callback_pointer_census_and_original_renderer(self):
        jal=0x0C000000|((g.ENTRY>>2)&0x03FFFFFF);direct=[];pointers=[]
        for i,(word,)in enumerate(struct.iter_unpack('>I',self.rom)):
            if word==jal:direct.append(i*4)
            if g.ENTRY<=word<g.ENTRY+692:pointers.append((i*4,word))
        self.assertEqual(direct,[]);self.assertEqual(pointers,[(0x22E6FC,g.ENTRY)])
        renderer=0x1513B83C;words=struct.unpack_from('>75I',self.rom,0x168CEC);before=self.q['predecessor_elf'].read_bytes();at=m.elf_slot_offset(before,renderer,300);self.assertEqual(before[at:at+300],self.rom[0x168CEC:0x168E18]);count=0;seen=set();cursor=0xB0000;table=0x80089C28
        for connected,view,geometry in itertools.product((0,3),(0,1,3),(0,1)):
            case=g.Case(layout=4,view=view,geometry=geometry,connected=connected);initial=g.fixture(case);initial[case.base+0x10]=0;initial[case.base+0x12]=5;initial[case.base+0x49]=255;g.wr(initial,table+20,g.ENTRY)
            for i in range(64):initial[cursor+i]=(i*13+0xA5)&255
            expected=g.reference(initial,case,home=g.STACK-32);memory=expected['memory'];g.wr(memory,cursor,0xDA380003);g.wr(memory,cursor+4,case.base+0x78+memory[g.PAGE]*64);g.wr(memory,cursor+8,0xDB060004);g.wr(memory,cursor+12,g.rd(memory,g.slot(case,memory[g.PAGE])));g.wr(memory,cursor+16,0xDE000000);g.wr(memory,cursor+20,g.rd(memory,case.base+0x54));calls=[(g.ENTRY,(case.base,g.u32(g.signed16(view))))]+expected['calls'];machines=[]
            for body in(self.truth,self.words,self.compact):
                code=g.helpers(self.rom,case);code.update(zip(range(g.ENTRY,g.ENTRY+len(body)*4,4),body));machine=g.Oracle(words,initial,case,entry=renderer,connected=code,arguments=(cursor,case.base,g.u32(view))).run();self.assertEqual((g.public(machine.memory,case),machine.calls,machine.r[2]),(g.public(memory,case),calls,cursor+24));machines.append(machine)
            self.assertEqual(g.state(machines[0]),g.state(machines[1]));seen.update(machines[0].visits);count+=1
        self.receipts['caller']=dict(direct_JALs=0,entry_pointers=1,interior_pointers=0,callback_slot=5,connected_renderer_cases_per_body=count,retained_renderer_words=75,executed_renderer_words=len(seen&set(range(renderer,renderer+300,4))),source_render_callback_ABI_matches=True,complete_texture_to_three_command_path=True)
    def test_05_fired_fault_prefixes_and_saved_FP_pairs(self):
        cuts=delays=0
        for case in(g.Case(layout=2),g.Case(layout=4),g.Case(layout=4,geometry=1),g.Case(layout=1,geometry=1,alias=3,sin0=0),g.Case(layout=4,connected=3,mutation=1)):
            full=self.compare(case)[0]
            for cut in range(full.all_accesses):
                machines=[]
                for body in(self.truth,self.words):
                    machine=g.Oracle(body,g.fixture(case),case,connected=g.helpers(self.rom,case));machine.cut=cut
                    with self.assertRaises(AccessBoundary):machine.run()
                    machines.append(machine)
                self.assertEqual(g.state(machines[0]),g.state(machines[1]));cuts+=1;delays+=machines[0].delay_of is not None
        self.receipts['faults']=dict(fired_cuts=cuts,delay_cuts=delays,full_private_memory_GPR_FPR_HI_LO_PC_trace=True,six_saved_FP_pairs_and_S0_S1_S2_preserved=True,raw_fault_FCSR_and_hardware_exception_identity_not_claimed=True)
    def test_06_native32_SDK_float_and_compiled_controls(self):
        def run(label,body,opt):
            path=self.out/(label+'.c');path.write_text(harness(body));exe=path.with_suffix('.elf');p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),*LINK_FLAGS,'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''));return subprocess.run([str(exe)]).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,None,opt),0,opt)
        s=c.SELECTED;variants=dict(stub=s[:s.index('{')+1]+'\nreturn 0;\n}',omit_matrix=s.replace('func_1513B968((s32)resource, view);',';'),wrong_angle=s.replace('sinf(payload[3])','sinf(payload[2])'),wrong_scale=s.replace('* D_800A4A74 + D_800A4A78','* D_800A4A74 - D_800A4A78'),wrong_zero_axis=s.replace('directionX = 1.0f;','directionX = -1.0f;'),wrong_wrap=s.replace('* 1024.0f','* 512.0f'),wrong_view=s.replace('func_15144B34(view)','func_15144B34(0)'),reload_payload=s.replace('    wrappedS =','    payload = (f32 *)(resource + *(u32 *)(resource + 0x50) + 0xF8);\n    wrappedS =',1),wrong_page=s.replace('((u32)D_800BE9C0 << 4)','(((u32)D_800BE9C0 ^ 1) << 4)'),wrong_direction=s.replace('directionZ = -horizontal * inverse','directionZ = horizontal * inverse'),missing_last_group=s.replace('(TextureVertexRange168A90 *)&D_800A4A74','D_800A4A2C + 8'),wrong_result=s.replace('    return 1;','    return 0;'));rejected={}
        for label,body in variants.items():
            self.assertNotEqual(body,s,label);answer=run('negative-'+label,body,'-O2');self.assertEqual(answer,1,label);rejected[label]=answer
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(list(native_cases())),SDK_Vtx16_ST8_range8_pointer32=True,retained_data_layout_endpoint_asserted=True,explicit_single_precision_SSE_sqrt=True,sine_services_controlled=True,signed16_narrowing_and_negative_1024_scroll=True,UBSan_traps=True,semantic_negatives=rejected,aliases_sparse_indices_invalid_conversions_and_private_homes_guest_only=True)
    def test_07_GNU_rebases_and_closed_full_image(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        moved=dict(g.symbols());base=0x81237FA0
        for name,off in(('D_800A49C0',0),('D_800A4A2C',108),('D_800A4A74',180),('D_800A4A78',184),('D_800A4A7C',188),('D_800A4A80',192)):moved[name]=base+off
        moved.update(D_800BE9C0=0x82348002,func_1513B968=0x1753B968,sinf=0x17547D60,func_15144B34=0x17644B34);links=0
        for entry,symbols in((g.ENTRY,g.symbols()),(0x17407F50,moved)):
            lines=['.set noreorder','.set noat','.text','.globl func_1513BBFC','func_1513BBFC:']
            for i,(word,)in enumerate(struct.iter_unpack('>I',self.normal)):
                refs=self.nr.get(i*4,[])
                if not refs:line='.word 0x%08X'%word
                else:
                    self.assertEqual(len(refs),1);kind,name=refs[0];rt,rs=word>>16&31,word>>21&31
                    if kind=='R_MIPS_26':line='jal '+name
                    elif kind=='R_MIPS_HI16':line='lui $%d, %%hi(%s)'%(rt,name)
                    elif word>>26==49:line='lwc1 $f%d, %%lo(%s)($%d)'%(rt,name,rs)
                    else:self.assertEqual(word>>26,9);line='addiu $%d, $%d, %%lo(%s)'%(rt,rs,name)
                lines.append(line)
            p=self.out/('rebase-'+str(links));p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v)for n,v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            self.assertEqual(list(struct.unpack_from('>173I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(self.normal,self.nr,symbols));links+=1
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),590)
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,692),2752128,2818146,3040154,3094648):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=590,exclusions=0,closed_symbol_string_pair_swaps=2,named_definitions_preserved=True,independent_links=links,bindings=20,signed_LO_carry_and_folded_scalar_load=True,corruptions_rejected=6)
if __name__=='__main__':unittest.main()
