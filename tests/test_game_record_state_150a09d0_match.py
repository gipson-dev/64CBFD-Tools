"""Record-state scan: typed C, original caller/SDK and strict image guards."""
import json,struct,subprocess,unittest
from dataclasses import replace
from unittest.mock import patch
from tools.experiments import game_record_state_150a09d0_match as source
from tools.tests import game_record_state_150a09d0_oracle as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_remaining_donor_candidates import sections

def symbols():return {n:int(n.split('_')[1],16)for rows in source.BINDINGS.values()for _,n in rows}

class RecordStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=source.ROOT;cls.out=cls.root/source.BUILD;cls.q=source.prepare(cls.root)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>209I',cls.rom,source.ROM))
        cls.words=source.bound_blob(cls.q['normal'],cls.q['normal_refs'],symbols());cls.raw=source.bound_blob(cls.q['raw'],cls.q['refs'],symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')

    def test_01_complete_owner_mask_and_fail_closed_guard_controls(self):
        q=self.q['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors']),(209,64,60,27,27))
        self.assertEqual((q['functions'],q['strict_changed_bytes'],q['exclusions'],q['diagnostics']),(6053,612,0,0));self.assertEqual(self.words,self.truth)
        self.assertEqual((q['caller']['functions'],q['caller']['inherited_diagnostics'],q['caller']['new_diagnostics']),(16,3,0))
        self.assertEqual(q['caller']['actual_Make']['commands'],3);self.assertTrue(q['caller']['padded_whole_object_fixed'])
        before=(self.out/'predecessor-guards.csv').read_bytes();after=source.guard_manifest(before,self.q['raw'],self.q['refs']);self.assertTrue(after.startswith(before));self.assertEqual(after,(self.out/'qualified-guards.csv').read_bytes())
        rows=source.guard_rows(self.q['raw'],self.q['refs']);self.assertEqual(len(rows),60)
        for at in range(0,836,4):
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
        self.receipts['scope']=dict(words=209,frame=64,guards=60,bindings=25,neighbors=27,labels=31,raw_word_corruptions=209,binding_corruptions=25,
            guard_word_corruptions=60,guard_relocation_corruptions=60,raw_register_metadata_corruptions=24,CPR1_added='0x00000000',padded_metadata_fixed=True,prior_CSV_prefix_fixed=True)

    def test_02_ordered_record_states_raw_C_and_saved_lifetimes(self):
        count=0;visited=set()
        for c in guest.cases():
            initial=guest.fixture(c);expected=guest.reference(initial,c);states=[]
            for body in(self.truth,self.words,self.raw):
                m=guest.Oracle(body,initial,c);regs,floats=m.r[:],m.f[:];m.run()
                self.assertEqual((guest.observable(m.memory,c),m.calls),expected[:2],c)
                self.assertEqual(m.r[16:24],regs[16:24]);self.assertEqual(m.r[28:32],regs[28:32]);self.assertEqual(m.f[20:],floats[20:])
                if body is not self.raw:states.append(guest.state(m));visited.update(m.visits)
            self.assertEqual(states[0],states[1]);count+=1
        dead={0x150A0B10,0x150A0BB8}
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+836,4))-visited,dead)
        # Both redundant instructions follow unconditional branches with owned
        # delay slots; neither can be a branch destination in this routine.
        for address in dead:
            i=(address-source.ENTRY)//4;w=self.truth[i-2]
            self.assertEqual(w>>26,4);self.assertEqual(w>>16&1023,0)
            for j,branch in enumerate(self.truth):
                if branch>>26 in(1,4,5,6,7,20,21,22,23):
                    self.assertNotEqual(j+1+((branch&65535)^32768)-32768,i)
        self.assertEqual(self.truth[9],0xAFA40040)
        self.receipts['model']=dict(cases=count,reachable_words=207,proven_dead_words=sorted(dead),raw_C_public_semantics=True,
            normalized_literal_states=True,live_base_count_and_view_bound=True,all_classes_and_five_call_sites=True,
            aliases=['outgoing fifth word','count global','viewer and source byte','viewer and signed bound','map byte and retained record'],
            unused_incoming_word_stored=True,all_saved_GPR_and_FPR_pairs_restored=True)

    def test_03_original_caller_and_SDK_low_half_argument(self):
        sites=[];pointers=[];interior=[];jal=0xC000000|(source.ENTRY>>2&0x3FFFFFF)
        for i,(w,)in enumerate(struct.iter_unpack('>I',self.rom)):
            p=i*4
            if p>=0x1000 and w==jal:sites.append(p)
            if source.ENTRY<=w<source.ENTRY+836:pointers.append(p)
            if p>=0x1000 and w>>26 in(2,3)and source.ENTRY<(0x10000000|((w&0x3FFFFFF)<<2))<source.ENTRY+836:interior.append(p)
        self.assertEqual((sites,pointers,interior),([0x462B8,0x1567B8],[],[]))
        wrapper_cases=0
        for phase in(0,8):
            for count in(0,1):
                for incoming in(0,0xD00DFEED,0xFFFFFFFF):
                    c=guest.Case(phase=phase,count=count,incoming=incoming);initial=guest.fixture(c);home=guest.STACK+phase
                    guest.wr(initial,0x800BE9E4,incoming)
                    entry,end=0x15018DFC,0x15018E10;window=struct.unpack_from('>5I',self.rom,0x462AC)
                    self.assertEqual(window,(0x27BDFFE8,0xAFBF0014,0x3C04800C,jal,0x8C84E9E4))
                    code=dict(zip(range(source.ENTRY,source.ENTRY+836,4),self.words));code[end]=struct.unpack_from('>I',self.rom,0x462C0)[0]
                    m=guest.Oracle(window,initial,c,entry=entry,connected=code);expected=guest.reference(initial,c,home=home-24)
                    m.code=WindowCode(m.code,m);m.code.ends=(end,)
                    with self.assertRaises(WindowBoundary):m.run()
                    self.assertEqual((guest.observable(m.memory,c),m.calls),(expected[0],[(source.ENTRY,(incoming,))]+expected[1]))
                    self.assertEqual(m.r[29],home-24);wrapper_cases+=1
        entry,end=0x15129290,0x15129340;window=struct.unpack_from('>44I',self.rom,0x156740)
        self.assertEqual(window[0],0x3C04800C);self.assertEqual(window[30:32],(jal,0x8C84E9E4))
        # No return-value read before the subsequent call overwrites V0.
        self.assertTrue(all(2 not in(w>>21&31,w>>16&31,w>>11&31)for w in window[32:]))
        calls=0
        for phase in(0,8):
            for incoming in(0,0x80000000,0xD00DFEED,0xFFFFFFFF):
                c=guest.Case(phase=phase,incoming=incoming);initial=guest.fixture(c);home=guest.STACK+phase
                actor,a,b=0x181000,0x180000,0x180100
                for base in(actor,a,b,0x182000,0x182100,0x182200,0x182300):
                    initial.update({base+j:(j*31+91)&255 for j in range(0x9A0 if base==actor else 64)})
                for off,dest in((0x9C,0x182000),(0x94,0x182100),(0x8C,0x182200),(0x88,0x182300)):guest.wr(initial,home+off,dest)
                guest.wr(initial,0x800BE9E4,incoming)
                code=dict(zip(range(source.ENTRY,source.ENTRY+836,4),self.words));code[end]=struct.unpack_from('>I',self.rom,0x1567F0)[0]
                m=guest.Oracle(window,initial,c,entry=entry,connected=code);m.r[16]=a;m.r[17]=actor;m.r[18]=b
                prior=dict(initial);guest.wr(prior,actor+0x39C,m.f[8])
                for src,dst in((b,0x182000),(a,0x182100),(b,0x182200),(a,0x182300)):
                    for j in range(12):prior[dst+j]=prior[src+j]
                expected=guest.reference(prior,c);m.code=WindowCode(m.code,m);m.code.ends=(end,)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual((guest.observable(m.memory,c),m.calls),(expected[0],[(source.ENTRY,(incoming,))]+expected[1]))
                self.assertEqual(m.r[29],home);calls+=1
        stop_words=struct.unpack_from('>72I',self.rom,guest.STOP-0x10000000)
        self.assertEqual(stop_words[31],0x97B6004A)
        class SDKOracle(guest.Oracle):
            def record_call(m,target):
                if target!=0x100111C8:return super(SDKOracle,m).record_call(target)
                a=tuple(m.arguments(1));m.calls.append((target,a));m.events.append(('CALL',target,a))
            def hook(m,target):
                if target!=0x100111C8:return super(SDKOracle,m).hook(target)
                if m.sdk_mutation:guest.wr(m.memory,0x80042760,0)
                for i in range(4):m.put(m.r[29]+4*i,0xB5000000+i,4)
                for i in(1,2,3,*range(4,16),24,25):m.r[i]=0xA5000000+i
                m.f[:20]=[0xA5000000+i for i in range(20)];m.r[2]=0xDEADBEEF
        sdk_cases=0;visits=set()
        for upper in(0,0xAAAA0000,0xFFFF0000):
            for mismatch in range(7):
                c=guest.Case(count=1,gate=0,parameter=upper|0x1234);initial=guest.fixture(c);p=guest.RECORDS
                initial.update({0x80041FE0+i:0 for i in range(96)})
                for off,val in((0,c.timer>>16),(2,-10),(4,20),(6,-1),(8,0x9234),(0x24,0 if mismatch==5 else 0x55)):
                    guest.wr(initial,0x80041FE0+off,val,2)
                if mismatch<5:guest.wr(initial,0x80041FE0+mismatch*2,0,2)
                guest.wr(initial,0x80042760,1);guest.wr(initial,0x80041FF0,0x12340000)
                expected=guest.reference(initial,c);wanted=dict(expected[2])
                # The connected SDK does not run the opaque STOP hook.
                for j in range(8):wanted[guest.MARK+j]=initial[guest.MARK+j]
                expected_calls=expected[1][:]
                if mismatch>=5:
                    guest.wr(wanted,0x80041FF0,0x12340080)
                    if mismatch==6:expected_calls.insert(1,(0x100111C8,(0x55,)));guest.wr(wanted,0x80042760,0)
                code=dict(zip(range(guest.STOP,guest.STOP+288,4),stop_words))
                states=[]
                for body in(self.truth,self.words,self.raw):
                    m=SDKOracle(body,initial,c,connected=code);m.sdk_mutation=mismatch==6;m.run();visits.update(m.visits)
                    self.assertEqual((guest.observable(m.memory,c),m.calls),(guest.observable(wanted,c),expected_calls),(upper,mismatch))
                    # The root passes the full word; SDK LHU consumes its low half.
                    self.assertEqual(m.calls[0][1][4],upper|0x1234)
                    if body is not self.raw:states.append(guest.state(m))
                self.assertEqual(states[0],states[1]);sdk_cases+=1
        self.assertIn(guest.STOP+0x7C,visits)
        self.receipts['connections']=dict(caller_cases=calls,caller_words=44,wrapper_cases=wrapper_cases,wrapper_words=5,direct_calls=2,pointers=0,interior_jumps=0,
            unused_word_loaded_in_delay_slot=True,void_return_ignored=True,SDK_cases=sdk_cases,SDK_words=72,
            full_fifth_word_preserved=True,low_half_consumed=True,SDK_definition_unchanged=True,handle_callback_count_reload=True,
            other_audio_and_collision_services_bounded=True)

    def test_04_literal_fault_prefixes_and_private_frame_alias(self):
        cuts=0
        for c in(guest.Case(count=0),guest.Case(count=1),guest.Case(kind=7,count=1),guest.Case(kind=4,count=1),guest.Case(kind=0,count=1),guest.Case(mutation=63),guest.Case(alias=1,count=1,kind=4),guest.Case(alias=3,count=1,kind=0,bound=0)):
            initial=guest.fixture(c);full=guest.Oracle(self.truth,initial,c);full.run()
            for cut in range(full.all_accesses):
                states=[]
                for body in(self.truth,self.words):
                    m=guest.Oracle(body,initial,c);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    states.append(guest.state(m))
                self.assertEqual(states[0],states[1],(c,cut));cuts+=1
        self.receipts['faults']=dict(executed_cuts=cuts,normalized_literal_low_word_states=True,raw_schedule_not_claimed_literal=True)

    def test_05_native32_typed_ABI_and_effective_semantic_controls(self):
        def run(label,body=None,opt='-O2'):
            p=self.out/(label+'.c');p.write_text(guest.native_harness(body));exe=p.with_suffix('.elf')
            r=subprocess.run([*native_command(opt),'-mstackrealign',str(p.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''));return subprocess.run([str(exe)],timeout=20).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,opt=opt),0)
        b=source.SELECTED
        controls=dict(stub=b[:b.index('{')+1]+'\nreturn;\n}',wrong_transition=b.replace('state ^ 3','state ^ 2'),wrong_class=b.replace('case 2:','case 3:'),
            unsigned_view_coordinate=b.replace('view->x = ((GeneratedCDE80Record *)((u32)D_800D3098 + offset))->origin0;', 'view->x = (u16)((GeneratedCDE80Record *)((u32)D_800D3098 + offset))->origin0;'),
            cached_count=b.replace('    u32 index;','    u32 savedCount = (u32)D_800D3094;\n    u32 index;',1).replace('index < (u32)D_800D3094','index < savedCount'),
            cached_after_stop=b.replace('((GeneratedCDE80Record *)((u32)D_800D3098 + offset))->field20 = 0;', 'record->field20 = 0;',1),
            wrong_timer_mask=b.replace('~255U','~65535U'),skip_shared_tail=b.replace('/* fall through */','break;'),
            exclusive_view_bound=b.replace('viewer <= D_80082FA0','viewer < D_80082FA0'),
            wrong_second_command=b.replace('record->field17, 100,','record->field17, 101,'),
            wrong_gate=b.replace('D_800C35EA == 1','D_800C35EA != 0'),wrong_subtype_exception=b.replace('field17 != 9','field17 != 10'))
        for name,bad in controls.items():self.assertNotEqual(b,bad,name);self.assertNotEqual(run('negative-'+name,bad),0,name)
        self.receipts['native']=dict(cases_per_executable=len(guest.native_cases()),optimizations=3,trapping_UBSan=True,
            SDK_view2464_record52_pointer32=True,typed_audio_u16_s16_s16_s16_u16_ABI=True,
            callback_stream_and_field_digests=True,effective_controls=list(controls),guest_aliases_separate=True)

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
            self.assertEqual(list(struct.unpack('>209I',sections(p.with_suffix('.elf'))['.text'][1])),source.bound_blob(self.q['normal'],self.q['normal_refs'],bindings))
        before,after=self.q['predecessor_elf'].read_bytes(),self.q['qualified_elf'].read_bytes();truth=self.rom[source.ROM:source.ROM+836];self.assertEqual(source.strict_image(before,after,truth),612)
        sym=next(p for p,n,f,s in source.symbol_rows(before)if n==source.FUNCTION)
        for at in(64,source.elf_slot_offset(before,source.ENTRY,836),sym+8,source.elf_slot_offset(before,0x80082B20,4)):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):source.strict_image(before,bytes(bad),truth)
        self.receipts['image']=dict(changed_bytes=612,exclusions=0,independent_links=2,bindings=25,signed_LO16_carries=True,corruption_controls=4,no_metadata_permutation=True)

if __name__=='__main__':unittest.main()
