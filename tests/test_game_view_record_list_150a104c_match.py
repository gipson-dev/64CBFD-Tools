"""View record-list updater: semantic C, ordered ABI and complete image gates."""
import json,struct,subprocess,unittest
from dataclasses import replace
from unittest.mock import patch
from tools.experiments import game_view_record_list_150a104c_match as source
from tools.tests import game_view_record_list_150a104c_oracle as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_remaining_donor_candidates import sections

def symbols():return {n:int(n.split('_')[1],16)for rows in source.BINDINGS.values()for _,n in rows}

class ViewRecordListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=source.ROOT;cls.out=cls.root/source.BUILD;cls.q=source.prepare(cls.root)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.elf=cls.q['qualified_elf'].read_bytes()
        cls.truth=list(struct.unpack_from('>94I',cls.rom,source.ROM));cls.words=source.bound_blob(cls.q['normal'],cls.q['normal_refs'],symbols());cls.raw=source.bound_blob(cls.q['raw'],cls.q['refs'],symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')

    def test_01_owner_scope_closed_roles_and_fail_closed_guards(self):
        q=self.q['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors']),(94,888,20,27,27))
        self.assertEqual((q['functions'],q['strict_changed_bytes'],q['exclusions'],q['diagnostics']),(6053,302,0,0));self.assertEqual(self.words,self.truth)
        rows=source.guard_rows(self.q['raw'],self.q['refs']);self.assertEqual(len(rows),20);self.assertEqual(self.q['refs'],self.q['normal_refs'])
        stores=(1,11,12,13,14,15);self.assertEqual(sorted(self.raw[i]for i in stores),sorted(self.truth[i]for i in stores))
        before=(self.out/'predecessor-guards.csv').read_bytes();after=source.guard_manifest(before,self.q['raw'],self.q['refs']);self.assertTrue(after.startswith(before));self.assertEqual(after,(self.out/'qualified-guards.csv').read_bytes())
        for at in range(0,376,4):
            raw=bytearray(self.q['raw']);raw[at+3]^=1
            with self.assertRaises(ValueError):source.normalize(bytes(raw),self.q['refs'])
        for at in self.q['refs']:
            refs=dict(self.q['refs']);refs[at]=[('R_MIPS_26','wrong')]
            with self.assertRaises(ValueError):source.normalize(self.q['raw'],refs)
        with self.assertRaises(ValueError):source.guard_manifest(before+b'\n',self.q['raw'],self.q['refs'])
        text,fs,refs=source.parse_object(self.out/'qualified-owner.o');start=fs[source.FUNCTION]['value']
        def emit():return source.pad_generated_object.emit_padded_assembly(self.out/'qualified-owner.o',self.root/'conker/asm/CDE80.s',word_patches_path=self.out/'qualified-guards.csv',filename=source.OWNER)
        for row in rows:
            at=int(row[2],16);bad=bytearray(text);bad[start+at+3]^=1
            with patch.object(source.pad_generated_object,'parse_object',return_value=(bytes(bad),fs,refs)):
                with self.assertRaisesRegex(ValueError,'stale word patch'):emit()
            bad_refs=dict(refs);bad_refs[start+at]=[('R_MIPS_HI16','wrong')]
            with patch.object(source.pad_generated_object,'parse_object',return_value=(text,fs,bad_refs)):
                with self.assertRaisesRegex(ValueError,'stale relocations'):emit()
        self.receipts['scope']=dict(words=94,frame=888,guards=20,bindings=3,neighbors=27,labels=31,
            closed_six_role_cycle=True,saved_store_permutation=6,role_words=14,raw_corruptions=94,binding_corruptions=3,
            production_guard_word_corruptions=20,production_guard_relocation_corruptions=20,prior_CSV_prefix_unchanged=True)

    def test_02_ordered_query_list_mutations_and_raw_semantics(self):
        visited=set();count=0
        for c in guest.cases():
            initial=guest.fixture(c);expected=guest.reference(initial,c);states=[]
            for body in(self.truth,self.words,self.raw):
                m=guest.Oracle(body,initial,c);regs,floats=m.r[:],m.f[:];m.run()
                self.assertEqual((guest.observable(m.memory,c),m.calls,m.query_observations),expected[:3],c)
                self.assertEqual(tuple(guest.rd(m.memory,guest.query(c)+p)for p in guest.FIELDS),tuple(guest.rd(expected[3],guest.query(c)+p)for p in guest.FIELDS))
                self.assertEqual(m.r[16:24],regs[16:24]);self.assertEqual(m.r[28:32],regs[28:32]);self.assertEqual(m.f[20:],floats[20:])
                if body is not self.raw:states.append(guest.state(m));visited.update(m.visits)
            self.assertEqual(states[0],states[1]);count+=1
        missing=set(range(source.ENTRY,source.ENTRY+376,4))-visited
        self.assertEqual(missing,{source.ENTRY+i*4 for i in(64,72,76)})
        self.receipts['model']=dict(cases=count,raw_C_and_normalized_public_semantics=True,initialized_query_fields=7,
            full_query_bytes_observed=812,public_words_reached=91,unreachable_original_words=[64,72,76],all_94_words_retained=True,
            null_and_class_gates=True,signed_height_sum=True,last_accepted_record_wins=True,query_list_view_and_incoming_home_mutations=True,
            private_aliases_guest_only=True,normalized_literal_states_equal=True)

    def test_03_original_count_gate_and_list_load_delay_slot(self):
        sites=[];pointers=[];interior=[];jal=0xC000000|(source.ENTRY>>2&0x3FFFFFF)
        for i,(w,)in enumerate(struct.iter_unpack('>I',self.rom)):
            p=i*4
            if p>=0x1000 and w==jal:sites.append(p)
            if source.ENTRY<=w<source.ENTRY+376:pointers.append(p)
            if p>=0x1000 and w>>26 in(2,3)and source.ENTRY<(0x10000000|((w&0x3FFFFFF)<<2))<source.ENTRY+376:interior.append(p)
        self.assertEqual((sites,pointers,interior),([0xCE6DC],[],[]))
        offset,entry,size=0xCE6A4,0x150A11F4,18;words=struct.unpack_from('>18I',self.rom,offset);checks=0
        code=dict(zip(range(source.ENTRY,source.ENTRY+376,4),self.words))
        for c in(guest.Case(count=0),guest.Case(count=1),guest.Case(),guest.Case(rejected=63),guest.Case(mutation=127),guest.Case(nulls=63)):
            for phase,present in((0,0),(0,1),(8,0),(8,1)):
                c=replace(c,phase=phase);initial=guest.fixture(c);home=guest.STACK+phase
                guest.wr(initial,guest.ACTOR+0x318,guest.view(c)if present else 0);guest.wr(initial,guest.ACTOR+0x127,0xD7,1);guest.wr(initial,guest.ACTOR+0x1C,guest.bits(-12.5))
                m=guest.Oracle(words,initial,c,entry=entry,connected=code);m.r[17]=guest.ACTOR;m.code=WindowCode(m.code,m);m.code.ends=(entry+size*4,)
                with self.assertRaises(WindowBoundary):m.run()
                if c.count and present:
                    expected=guest.reference(initial,c);calls=[(source.ENTRY,(guest.view(c),guest.listing(c),c.count))]+expected[1];observable=expected[0];obs=expected[2]
                else:calls=[];observable=guest.observable(initial,c);obs=[]
                self.assertEqual((m.calls,guest.observable(m.memory,c),m.query_observations),(calls,observable,obs))
                self.assertEqual((m.r[29],m.r[17],m.f[16],m.r[5]),(home,guest.ACTOR,guest.bits(-12.5),0xD7));checks+=1
        self.receipts['caller']=dict(direct_calls=1,entry_or_interior_pointers=0,direct_interior_jumps=0,original_words=18,connected_cases=checks,
            null_view_and_zero_count_skip_entire_call=True,list_loaded_in_JAL_delay_slot=True,postcall_actor_byte_reload=True,complete_large_caller_not_claimed=True)

    def test_04_literal_memory_fault_prefixes_and_full_word_counts(self):
        cuts=0
        for c in(guest.Case(),guest.Case(count=0),guest.Case(mutation=127),guest.Case(alias=1),guest.Case(alias=3)):
            initial=guest.fixture(c);full=guest.Oracle(self.truth,initial,c);full.run()
            for cut in range(full.all_accesses):
                states=[]
                for body in(self.truth,self.words):
                    m=guest.Oracle(body,initial,c);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    states.append(guest.state(m))
                self.assertEqual(states[0],states[1],(c,cut));cuts+=1
        for count in(0xFFFFFFFF,0x80000000,0x10000):
            c=guest.Case(count=count,nulls=63);initial=guest.fixture(c);states=[]
            for body in(self.truth,self.words):
                m=guest.Oracle(body,initial,c);m.cut=32
                with self.assertRaises(AccessBoundary):m.run()
                states.append(guest.state(m))
            self.assertEqual(states[0],states[1]);cuts+=1
        self.receipts['faults']=dict(executed_cuts=cuts,normalized_literal_low_word_states=True,negative_and_full_word_count_prefixes=3,
            raw_save_schedule_not_claimed_literal=True,opaque_collision_faults_not_modeled=True)

    def test_05_native32_typed_record_layout_and_effective_controls(self):
        def run(label,body=None,opt='-O2'):
            p=self.out/(label+'.c');p.write_text(guest.native_harness(body));exe=p.with_suffix('.elf')
            r=subprocess.run([*native_command(opt),'-mstackrealign',str(p.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''));return subprocess.run([str(exe)],timeout=20).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,opt=opt),0)
        b=source.SELECTED;controls=dict(stub=b[:b.index('{')+1]+'\nreturn;\n}',unsigned_height=b.replace('record->heightOffset +','(u16)record->heightOffset +'),
            wrong_secondary_y=b.replace('query.unk180 = query.y_position;','query.unk180 = query.z_position;'),wrong_class=b.replace('>> 2) == 1','>> 2) == 2'),
            cached_record=b.replace('                record = *records;\n',''),wrong_truth=b.replace('0) == 0','0) != 0'),
            skip_empty_initialization=b.replace('    query.x_position =','    if (count == 0) return;\n    query.x_position =',1),
            rebuild_query=b.replace('            if (func_150A1DA0','            query.x_position = view->unk2F8;\n            if (func_150A1DA0'))
        for name,bad in controls.items():self.assertNotEqual(b,bad,name);self.assertNotEqual(run('negative-'+name,bad),0,name)
        self.receipts['native']=dict(cases_per_executable=len(guest.native_cases()),optimizations=3,effective_controls=list(controls),trapping_UBSan=True,
            typed_void_pointer_pointer_s32_interface=True,actor812_view2464_record52_pointer32=True,typed_halfword_at8=True,
            only_seven_initialized_fields_read=True,private_aliases_and_invalid_counts_guest_only=True)

    def test_06_independent_links_and_complete_image_controls(self):
        original=symbols();moved={'D_8009F5AC':0x81238000,'func_150A1DA0':0x17518000}
        for i,bindings in enumerate((original,moved)):
            p=self.out/('rebase-'+str(i));lines=['.set noreorder','.set noat','.text','.globl updater','updater:']
            for j,(word,)in enumerate(struct.iter_unpack('>I',self.q['normal'])):
                for kind,name in self.q['normal_refs'].get(j*4,[]):lines.append('.reloc ., '+kind+', '+name)
                lines.append('.word 0x%08X'%word)
            p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS{.text 0x17508000 : SUBALIGN(4) { *(.text) }}\n')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-no-pad-sections','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v)for n,v in bindings.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            self.assertEqual(list(struct.unpack('>94I',sections(p.with_suffix('.elf'))['.text'][1])),source.bound_blob(self.q['normal'],self.q['normal_refs'],bindings))
        before,after=self.q['predecessor_elf'].read_bytes(),self.q['qualified_elf'].read_bytes();truth=self.rom[source.ROM:source.ROM+376];self.assertEqual(source.strict_image(before,after,truth),302)
        sym=next(p for p,n,f,s in source.symbol_rows(before)if n==source.FUNCTION)
        for at in(64,source.elf_slot_offset(before,source.ENTRY,376),sym+8,source.elf_slot_offset(before,0x80082B20,4)):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):source.strict_image(before,bytes(bad),truth)
        self.receipts['image']=dict(changed_bytes=302,exclusions=0,independent_links=2,bindings=3,signed_LO16_carries=True,corruption_controls=4,no_metadata_permutation=True)

if __name__=='__main__':unittest.main()
