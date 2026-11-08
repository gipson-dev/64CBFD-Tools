"""Complete subtype dispatcher, aligned mask ABI, table and literal image gates."""
import json,struct,subprocess,unittest
from dataclasses import replace
from unittest.mock import patch
from tools.experiments import game_record_subtype_150a25d4_match as source
from tools.tests import game_record_subtype_150a25d4_oracle as guest
from tools.tests import game_record_subtype_150a25d4_connections as connected
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_remaining_donor_candidates import sections
from tools.tests.game_owner_pool import normalized_pools

def symbols():
    return {'.rodata':guest.RAW_TABLE,'jtbl_8009F648':guest.JTBL,**{n:int(n.split('_')[1],16)for rows in source.BINDINGS.values()for _,n in rows if n!='.rodata'}}

class RecordSubtypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=source.ROOT;cls.out=cls.root/source.BUILD;cls.q=source.prepare(cls.root)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>110I',cls.rom,source.ROM))
        cls.words=source.bound_blob(cls.q['normal'],cls.q['normal_refs'],symbols());cls.raw=source.bound_blob(cls.q['raw'],cls.q['refs'],symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')

    def test_01_owner_table_and_fail_closed_guard_controls(self):
        q=self.q['report'];self.assertEqual((q['words'],q['raw_words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors']),(110,108,40,41,27,27))
        self.assertEqual((q['functions'],q['strict_changed_bytes'],q['exclusions'],q['diagnostics']),(6053,424,0,0));self.assertEqual(self.words,self.truth)
        before=(self.out/'predecessor-guards.csv').read_bytes();after=source.guard_manifest(before,self.q['raw'],self.q['refs']);self.assertTrue(after.startswith(before));self.assertEqual(after,(self.out/'qualified-guards.csv').read_bytes())
        rows=source.guard_rows(self.q['raw'],self.q['refs']);self.assertEqual(len(rows),41);self.assertEqual([int(r[2],16)for r in rows if r[8]],[352,356])
        for at in range(0,432,4):
            bad=bytearray(self.q['raw']);bad[at+3]^=1
            with self.assertRaises(ValueError):source.normalize(bytes(bad),self.q['refs'])
        for at in self.q['refs']:
            bad=dict(self.q['refs']);bad[at]=[('R_MIPS_26','wrong')]
            with self.assertRaises(ValueError):source.normalize(self.q['raw'],bad)
        with self.assertRaises(ValueError):source.guard_manifest(before+b'\n',self.q['raw'],self.q['refs'])
        a,b=(source.alloc_pools(self.out/(n+'.o'))for n in('predecessor-owner','qualified-owner'))
        for at in range(24):
            bad=dict(b);row=list(b['.reginfo']);raw=bytearray(row[4]);raw[at]^=1;row[4]=bytes(raw);bad['.reginfo']=tuple(row)
            with patch.object(source,'alloc_pools',side_effect=[a,bad]):
                with self.assertRaises(ValueError):source.owner_pools(None,None)
        pools=normalized_pools(self.out/'qualified-owner.o');self.assertEqual(pools['.rodata'],(bytes(48),tuple((i*4,source.FUNCTION,off)for i,off in enumerate(guest.RAW_OFFSETS))))
        for i in range(11):
            bad=dict(pools);entries=list(pools['.rodata'][1]);off,name,target=entries[i];entries[i]=(off,name,target+4);bad['.rodata']=(bytes(48),tuple(entries))
            with patch('tools.tests.game_owner_pool.normalized_pools',return_value=bad):
                with self.assertRaises(ValueError):source.owner_pools(self.out/'predecessor-owner.o',self.out/'qualified-owner.o')
        self.assertEqual(struct.unpack_from('>11I',self.rom,0x244108),tuple(source.ENTRY+off for off in guest.OFFSETS))
        text,fs,refs=source.parse_object(self.out/'qualified-owner.o');start=fs[source.FUNCTION]['value']
        def emit():return source.pad_generated_object.emit_padded_assembly(self.out/'qualified-owner.o',self.root/'conker/asm/CDE80.s',word_patches_path=self.out/'qualified-guards.csv',filename=source.OWNER)
        for row in rows:
            at=int(row[2],16);bad=bytearray(text);bad[start+at+3]^=1
            with patch.object(source.pad_generated_object,'parse_object',return_value=(bytes(bad),fs,refs)):
                with self.assertRaisesRegex(ValueError,'stale word patch'):emit()
            bad_refs=dict(refs);bad_refs[start+at]=[('R_MIPS_HI16','wrong')]
            with patch.object(source.pad_generated_object,'parse_object',return_value=(text,fs,bad_refs)):
                with self.assertRaisesRegex(ValueError,'stale relocations'):emit()
        self.receipts['scope']=dict(raw_words=108,words=110,frame=40,guards=41,raw_bindings=16,normalized_bindings=20,neighbors=27,labels=31,
            raw_word_corruptions=108,binding_corruptions=16,guard_word_corruptions=41,guard_relocation_corruptions=41,pool_target_corruptions=11,
            raw_register_metadata_corruptions=24,inserted_address_and_RA_words=2,table_bytes=44,table_padding_bytes=4,prior_CSV_prefix_fixed=True)

    def test_02_ordered_subtypes_and_aligned_mask_semantics(self):
        count=0;visited=set()
        for c in guest.cases():
            initial=guest.fixture(c);expected=guest.reference(initial,c);states=[]
            for body in(self.truth,self.words,self.raw):
                m=guest.Oracle(body,initial,c);regs,floats=m.r[:],m.f[:];m.run()
                self.assertEqual((guest.observable(m.memory,c),m.calls),expected[:2],c)
                self.assertEqual(m.r[16:24],regs[16:24]);self.assertEqual(m.r[28:32],regs[28:32]);self.assertEqual(m.f[20:],floats[20:])
                if body is not self.raw:states.append(guest.state(m));visited.update(m.visits)
            self.assertEqual(states[0],states[1]);count+=1
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+440,4))-visited,{0x150A2718})
        self.assertEqual(self.truth[79]>>26,4)
        for j,w in enumerate(self.truth):
            if w>>26 in(1,4,5,6,7,20,21,22,23):self.assertNotEqual(j+1+((w&65535)^32768)-32768,81)
        self.receipts['model']=dict(cases=count,reachable_words=109,unreachable_words=[0x150A2718],raw_C_public_semantics=True,normalized_literal_states=True,
            four_formals_with_aligned_u64_mask=True,ignored_A3_padding=True,low_mask_word_only=True,source_and_destination_aliases=True,
            source_home_alias=True,counter_actor_halfword_alias=True,post_SDK_counter_delta_reload=True,all_saved_registers_restored=True)

    def test_03_original_caller_and_connected_providers(self):
        sites=[];pointers=[];interior=[];jal=0xC000000|(source.ENTRY>>2&0x3FFFFFF)
        for i,(w,)in enumerate(struct.iter_unpack('>I',self.rom)):
            p=i*4
            if p>=0x1000 and w==jal:sites.append(p)
            if source.ENTRY<=w<source.ENTRY+440:pointers.append(p)
            if p>=0x1000 and w>>26 in(2,3)and source.ENTRY<(0x10000000|((w&0x3FFFFFF)<<2))<source.ENTRY+440:interior.append(p)
        self.assertEqual((sites,pointers,interior),([0xCF0E8],list(range(0x244108,0x244134,4)),[]))
        caller=[connected.caller(self.rom,body)for body in(self.truth,self.words,self.raw)]
        providers=connected.providers(self.rom,(self.truth,self.words,self.raw))
        self.assertEqual(caller[0],caller[1]);self.assertEqual(caller[1],caller[2])
        self.assertEqual(caller[0]['cases'],504);self.assertEqual(providers['owner_words_reached'],14);self.assertEqual(providers['action_words_reached'],18)
        # The restored random provider is byte-parameter typed. Its complete
        # pristine routine reads the index home only through its low byte.
        words=struct.unpack_from('>196I',self.rom,0x114740);frame=(-words[0])&65535
        reads=[(i,w>>26,w&65535)for i,w in enumerate(words)if w>>26 in(32,33,35,36,37)and w>>21&31==29 and frame<=w&65535<frame+4]
        self.assertTrue(reads);self.assertTrue(all(op==36 and off==frame+3 for _,op,off in reads))
        self.receipts['connections']=dict(direct_calls=1,table_pointer_entries=11,interior_direct_jumps=0,caller=caller[0],caller_body_variants=3,
            providers=providers,narrow_index_home_reads=reads,provider_narrow_definition_unchanged=True)

    def test_04_literal_fault_prefixes(self):
        cuts=0
        cases=[guest.Case(kind=k)for k in(0,1,2,3,6,8,9,10)]+[guest.Case(kind=2,alias=i)for i in(1,2,4)]+[guest.Case(alias=3,low=1,delta=31),guest.Case(mutation=31)]
        for c in cases:
            initial=guest.fixture(c);full=guest.Oracle(self.truth,initial,c);full.run()
            for cut in range(full.all_accesses):
                states=[]
                for body in(self.truth,self.words):
                    m=guest.Oracle(body,initial,c);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    states.append(guest.state(m))
                self.assertEqual(states[0],states[1],(c,cut));cuts+=1
        self.receipts['faults']=dict(executed_cuts=cuts,normalized_literal_low_word_states=True,raw_schedule_not_claimed_literal=True)

    def test_05_native32_typed_mask_ABI_and_effective_controls(self):
        def run(label,body=None,opt='-O2'):
            p=self.out/(label+'.c');p.write_text(guest.native_harness(body));exe=p.with_suffix('.elf')
            r=subprocess.run([*native_command(opt),'-mstackrealign',str(p.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''));return subprocess.run([str(exe)],timeout=20).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,opt=opt),0)
        controls=guest.semantic_controls(source.SELECTED)
        for name,bad in controls.items():self.assertNotEqual(source.SELECTED,bad);self.assertNotEqual(run('negative-'+name,bad),0,name)
        self.receipts['native']=dict(cases_per_executable=len(guest.native_cases()),optimizations=3,trapping_UBSan=True,actor812_record52_pointer32_mask64=True,
            typed_four_parameter_entry=True,typed_providers_unchanged=True,callback_stream_and_field_digests=True,effective_controls=list(controls),guest_aliases_separate=True)

    def test_06_independent_relocated_links_and_literal_full_image(self):
        original={n:v for n,v in symbols().items()if n!='.rodata'};moved={n:(0x17518000+i*0x1000 if n.startswith('func_')else 0x81238000+i*0x10000)for i,n in enumerate(original)}
        for i,bindings in enumerate((original,moved)):
            p=self.out/('rebase-'+str(i));lines=['.set noreorder','.set noat','.text','.globl dispatcher','dispatcher:']
            for j,(w,)in enumerate(struct.iter_unpack('>I',self.q['normal'])):
                for kind,name in self.q['normal_refs'].get(j*4,[]):lines.append('.reloc ., '+kind+', '+name)
                lines.append('.word 0x%08X'%w)
            p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS{.text 0x17508000 : SUBALIGN(4) { *(.text) }}\n')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-no-pad-sections','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v)for n,v in bindings.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            self.assertEqual(list(struct.unpack('>110I',sections(p.with_suffix('.elf'))['.text'][1])),source.bound_blob(self.q['normal'],self.q['normal_refs'],bindings))
        before,after=self.q['predecessor_elf'].read_bytes(),self.q['qualified_elf'].read_bytes();truth=self.rom[source.ROM:source.ROM+440]
        self.assertEqual(source.strict_image(before,after,truth),424)
        rows={n:(p,f,s)for p,n,f,s in source.symbol_rows(before)}
        positions=(64,source.elf_slot_offset(before,source.ENTRY,440),rows[source.FUNCTION][0]+8,source.elf_slot_offset(before,0x80082B20,4),rows['D_800CC2D0'][0]+4,rows['D_800CC2D0'][2])
        for at in positions:
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):source.strict_image(before,bytes(bad),truth)
        self.receipts['image']=dict(changed_bytes=424,exclusions=0,independent_links=2,raw_bindings=16,normalized_bindings=20,signed_LO16_carries=True,
            corruption_controls=len(positions),closed_symbol_string_permutations=3,metadata_permutation_bytes=69,named_definitions_fixed_except_target_size=True)

if __name__=='__main__':unittest.main()
