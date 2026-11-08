"""Class-6 actor scan: typed C, real caller/providers and exact image guards."""
import json,struct,subprocess,unittest
from dataclasses import replace
from unittest.mock import patch
from tools.experiments import game_class6_actor_scan_150a0d8c_match as source
from tools.tests import game_class6_actor_scan_150a0d8c_oracle as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_remaining_donor_candidates import sections

def symbols():return {n:int(n.split('_')[1],16)for rows in source.BINDINGS.values()for _,n in rows}

class Class6ActorScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=source.ROOT;cls.out=cls.root/source.BUILD;cls.q=source.prepare(cls.root)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>173I',cls.rom,source.ROM))
        cls.words=source.bound_blob(cls.q['normal'],cls.q['normal_refs'],symbols());cls.raw=source.bound_blob(cls.q['raw'],cls.q['refs'],symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')

    def test_01_complete_owner_mask_and_fail_closed_guard_controls(self):
        q=self.q['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors']),(173,128,31,27,27))
        self.assertEqual((q['functions'],q['strict_changed_bytes'],q['exclusions'],q['diagnostics']),(6053,533,0,0));self.assertEqual(self.words,self.truth)
        before=(self.out/'predecessor-guards.csv').read_bytes();after=source.guard_manifest(before,self.q['raw'],self.q['refs']);self.assertTrue(after.startswith(before));self.assertEqual(after,(self.out/'qualified-guards.csv').read_bytes())
        rows=source.guard_rows(self.q['raw'],self.q['refs']);self.assertEqual(len(rows),31)
        for at in range(0,692,4):
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
        text,fs,refs=source.parse_object(self.out/'qualified-owner.o');start=fs[source.FUNCTION]['value']
        def emit():return source.pad_generated_object.emit_padded_assembly(self.out/'qualified-owner.o',self.root/'conker/asm/CDE80.s',word_patches_path=self.out/'qualified-guards.csv',filename=source.OWNER)
        for row in rows:
            at=int(row[2],16);bad=bytearray(text);bad[start+at+3]^=1
            with patch.object(source.pad_generated_object,'parse_object',return_value=(bytes(bad),fs,refs)):
                with self.assertRaisesRegex(ValueError,'stale word patch'):emit()
            bad_refs=dict(refs);bad_refs[start+at]=[('R_MIPS_HI16','wrong')]
            with patch.object(source.pad_generated_object,'parse_object',return_value=(text,fs,bad_refs)):
                with self.assertRaisesRegex(ValueError,'stale relocations'):emit()
        self.receipts['scope']=dict(words=173,frame=128,guards=31,bindings=14,neighbors=27,labels=31,raw_word_corruptions=173,binding_corruptions=14,
            guard_word_corruptions=31,guard_relocation_corruptions=31,raw_register_metadata_corruptions=24,CPR1_added='0x3FC00200',padded_metadata_fixed=True,prior_CSV_prefix_fixed=True)

    def test_02_ordered_scan_raw_C_and_saved_register_lifetimes(self):
        count=0;visited=set()
        for c in guest.cases():
            initial=guest.fixture(c);expected=guest.reference(initial,c);states=[]
            for body in(self.truth,self.words,self.raw):
                m=guest.Oracle(body,initial,c);regs,floats=m.r[:],m.f[:];m.run()
                self.assertEqual((guest.observable(m.memory,c),m.calls),expected[:2],c)
                self.assertEqual(m.r[16:24],regs[16:24]);self.assertEqual(m.r[28:32],regs[28:32]);self.assertEqual(m.f[20:],floats[20:])
                if body is not self.raw:states.append(guest.state(m));visited.update(m.visits)
            self.assertEqual(states[0],states[1]);count+=1
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+692,4))-visited,set())
        self.receipts['model']=dict(cases=count,public_words_reached=173,raw_C_public_semantics=True,normalized_literal_states=True,
            actor_count=25,signed_halfword_deltas=True,opening_scale_snapshot=True,live_base_and_count=True,service_mutations=True,
            aliases=['outgoing argument frame','actor record overlap','count and pointer globals'],all_saved_GPR_and_FPR_pairs_restored=True)

    def test_03_real_gate_caller_distance_and_effect_early_return(self):
        sites=[];pointers=[];interior=[];jal=0xC000000|(source.ENTRY>>2&0x3FFFFFF)
        for i,(w,)in enumerate(struct.iter_unpack('>I',self.rom)):
            p=i*4
            if p>=0x1000 and w==jal:sites.append(p)
            if source.ENTRY<=w<source.ENTRY+692:pointers.append(p)
            if p>=0x1000 and w>>26 in(2,3)and source.ENTRY<(0x10000000|((w&0x3FFFFFF)<<2))<source.ENTRY+692:interior.append(p)
        self.assertEqual((sites,pointers,interior),([0x467BC],[],[]));count=0;helpers=set()
        for connected,kind,coords,phase in((0,0,0,0),(1,0,0,0),(1,0,1,8),(1,0,2,0),(2,0,0,0),(2,1,0,8),(3,0,0,8),(3,0,1,0)):
            c=guest.Case(connected=connected,kind=kind,coords=coords,phase=phase,count=1,radius=1000)
            initial=guest.fixture(c);expected=guest.reference(initial,c);m=guest.Oracle(self.words,initial,c,connected=guest.connected_code(self.rom,c));m.run()
            self.assertEqual((guest.observable(m.memory,c),m.calls),expected[:2]);helpers.update(m.visits);count+=1
            for gate in(0,1):
                initial=guest.fixture(c);guest.wr(initial,guest.GATE,gate,1);code=guest.connected_code(self.rom,c);code.update(zip(range(source.ENTRY,source.ENTRY+692,4),self.words))
                entry=0x150192FC;words=struct.unpack_from('>6I',self.rom,0x467AC)
                # Own the authentic return destination; stop before its next JAL.
                code[entry+24]=struct.unpack_from('>I',self.rom,0x467C4)[0]
                m=guest.Oracle(words,initial,c,entry=entry,connected=code);m.code=WindowCode(m.code,m);m.code.ends=(entry+24,)
                with self.assertRaises(WindowBoundary):m.run()
                if gate:observable,calls=guest.observable(initial,c),[]
                else:
                    expected=guest.reference(initial,c);observable,calls=expected[0],[(source.ENTRY,())]+expected[1]
                self.assertEqual((guest.observable(m.memory,c),m.calls),(observable,calls));self.assertEqual(m.r[29],guest.STACK+phase);count+=1
        distance_words={guest.DISTANCE+i*4 for i in range(32)};self.assertTrue(distance_words<=helpers)
        effect_words={p for p in helpers if guest.EFFECT<=p<0x15035D6C};self.assertGreater(len(effect_words),20)
        self.receipts['connections']=dict(cases=count,caller_words=6,direct_calls=1,pointers=0,interior_jumps=0,void_return_ignored=True,
            real_distance_words_reached=len(distance_words),real_effect_early_return_words_reached=len(effect_words),effect_ten_word_O32_packet=True,full_effect_provider_not_claimed=True)

    def test_04_literal_fault_prefixes_and_private_frame_alias(self):
        cuts=0
        for c in(guest.Case(count=0),guest.Case(count=1),guest.Case(count=1,kind=1),guest.Case(collision_mut=127),guest.Case(alias=1,count=1),guest.Case(count=1,connected=3,phase=8)):
            initial=guest.fixture(c);code=guest.connected_code(self.rom,c);full=guest.Oracle(self.truth,initial,c,connected=code);full.run()
            for cut in range(full.all_accesses):
                states=[]
                for body in(self.truth,self.words):
                    m=guest.Oracle(body,initial,c,connected=code);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    states.append(guest.state(m))
                self.assertEqual(states[0],states[1],(c,cut));cuts+=1
        self.receipts['faults']=dict(executed_cuts=cuts,normalized_literal_low_word_states=True,root_and_connected_provider_memory_accesses=True,raw_schedule_not_claimed_literal=True)

    def test_05_native32_effect_ABI_and_effective_semantic_controls(self):
        def run(label,body=None,opt='-O2'):
            p=self.out/(label+'.c');p.write_text(guest.native_harness(body));exe=p.with_suffix('.elf')
            r=subprocess.run([*native_command(opt),'-mstackrealign',str(p.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''));return subprocess.run([str(exe)],timeout=20).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,opt=opt),0)
        b=source.SELECTED
        def drop_record(n):
            lines=b.splitlines();at=[i for i,s in enumerate(lines)if 'record = (GeneratedCDE80Record *)'in s];self.assertEqual(len(at),3);del lines[at[n]];return'\n'.join(lines)
        controls=dict(stub=b[:b.index('{')+1]+'\nreturn;\n}',unsigned_z=b.replace('(s16)(actor->z_position','(u16)(actor->z_position'),wrong_class=b.replace('>> 2) == 6','>> 2) == 5'),
            skip_last_actor=b.replace('actorIndex != 25','actorIndex != 24'),wrong_mode=b.replace('offset + (u32)D_800D3098, 1)','offset + (u32)D_800D3098, 0)'),
            inclusive_radius=b.replace('distance < record->radius','distance <= record->radius'),reload_scale=b.replace('record->radius * scale','record->radius * D_8009F5A8').replace('scale = D_8009F5A8;','scale = D_8009F5A8;\n        (void)scale;'),
            cached_collision_record=drop_record(1),cached_distance_record=drop_record(2),
            cached_count=b.replace('    index = 0;','    u32 savedCount = (u32)D_800D3094;\n    index = 0;',1).replace('index < (u32)D_800D3094','index < savedCount'),
            wrong_secondary_y=b.replace('actor->x_position, actor->unk180','actor->x_position, actor->y_position'))
        for name,bad in controls.items():self.assertNotEqual(b,bad,name);self.assertNotEqual(run('negative-'+name,bad),0,name)
        self.receipts['native']=dict(cases_per_executable=len(guest.native_cases()),optimizations=3,trapping_UBSan=True,actor812_record52_pointer32=True,
            typed_void_scan_and_effect_int_int_float8_ABI=True,callback_stream_and_mutable_field_digests=True,effective_controls=list(controls),invalid_float_casts_and_aliases_guest_only=True)

    def test_06_independent_relocated_links_and_whole_image_controls(self):
        original=symbols();moved={n:(0x17518000+i*0x1000 if n.startswith('func_')else 0x81238000+i*0x10000)for i,n in enumerate(original)}
        for i,bindings in enumerate((original,moved)):
            p=self.out/('rebase-'+str(i));lines=['.set noreorder','.set noat','.text','.globl scan','scan:']
            for j,(w,)in enumerate(struct.iter_unpack('>I',self.q['normal'])):
                for kind,name in self.q['normal_refs'].get(j*4,[]):lines.append('.reloc ., '+kind+', '+name)
                lines.append('.word 0x%08X'%w)
            p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS{.text 0x17508000 : SUBALIGN(4) { *(.text) }}\n')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-no-pad-sections','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v)for n,v in bindings.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            self.assertEqual(list(struct.unpack('>173I',sections(p.with_suffix('.elf'))['.text'][1])),source.bound_blob(self.q['normal'],self.q['normal_refs'],bindings))
        before,after=self.q['predecessor_elf'].read_bytes(),self.q['qualified_elf'].read_bytes();truth=self.rom[source.ROM:source.ROM+692];self.assertEqual(source.strict_image(before,after,truth),533)
        sym=next(p for p,n,f,s in source.symbol_rows(before)if n==source.FUNCTION)
        for at in(64,source.elf_slot_offset(before,source.ENTRY,692),sym+8,source.elf_slot_offset(before,0x80082B20,4)):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):source.strict_image(before,bytes(bad),truth)
        self.receipts['image']=dict(changed_bytes=533,exclusions=0,independent_links=2,bindings=14,signed_LO16_carries=True,corruption_controls=4,no_metadata_permutation=True)

if __name__=='__main__':unittest.main()
