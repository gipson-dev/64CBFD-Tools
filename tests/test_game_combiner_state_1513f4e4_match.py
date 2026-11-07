"""Direct SDK combiner semantics, real helper/caller and complete linked image."""
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_combiner_state_1513f4e4_candidates as c
from tools.experiments import game_combiner_state_1513f4e4_match as m
from tools.tests import game_combiner_state_1513f4e4_oracle as g
from tools.tests.game_combiner_state_1513f4e4_native import harness,LINK_FLAGS
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

class CombinerStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes();cls.truth=list(struct.unpack_from('>103I',cls.rom,0x16C994));cls.raw,cls.refs=m.function_blob(cls.q['qualified_compacts'][0]);cls.words=m.bound_blob(cls.raw,cls.refs,g.symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')

    def test_01_direct_owner_history_and_two_literal_metadata_swaps(self):
        q=self.q['report'];t=q['targets'][0]
        self.assertEqual((q['frozen_inputs'],q['functions'],q['strict_changed_bytes'],q['strict_exclusions']),(181,6052,354,0));self.assertEqual((t['words'],t['frame'],t['guards'],t['bindings'],t['raw_neighbors'],t['padded_neighbors']),(103,24,0,7,58,58));self.assertEqual(t['diagnostics'],dict(before=43,after=43,new=[]));self.assertEqual(self.words,self.truth);self.assertEqual(m.derive(self.raw,self.refs),(self.raw,self.refs));self.assertEqual(m.guard_rows(),[])
        before,after,installed=c.source_states((self.root/c.TARGETS[0]['source']).read_text());self.assertEqual(c.source_states(after),(before,after,True));self.assertIn(c.STUB,before);self.assertNotIn(c.STUB,after)
        for i in range(103):
            bad=bytearray(self.raw);bad[i*4+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),self.refs)
        for at in self.refs:
            refs=dict(self.refs);refs[at]=[('R_MIPS_26','wrong_symbol')]
            with self.assertRaises(ValueError):m.derive(self.raw,refs)
        blob=self.q['qualified_compacts'][0].read_bytes()
        for section in('.reginfo','.options'):
            shape,data=m.dependent_sections(blob)[section];bad=bytearray(blob);bad[shape[4]+len(data)-1]^=1;p=self.out/('bad'+section+'.o');p.write_bytes(bad)
            with self.assertRaises(ValueError):m.pools(self.out/'match-predecessor-0.o',p)
        frozen=(self.out/'predecessor-guards.csv').read_bytes();self.assertEqual(m.guard_manifest(frozen),frozen)
        with self.assertRaises(ValueError):m.guard_manifest(b'changed history')
        self.assertEqual(m.METADATA_GROUPS,((2790108,('D_800DD1BE','D_800AB1CC'),(1,0)),(2853436,('D_800A4BA8','D_8009BBC0'),(1,0))))
        a=self.q['predecessor_elf'].read_bytes();b=self.q['qualified_elf'].read_bytes();ar=list(m.symbol_rows(a));br=list(m.symbol_rows(b))
        self.assertEqual([p for(p,n,f,s),(q,k,h,t)in zip(ar,br)if(p,n,f,s)!=(q,k,h,t)],[2790108,2790124,2853436,2853452,2973580])
        shapes=m.dependent_sections(a);other=m.dependent_sections(b)
        self.assertEqual({n:sum(x!=y for x,y in zip(data,other[n][1]))for n,(shape,data)in shapes.items()if data!=other[n][1]},{'.game':320,'.symtab':18,'.strtab':16})
        self.receipts['owner']=q

    def test_02_independent_packing_aliases_u8_and_real_selector(self):
        seen=set();count=0
        for case in g.cases():
            initial=g.fixture(case);e=g.reference(initial,case);machines=[]
            for words in(self.truth,self.words):
                v=g.Oracle(words,initial,case);v.run();self.assertEqual((g.public(v.memory,case),v.calls,v.r[2]),(e['observed'],e['calls'],e['value']),case);machines.append(v)
            self.assertEqual(g.state(machines[0]),g.state(machines[1]));seen.update(machines[0].visits);count+=1
        self.assertEqual(set(range(g.ENTRY,g.ENTRY+412,4))-seen,set())
        # Unchanged cache must not require dirty, output or table memory.
        case=g.Case(same=1);initial=g.fixture(case);minimal={p:v for p,v in initial.items()if g.STACK-2048<=p<g.STACK+512 or g.CACHE<=p<g.CACHE+2}
        for words in(self.truth,self.words):
            v=g.Oracle(words,minimal,case);v.run();self.assertEqual((g.public(v.memory,case),v.r[2]),(g.public(minimal,case),g.OUTPUT))
        helper=g.helper_code(self.rom);before=self.q['predecessor_elf'].read_bytes();at=m.elf_slot_offset(before,g.HELPER,40);self.assertEqual(before[at:at+40],self.rom[0x1704F4:0x17051C]);helper_seen=set();real_count=0
        for index,dirty,same in itertools.product((0,1,17,127,128,255,0xABCDFF80),(0,1,255),(0,1)):
            case=g.Case(index=index,dirty=dirty,same=same,phase=8);initial=g.fixture(case);e=g.reference(initial,case,connected=True);machines=[]
            for words in(self.truth,self.words):
                v=g.Oracle(words,initial,case,connected=helper);v.run();self.assertEqual((g.public(v.memory,case),v.calls,v.r[2]),(e['observed'],e['calls'],e['value']));machines.append(v)
            self.assertEqual(g.state(machines[0]),g.state(machines[1]));helper_seen.update(machines[0].visits);real_count+=1
        missing=sorted(i for i in range(10)if g.HELPER+i*4 not in helper_seen)
        for i in missing:self.assertEqual(helper[g.HELPER+i*4],0)
        self.receipts['guest']=dict(cases_per_body=count+1,bodies=2,all_target_words_executed=103,independent_field_masks_and_ordered_memory_model=True,six_explicit_alias_positions=True,all_256_indices_and_four_dirty_values=True,changed_and_unchanged_signed_cache=True,unchanged_cache_needs_no_table_or_output_mapping=True,incoming_home_mutations_guest_only=True,original_selector_words_compared=10,selector_cases_per_body=real_count,selector_words_executed=10-len(missing),selector_unused_padding_words=missing,production_selector_already_exact=True,full_private_machine_identity=True)

    def test_03_full_original_renderer_actual_calls_and_pointer_ABI(self):
        jal=0x0C000000|((g.ENTRY>>2)&0x3FFFFFF);calls=[];pointers=[]
        for i,(word,)in enumerate(struct.iter_unpack('>I',self.rom)):
            if word==jal:calls.append(i*4)
            if g.ENTRY<=word<g.ENTRY+412:pointers.append((i*4,word))
        self.assertEqual((len(calls),pointers),(41,[]));self.assertIn(0x16B38C,calls)
        import csv
        layout=list(csv.DictReader((self.root/'conker/retail_layout.us.txt').open()));names=[]
        for at in calls:
            pc=0x15000000+at-0x2D4B0;rows=[r for r in layout if r['section']=='game'and int(r['address'],16)<=pc<int(r['end'],16)];self.assertEqual(len(rows),1);names.append(rows[0]['function'])
        self.assertEqual(len(set(names)),36)
        caller=list(struct.unpack_from('>295I',self.rom,0x16AFB0));seen=set();count=0;target_calls=0
        for flags,enabled,view,success,animation,attached in itertools.product((0,8,0x1000000,0xC000,0x20000000,0x7FFFFFE0),(0,1),(0,1),(0,1),(0,255),(0,1,2)):
            rc=g.render.Case(view=view,success=success,scale=2,mutation=1,redirect=1);case=g.Case(pattern=count%4,cache=0xFFFF if count%2 else 0x7FFF);initial=g.caller_fixture(rc,case,flags,enabled,255,attached,animation)
            reference=g.CallerOracle(caller,initial,rc,case,provider=True);reference.run();machines=[]
            for words in(self.truth,self.words):
                code=g.helper_code(self.rom);code.update(zip(range(g.ENTRY,g.ENTRY+412,4),words));v=g.CallerOracle(caller,initial,rc,case,connected=code);v.run();self.assertEqual((g.render.public(v.memory,rc),v.calls,v.r[2]),(g.render.public(reference.memory,rc),reference.calls,reference.r[2]));machines.append(v)
            self.assertEqual(g.state(machines[0]),g.state(machines[1]));seen.update(machines[0].visits);target_calls+=sum(t==g.ENTRY for t,a in machines[0].calls);count+=1
        for has_buffer in(0,1):
            rc=g.render.Case(view=1);case=g.Case();initial=g.caller_fixture(rc,case,8,1,0);g.wr(initial,g.render.slot(rc),g.render.BUFFER if has_buffer else 0)
            reference=g.CallerOracle(caller,initial,rc,case,provider=True);reference.run();machines=[]
            for words in(self.truth,self.words):
                code=g.helper_code(self.rom);code.update(zip(range(g.ENTRY,g.ENTRY+412,4),words));v=g.CallerOracle(caller,initial,rc,case,connected=code);v.run();self.assertEqual((g.render.public(v.memory,rc),v.calls,v.r[2]),(g.render.public(reference.memory,rc),reference.calls,reference.r[2]));machines.append(v)
            self.assertEqual(g.state(machines[0]),g.state(machines[1]));seen.update(machines[0].visits);target_calls+=sum(t==g.ENTRY for t,a in machines[0].calls);count+=1
        missing={i for i in range(295)if g.render.CALLER+i*4 not in seen};self.assertEqual(missing,{115,146});self.assertGreater(target_calls,0)
        for i,branch in((115,111),(146,142)):
            self.assertEqual(caller[branch]>>26,1);self.assertEqual(caller[branch+2]>>26,4);self.assertEqual((caller[branch]&65535,caller[branch+2]&65535),(4,2))
        before=self.q['predecessor_elf'].read_bytes();at=m.elf_slot_offset(before,g.render.CALLER,1180);self.assertNotEqual(before[at:at+1180],self.rom[0x16AFB0:0x16B44C])
        self.receipts['caller']=dict(cases_per_body=count,actual_target_calls_per_body=target_calls,original_renderer_words_compared=295,reachable_renderer_words_executed=293,unreachable_duplicate_defaults=sorted(missing),direct_JAL_sites=41,unique_direct_callers=36,entry_or_interior_pointers=0,Gfx_pointer_u8_dirty_pointer_ABI=True,independent_combiner_provider_counterpart=True,actual_selector_connected=True,other_renderer_services_bounded=True,production_dispatcher_still_unrestored=True)

    def test_04_all_access_prefixes_and_RA_lifetime(self):
        cuts=delays=0
        for case,connected in((g.Case(same=1),False),(g.Case(dirty=0),False),(g.Case(),False),(g.Case(alias=1),False),(g.Case(alias=3),False),(g.Case(alias=4),False),(g.Case(mutation=2),False),(g.Case(mutation=3),False),(g.Case(),True)):
            initial=g.fixture(case);code=g.helper_code(self.rom)if connected else None;full=g.Oracle(self.truth,initial,case,connected=code);full.run();self.assertIn(('W',g.STACK+case.phase-4,4,0xDEAD0000),full.trace)
            for cut in range(full.all_accesses):
                machines=[]
                for words in(self.truth,self.words):
                    v=g.Oracle(words,initial,case,connected=code);v.cut=cut
                    with self.assertRaises(AccessBoundary):v.run()
                    machines.append(v)
                self.assertEqual(g.state(machines[0]),g.state(machines[1]));cuts+=1;delays+=machines[0].delay_of is not None
        self.receipts['faults']=dict(fired_cuts=cuts,delay_cuts=delays,full_memory_GPR_FPR_HI_LO_PC_delay_and_access_prefix_identity=True,frame=24,saved_RA_and_incoming_homes=True,original_selector_prefixes=True,guest_only_provider_home_mutations=True)

    def test_05_native32_SDK_Gfx_and_effective_controls(self):
        def run(label,body,opt):
            path=self.out/(label+'.c');path.write_text(harness(body));exe=path.with_suffix('.elf');p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),*LINK_FLAGS,'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(p.stdout+p.stderr,'');return subprocess.run([str(exe)],timeout=20).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,None,opt),0,opt)
        s=c.SELECTED
        variants=dict(stub=s[:s.index('{')+1]+'\nreturn cursor;\n}',wrong_compare=s.replace('selection != D_800DD1BE','selection == D_800DD1BE'),wrong_dirty=s.replace('*dirty == 1','*dirty != 0'),skip_clear=s.replace('            *dirty = 0;',''),wrong_mode=s.replace('func_15143044(index, 0)','func_15143044(index, 1)'),wrong_table=s.replace('D_800A4BA8[index]','D_800A4BA8[0]'),wrong_mux=s.replace('GCCc1w0(record[8], record[10])','GCCc1w0(record[8], record[8])'),wrong_cache=s.replace('D_800DD1BE = selection','D_800DD1BE = 0'),wrong_return=s.replace('return cursor;','return NULL;'))
        rejected={}
        for label,body in variants.items():self.assertNotEqual(body,s,label);answer=run('negative-'+label,body,'-O2');self.assertEqual(answer,1,label);rejected[label]=answer
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(g.native_cases()),SDK_Gfx64_and_pointer32=True,typed_u8_and_pointer_return_call=True,all_256_selectors=True,signed16_cache_and_provider_return=True,selector_call_arguments_and_count_checked=True,UBSan_traps=True,semantic_negatives=rejected,aliases_and_incoming_homes_guest_only=True)

    def test_06_independent_GNU_links_and_repeated_cache_pairs(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        configs=((g.ENTRY,g.symbols()),(0x17407F50,dict(func_15143044=0x17418010,D_800DD1BE=0x81238002,D_800A4BA8=0x82347FF8)))
        for i,(entry,symbols)in enumerate(configs):
            lines=['.set noreorder','.set noat','.text','.globl func_1513F4E4','func_1513F4E4:']
            for j,(word,)in enumerate(struct.iter_unpack('>I',self.raw)):
                refs=self.refs.get(j*4,[])
                if not refs:line='.word 0x%08X'%word
                else:
                    self.assertEqual(len(refs),1);kind,name=refs[0];rt,rs=word>>16&31,word>>21&31
                    if kind=='R_MIPS_26':line='jal '+name
                    elif kind=='R_MIPS_HI16':line='lui $%d, %%hi(%s)'%(rt,name)
                    elif word>>26==9:line='addiu $%d, $%d, %%lo(%s)'%(rt,rs,name)
                    else:self.assertIn(word>>26,(33,41));line=('lh'if word>>26==33 else'sh')+' $%d, %%lo(%s)($%d)'%(rt,name,rs)
                lines.append(line)
            p=self.out/('rebase-'+str(i));p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v)for n,v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>103I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(self.raw,self.refs,symbols))
        self.receipts['relocations']=dict(independent_links=2,bindings=7,repeat_cache_HI_LO_pairs=2,signed_LO_carry=True,guards=0)

    def test_07_literal_full_image_and_effective_corruptions(self):
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),354)
        slot=[p for p,n,f,s in m.symbol_rows(before)if n=='func_1513F4E4'];self.assertEqual(len(slot),1)
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,412),slot[0]+8,2790108+4,2853436+14,3071586,3123139):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=354,exclusions=0,body_bytes=320,symbol_bytes=18,string_bytes=16,literal_adjacent_symbol_name_swaps=2,named_definitions_fixed_except_target_size=True,corruptions_rejected=7)

if __name__=='__main__':unittest.main()
