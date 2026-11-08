"""Record updater ABI, ordered memory effects, caller and complete-image gates."""
import json
import struct
import subprocess
import unittest
from pathlib import Path
from tools.experiments import game_record_parameter_150a2940_match as source
from tools.tests import game_record_parameter_150a2940_oracle as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode, WindowBoundary
from tools.experiments.game_remaining_donor_candidates import sections


def symbols():return {name:int(name.split('_')[1],16) for rows in source.BINDINGS.values() for _,name in rows}


class RecordParameterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=source.ROOT;cls.out=cls.root/source.BUILD;cls.q=source.prepare(cls.root)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.elf=cls.q['qualified_elf'].read_bytes()
        cls.truth=list(struct.unpack_from('>34I',cls.rom,source.ROM))
        cls.words=source.bound_blob(cls.q['normal'],cls.q['normal_refs'],symbols())
        cls.raw=source.bound_blob(cls.q['raw'],cls.q['refs'],symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')

    def test_01_owner_scope_and_fail_closed_schedule(self):
        q=self.q['report']
        self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors']),(34,0,2,27,27))
        self.assertEqual((q['functions'],q['exclusions'],q['diagnostics']),(6053,0,0))
        self.assertEqual(self.words,self.truth)
        self.assertEqual([i for i,(a,b) in enumerate(zip(self.raw,self.truth)) if a!=b],[11,12])
        self.assertEqual(self.raw[11:13],self.truth[11:13][::-1])
        self.assertEqual(self.q['normal_refs'][44],self.q['refs'][48]);self.assertNotIn(48,self.q['normal_refs'])
        for offset in source.BINDINGS:
            refs=dict(self.q['refs']);refs[offset]=[('R_MIPS_26','wrong')]
            with self.assertRaises(ValueError):source.normalize(self.q['raw'],refs)
        for offset in range(0,136,4):
            bad=bytearray(self.q['raw']);bad[offset+3]^=1
            with self.assertRaises(ValueError):source.normalize(bytes(bad),self.q['refs'])
        before=(self.out/'predecessor-guards.csv').read_bytes();after=(self.out/'qualified-guards.csv').read_bytes()
        self.assertTrue(after.startswith(before));self.assertEqual(len(after[len(before):].splitlines()),2)
        with self.assertRaises(ValueError):source.guard_manifest(before+b'\n',self.q['raw'],self.q['refs'])
        changes=source.recovered_metadata(self.out)
        self.assertEqual(changes[source.LAYOUT].count('game,generated_CDE80,func_150A29C8,0x150A29C8,0x150A2AEC'),1)
        self.assertNotIn('func_150A29C8 = ',changes[source.AUTO])
        prior=(self.out/'frozen/conker/progress.csv').read_text()
        line='us,game,generated_CDE80,func_150A2940,352987456,428,c'
        recovered='us,game,generated_CDE80,func_150A2940,352987456,136,c\nus,game,generated_CDE80,func_150A29C8,352987592,292,c'
        self.assertEqual(prior.count(line),1)
        proposed=prior.replace(line,recovered)
        source.progress_scope(prior,proposed)
        with self.assertRaises(ValueError):source.progress_scope(prior,proposed.replace(',352987592,292,c',',352987592,288,c'))
        with self.assertRaises(ValueError):source.progress_scope(prior,proposed+recovered+'\n')
        self.receipts['scope']=dict(words=34,raw_matching_words=32,guards=2,frame=0,bindings=6,neighbors=27,labels=31,
            raw_and_padded_alloc_pools_fixed=True,guard_prefix_fixed=True,raw_corruption_controls=34,binding_controls=6,recovered_placeholder_boundary=True,progress_corruptions=2)

    def test_02_ordered_model_full_width_sentinels_and_aliases(self):
        visited=set();count=0
        for case in guest.cases():
            initial=guest.fixture(case);expected=guest.reference(initial,case);machines=[]
            for body in (self.truth,self.words,self.raw):
                m=guest.Oracle(body,initial,case);registers,floats=m.r[:],m.f[:];m.run()
                self.assertEqual(m.memory,expected,case);self.assertEqual(m.calls,[])
                self.assertEqual(m.r[16:24],registers[16:24]);self.assertEqual(m.r[28:32],registers[28:32]);self.assertEqual(m.f[20:],floats[20:])
                machines.append(m)
            self.assertEqual(guest.state(machines[0]),guest.state(machines[1]))
            self.assertEqual(guest.state(machines[0]),guest.state(machines[2]))
            visited.update(machines[0].visits);count+=1
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+136,4))-visited,set())
        self.receipts['model']=dict(cases=count,all_words_reached=34,full_s32_sentinels=True,unsigned_count=True,low12_mask=True,
            ordered_word_byte_clear=True,pointer_reloads_after_alias_stores=True,raw_and_normalized_literal_state_equal=True,
            void_return=True,arbitrary_register_V0_not_a_result=True)

    def test_03_retail_caller_window_and_pointer_census(self):
        jal=0xC000000|(source.ENTRY>>2&0x3FFFFFF)
        sites=[p for p in range(0x2D4B0,0x24D500,4) if struct.unpack_from('>I',self.rom,p)[0]==jal]
        self.assertEqual(sites,[0xCD8C8])
        pointers=[p for p in range(0,len(self.rom)-3,4) if source.ENTRY<=struct.unpack_from('>I',self.rom,p)[0]<source.ENTRY+136]
        self.assertEqual(pointers,[])
        entry,end=0x150A0410,0x150A04C4;window=struct.unpack_from('>6I',self.rom,0xCD8C0)
        code=dict(zip(range(source.ENTRY,source.ENTRY+136,4),self.words));checks=0
        for case in (guest.Case(),guest.Case(value=-1),guest.Case(kind=-1),guest.Case(count=0),guest.Case(identity=0xFFFFF003)):
            initial=guest.fixture(case);m=guest.Oracle(window,initial,case,entry=entry,connected=code)
            m.r[16],m.r[17]=guest.PACKET,guest.u32(case.identity);m.code=WindowCode(m.code,m);m.code.ends=(end,)
            with self.assertRaises(WindowBoundary):m.run()
            self.assertEqual(m.memory,guest.reference(initial,case));self.assertEqual(m.calls,[(source.ENTRY,tuple(map(guest.u32,(case.identity,case.value,case.kind))))])
            self.assertEqual(m.r[2],1);self.assertEqual(m.r[29],guest.STACK);checks+=1
        self.receipts['caller']=dict(direct_calls=1,entry_or_interior_pointers=0,original_window_words=6,connected_cases=checks,
            full_width_argument_loads=True,ignored_updater_return=True,caller_result_one=True,complete_switch_or_gameplay_not_qualified=True)

    def test_04_all_executed_memory_fault_prefixes(self):
        checks=0
        for case in (guest.Case(),guest.Case(value=-1,kind=-1),guest.Case(count=0),guest.Case(value=guest.ALT,alias=1),guest.Case(value=-1,kind=0xA0,alias=2)):
            initial=guest.fixture(case);full=guest.Oracle(self.truth,initial,case);full.run()
            for cut in range(full.all_accesses):
                states=[]
                for body in (self.truth,self.words,self.raw):
                    m=guest.Oracle(body,initial,case);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    states.append(guest.state(m))
                self.assertEqual(states[0],states[1],(case,cut));self.assertEqual(states[0],states[2],(case,cut));checks+=1
        self.receipts['fault_prefixes']=dict(executed_cuts=checks,all_literal_low_word_state=True,raw_schedule_qualified=True,portable_C_fault_semantics_not_claimed=True)

    def test_05_native32_SDK_layout_and_effective_negative_controls(self):
        def run(label,body=None,opt='-O2'):
            p=self.out/(label+'.c');p.write_text(guest.native_harness(body));exe=p.with_suffix('.elf')
            result=subprocess.run([*native_command(opt),'-mstackrealign',str(p.relative_to(self.root)),'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''))
            return subprocess.run([str(exe)],timeout=20).returncode
        for opt in ('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,opt=opt),0)
        body=source.SELECTED
        negatives=dict(stub=body[:body.index('{')+1]+'\nreturn;\n}',mask=body.replace('&= 0xFFF','&= 0xFFE'),
            bound=body.replace('identity < (u32)D_800D3094','identity <= (u32)D_800D3094'),
            byte_sentinel=body.replace('kind != -1','(u8)kind != 0xFF'),
            lost_word=body.replace('.field18 = value','.field18 = (u8)value'),
            lost_clear=body.replace('.field1C = 0','.field1C = 1'),
            swapped_fields=body.replace('.field18 = value','.field1C = value'))
        for label,bad in negatives.items():self.assertNotEqual(body,bad);self.assertNotEqual(run('negative-'+label,bad),0,label)
        self.receipts['native']=dict(cases_per_executable=len(guest.native_cases()),optimizations=3,SDK_record52_pointer32=True,
            trapping_UBSan=True,effective_negatives=list(negatives),valid_arrays_only=True,guest_aliases_not_portable_C_claims=True)

    def test_06_independent_GNU_relocations_and_full_image_controls(self):
        original=symbols();moved={n:0x81238000+i*0x10000 for i,n in enumerate(original)}
        for i,(entry,bindings) in enumerate(((source.ENTRY,original),(0x17407F50,moved))):
            lines=['.set noreorder','.set noat','.text','.globl '+source.FUNCTION,source.FUNCTION+':']
            for j,(word,) in enumerate(struct.iter_unpack('>I',self.q['normal'])):
                refs=self.q['normal_refs'].get(j*4,[])
                if not refs:lines.append('.word 0x%08X'%word)
                else:
                    kind,name=refs[0];rt,rs=word>>16&31,word>>21&31
                    if kind=='R_MIPS_HI16':line='lui $%d, %%hi(%s)'%(rt,name)
                    elif word>>26==35:line='lw $%d, %%lo(%s)($%d)'%(rt,name,rs)
                    else:line='addiu $%d, $%d, %%lo(%s)'%(rt,rs,name)
                    lines.append(line)
            p=self.out/('rebase-'+str(i));p.with_suffix('.s').write_text('\n'.join(lines)+'\n')
            p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-no-pad-sections','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v) for n,v in bindings.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            self.assertEqual(list(struct.unpack('>34I',sections(p.with_suffix('.elf'))['.text'][1])),source.bound_blob(self.q['normal'],self.q['normal_refs'],bindings))
        before,after=self.q['predecessor_elf'].read_bytes(),self.q['qualified_elf'].read_bytes();truth=self.rom[source.ROM:source.ROM+136]
        changed=source.strict_image(before,after,truth);self.assertEqual(changed,self.q['report']['strict_changed_bytes'])
        sym=next(p for p,n,f,s in source.symbol_rows(before) if n==source.FUNCTION)
        neighbor=next(p for p,n,f,s in source.symbol_rows(before) if n==source.NEIGHBOR)
        for offset in (64,source.elf_slot_offset(before,source.ENTRY,136),sym+8,neighbor+14,source.elf_slot_offset(before,0x80082B20,4)):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):source.strict_image(before,bytes(bad),truth)
        self.receipts['image']=dict(changed_bytes=changed,exclusions=0,independent_links=2,signed_LO_carries=True,
            corruption_controls=5,named_definitions_fixed_except_size=True,protected_data_bytes=189088,protected_owners=720)


    def test_07_durable_symbol_actual_Splat_parser_writer(self):
        source.recovered_metadata(self.out)
        script = "\nimport sys\nfrom pathlib import Path\nfrom types import SimpleNamespace\nfrom intervaltree import IntervalTree\nroot,out,toolrepo=map(Path,sys.argv[1:])\nsys.path.insert(0,str(toolrepo/'n64splat/src'))\nfrom splat.util import symbols,options\nfrom splat.scripts import split\nsource=out/'qualified-symbol-addrs.us.txt';text=source.read_text()\nline='func_150A29C8 = 0x150A29C8; // type:func defined:true'\nfor defined in (True,False):\n    symbols.all_symbols=[];symbols.all_symbols_dict={};symbols.all_symbols_ranges=IntervalTree()\n    lines=text.splitlines() if defined else text.replace(line,line.replace('defined:true','defined:false')).splitlines()\n    symbols.handle_sym_addrs(source,lines,[])\n    matches=[s for s in symbols.all_symbols if s.name=='func_150A29C8']\n    assert len(matches)==1\n    target=matches[0];target.referenced=True\n    assert (target.vram_start,target.type,target.defined)==(0x150A29C8,'func',defined)\n    symbols.add_symbol(symbols.Symbol(0x15500000,given_name='unresolved_canary',type='func',referenced=True))\n    dest=out/('Splat-defined-%s.txt'%defined)\n    options.opts=SimpleNamespace(create_undefined_funcs_auto=True,undefined_funcs_auto_path=dest)\n    split.write_undefined_funcs_auto()\n    expected=('' if defined else 'func_150A29C8 = 0x150A29C8;\\n')+'unresolved_canary = 0x15500000;\\n'\n    assert dest.read_text()==expected\nprint('actual parser/writer and missing-defined negative passed')\n"
        toolrepo=Path(source.pad_generated_object.__file__).resolve().parent
        result=subprocess.run(['python3','-c',script,str(self.root),str(self.out),str(toolrepo)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        (self.out/'actual-Splat.log').write_text(result.stdout+result.stderr)
        self.assertIn('missing-defined negative passed',result.stdout)
        self.receipts['durable_boundary']=dict(actual_Splat_parser_writer=True,provider_copy=str(toolrepo),
            files={str(toolrepo/n):source.sha((toolrepo/n).read_bytes()) for n in ('n64splat/src/splat/scripts/split.py','n64splat/src/splat/util/symbols.py','n64splat/src/splat/util/options.py')},defined_canary_suppressed=True,
            undefined_canary_retained=True,missing_defined_negative_effective=True,full_extraction_not_run=True)


if __name__=='__main__':unittest.main()
