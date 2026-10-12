"""Exact metrics switch/pool, ordered aliases, O32 homes and linked audit."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_extended_character_metrics_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.check_game_data_layout import audit_layout
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_actor_timer_callbacks_match import symbol_records
from tools.tests.game_animation_timeline_oracle import signed

STACK, OUTPUT = guest.STACK,0x50000
CONSTANTS = tuple(screen.SYMBOLS)
BITS = (0x40466666,0x3F1A5E35,0xBFCCCCCD,0x3E4CCCCD,0x3F39DB23)
CODES = (*range(-2,258),-2147483648,2147483647)
CASES = (
    ((0xA8,0xA9),0x44,(('w',32),('h',18),('s','D_80098AFC'),('m',1))),
    ((0xAA,0xAB,0xAC,0xAD),0x70,(('w',32),('h',27),('s',0x40000000),('m',1),('f','D_80098B00'))),
    ((0xAE,),0xA8,(('w',16),('h',17),('s','D_80098B04'),('m',1))),
    ((0xAF,0xB0),0xD4,(('w',46),('h',16),('s',0x40000000),('m',1))),
    ((0xB6,0xB7,0xB8,0xB9),0x100,(('w',16),('h',12),('s',0x40000000),('m',0))),
    ((0xBA,),0x128,(('m',0),('s','D_80098B08'),('w',55),('h',12))),
    ((0xB1,),0x150,(('w',38),('h',24),('s',0x40000000),('m',1),('f','D_80098B0C'))),
)
DEFAULT = (('w',12),('h',16),('s',0x40000000),('m',0))

# New global references change eight linker hash-chain orders, not symbol meanings.
METADATA_CYCLES = (
    ('D_80098B08','D_80088B20','D_8002BD14','D_800A2358'),
    ('D_8008B0E4','D_8008AD30'),
    ('D_80098B04','D_800A2354'),
    ('D_80098B00','func_15017300','D_80090060','D_800A2350'),
    ('func_150C522C','D_8008AD60'),
    ('D_80098AFC','D_800C3F00','D_80033330'),
    ('D_80098B0C','D_8009006C','D_800A235C'),
    ('D_80086014','D_800D3584'),
)


def reorder_linker_metadata(data):
    records = symbol_records(data)
    for cycle in METADATA_CYCLES:
        group = []
        for name in cycle:
            matches = [record for record in records if record[0] == name]
            assert len(matches) == 1
            group.append(matches[0])
        assert all(b[2]-a[2] == 16 and b[3]-a[3] == len(a[0])+1
            for a,b in zip(group,group[1:]))
        cursor = 0
        for destination,source in zip(group,group[1:]+group[:1]):
            name,symbol,offset,string_offset = source
            assert data[string_offset:string_offset+len(name)+1] == name.encode()+b'\0'
            encoded = name.encode()+b'\0'
            new_name = group[0][1][0]+cursor
            struct.pack_into('>IIIBBH',data,destination[2],new_name,*symbol[1:])
            cursor += len(encoded)
        encoded = b''.join(record[0].encode()+b'\0' for record in group[1:]+group[:1])
        start = group[0][3]
        data[start:start+len(encoded)] = encoded
    return data


def table_targets(entry=screen.ENTRY):
    return [entry+next((offset for codes,offset,ops in CASES if code in codes),0x188)
        for code in range(0xA8,0xBB)]


def fixture(code=0xA8,alias=0,phase=0,entry=screen.ENTRY,table=screen.TABLE,symbols=screen.SYMBOLS):
    memory = {STACK+i:0xA5 for i in range(-128,0x300)}
    memory.update({OUTPUT+i:(i*17+53)&255 for i in range(-16,128)})
    memory.update({i:0xA5 for i in range(0,256)})
    for address in (*BITS,0x40000000,0x3F800000):
        memory.update({address+i:0xA5 for i in range(4)})
    for i,value in enumerate(table_targets(entry)): put(memory,table+i*4,value)
    for name,value in zip(CONSTANTS,BITS): put(memory,symbols[name],value)
    outputs = [OUTPUT+i*4 for i in range(5)]
    if alias == 1: outputs = [OUTPUT]*5
    elif alias == 2: outputs = [OUTPUT,OUTPUT,OUTPUT+4,OUTPUT+4,OUTPUT+8]
    elif 3 <= alias < 8: outputs[4] = symbols[CONSTANTS[alias-3]]
    elif 8 <= alias < 13: outputs[0] = symbols[CONSTANTS[alias-8]]
    elif alias == 13: outputs[0] = STACK+phase+16
    elif alias == 14: outputs[0] = STACK+phase+20
    elif alias == 15: outputs[2] = STACK+phase+16
    elif alias == 16: outputs[3] = STACK+phase+20
    args = (code,*outputs)
    put(memory,STACK+phase+16,outputs[3]);put(memory,STACK+phase+20,outputs[4])
    return memory,args


class Reference:
    def __init__(self,memory,args,phase=0,entry=screen.ENTRY,table=screen.TABLE,symbols=screen.SYMBOLS):
        self.memory,self.events = memory.copy(),[]
        self.args,self.home,self.entry,self.table,self.symbols = args,STACK+phase,entry,table,symbols
    def get(self,address):
        assert all(address+i in self.memory for i in range(4)),('unmapped reference read',address)
        value=read(self.memory,address)
        self.events.append(('R',address,4,value));return value
    def store(self,address,value):
        assert all(address+i in self.memory for i in range(4)),('unmapped reference write',address)
        put(self.memory,address,value)
        self.events.append(('W',address,4,value&0xFFFFFFFF))
    def run(self):
        code,w,h,s,m,f = self.args;code=signed(code)
        if code >= 0xA8: f=self.get(self.home+20)
        if code < 0xA8 or code >= 0x100:
            for address in (s,w,h):self.store(address,0)
            return self
        self.store(f,0x3F800000)
        if code < 0xBB:
            self.get(self.table+(code-0xA8)*4)
        operations=next((ops for codes,offset,ops in CASES if code in codes),DEFAULT)
        addresses=dict(w=w,h=h,s=s,f=f)
        for name,value in operations:
            if name == 'm':address=self.get(self.home+16)
            else:address=addresses[name]
            if isinstance(value,str):value=self.get(self.symbols[value])
            self.store(address,value)
        return self


class MetricsOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,args,entry=screen.ENTRY,phase=0,connected=None):
        super().__init__(words,memory,arguments=args,entry=entry,phase=phase,connected=connected)


class WindowOracle(MetricsOracle):
    def record_call(self,target):
        assert target == screen.ENTRY
        args=self.arguments(6)
        self.calls.append((target,*args));self.events.append(('CALL',target,tuple(args)))


class GameExtendedCharacterMetricsMatchTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-extended-character-metrics-match-test';cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s',metrics_pool='conker/asm/data/23D570.rodata.s',
            symbols='conker/symbol_addrs.us.txt',undefined='conker/undefined_funcs_auto.txt',
            undefined_symbols='conker/undefined_syms_auto.txt',layout='conker/retail_layout.us.txt',
            makefile='conker/Makefile',assembly='conker/asm/6E770.s')
        manifest=cls.out/'baseline.json'
        if not manifest.exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads(manifest.read_text())
        assert cls.baseline['source']=='25ba94b9b2580a6657b42f1d834fe6f7799810e4a2da607635c2cebb44b4db56'
        assert cls.baseline['elf']=='48d60bd24c2c18e51c2d83704b8643dd6bfb8ff3c4db0ba932df4d0543f10f9a'
        assert cls.baseline['guards']=='9b08dabc9ccc24cfa82b40ec626d3f5f73a7521f89d5a118f8e62773ccfea168'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.before=(cls.out/'before-elf').read_bytes();cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>115I',cls.rom,screen.ROM))
        cls.meta,cls.raw,cls.pool=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.old_source=(cls.out/'before-source').read_text()
        cls.asm=(cls.out/'before-assembly').read_text()
        body=cls.asm.split('glabel '+screen.FUNCTION,1)[1].split('endlabel '+screen.FUNCTION,1)[0].replace('jlabel ','')
        original='.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+',@function\n'+\
            screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n'
        # Original jlabels need colons when the macro prelude is intentionally absent.
        original='\n'.join(line+':' if line.strip().startswith('.L') and not line.rstrip().endswith(':') else line
            for line in original.splitlines())+'\n'
        cls.assemble('original',original)
        slot=cls.out/'slot.s';slot.write_text('glabel '+screen.FUNCTION+
            cls.asm.split('glabel '+screen.FUNCTION,1)[1].split('endlabel '+screen.FUNCTION,1)[0]+
            'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('fitted',emit_padded_assembly(cls.out/'selected.o',slot,filename='generated_6E770',
            rodata_symbol=screen.ANCHOR))
        cls.owners=[]
        run=subprocess.run
        def compact(command,*args,**kwargs):
            if str(command[0]).endswith('/cc'):command=list(command)+['-Wo,-loopunroll,0']
            return run(command,*args,**kwargs)
        for stage,source in (('before',cls.old_source),('after',screen.install(cls.old_source))):
            with patch('subprocess.run',side_effect=compact):
                obj,warnings=compile_owner(cls.root,cls.out,source,'owner-'+stage)
            assert not warnings,warnings
            subprocess.run(['python3',str(cls.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((cls.out/('owner-'+stage+'.c')).relative_to(cls.root/'conker')),'--post-process',
                str(obj.relative_to(cls.root/'conker')),'--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=cls.root/'conker',check=True,capture_output=True)
            cls.owners.append(obj)

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def link(self,name,entry=screen.ENTRY,table=screen.TABLE):
        script=self.out/(name+'-%X-%X.ld'%(entry,table));elf=script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } '
            '.rodata 0x%X : SUBALIGN(4) { *(.rodata) } }\n'%(entry,table))
        symbols={key:table+value-screen.TABLE for key,value in screen.SYMBOLS.items()}
        symbols.update({screen.ANCHOR:table,'jtbl_80098AB0':table})
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(self.out/(name+'.o'))],
            check=True,capture_output=True)
        return list(struct.unpack_from('>115I',sections(elf)['.text'][1]))

    @property
    def forms(self):
        if not hasattr(type(self),'_forms'):type(self)._forms=(self.retail,self.raw,self.link('fitted'))
        return type(self)._forms

    def compare(self,code,alias=0,phase=0,entry=screen.ENTRY,table=screen.TABLE,forms=None):
        symbols={key:table+value-screen.TABLE for key,value in screen.SYMBOLS.items()}
        memory,args=fixture(code,alias,phase,entry,table,symbols)
        expected=Reference(memory,args,phase,entry,table,symbols).run()
        models=[MetricsOracle(w,memory,args,entry,phase).run() for w in forms or self.forms]
        for m in models:
            self.assertEqual((m.memory,m.events,m.calls),(expected.memory,expected.events,[]))
        for m in models[1:]:
            self.assertEqual((m.memory,m.events,m.r,m.f),(models[0].memory,models[0].events,models[0].r,models[0].f))
        return models

    def test_01_exact_full_switch_pool_and_ordered_aliases(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],self.meta['pool_bytes']),(115,0,0,80))
        self.assertEqual(self.raw,self.retail);self.assertEqual(self.link('original'),self.retail)
        self.assertEqual(self.forms[-1],self.retail)
        self.assertEqual(self.pool[:76],self.rom[screen.TABLE_ROM:screen.TABLE_ROM+76])
        self.assertEqual(self.pool[76:],b'\x00'*4)
        self.assertEqual(list(struct.unpack('>19I',self.pool[:76])),table_targets())
        reached,cases=set(),0
        for code,alias,phase in itertools.product(CODES,range(13),(0,8)):
            models=self.compare(code,alias,phase);reached.update(models[0].visits);cases+=1
        self.assertEqual(reached,set(range(screen.ENTRY,screen.ENTRY+460,4)))
        self.receipt('semantic',cases=cases,reached115=True,meaningful_pool19_exact_padding4_discarded=True,
            all_complete_memory_events_GPR_FPR_exact=True,signed_gate_all_bytes_limits_and_constant_aliases=True,
            no_frame_guards_or_helper_calls=True)

    def test_02_incoming_home_lifetimes_and_independent_rebases(self):
        cases=0
        for code,alias,phase in itertools.product((0xA8,0xAA,0xAE,0xAF,0xB1,0xBA,0xBB,0x100),range(13,17),(0,8)):
            self.compare(code,alias,phase);cases+=1
        for entry,table in ((0x15207FFC,0x80107FFC),(0x15308004,0x80218004)):
            forms=tuple(self.link(name,entry,table) for name in ('original','selected','fitted'))
            self.assertEqual(forms[0],forms[1]);self.assertEqual(forms[0],forms[2])
            for code,alias,phase in itertools.product((0xA7,0xA8,0xAA,0xAE,0xBA,0xBB,0x100),(0,1,3,8),(0,8)):
                self.compare(code,alias,phase,entry,table,forms);cases+=1
        self.receipt('lifetimes-rebases',cases=cases,links2_table_and_five_constants=True,
            factor_home_cached_mode_home_branch_order=True,all_words_state_and_HI_LO_carries_exact=True,
            incoming_home_aliases_guest_only=True)

    def test_03_all_fired_fault_prefixes_and_invalid_untouched_outputs(self):
        faults=0
        for code,alias,phase in itertools.product((0xA7,0xA8,0xAA,0xAE,0xAF,0xB1,0xB6,0xBA,0xBB,0x100),
                (0,1,3),(0,8)):
            memory,args=fixture(code,alias,phase)
            full=MetricsOracle(self.retail,memory,args,phase=phase).run()
            for fault in range(full.accesses):
                models=[MetricsOracle(w,memory,args,phase=phase) for w in self.forms]
                for m in models:
                    m.fault=fault
                    with self.assertRaises(guest.AccessFault):m.run()
                    self.assertEqual(m.accesses,fault)
                for m in models[1:]:
                    self.assertEqual((m.memory,m.events,m.r,m.f),(models[0].memory,models[0].events,models[0].r,models[0].f))
                faults+=1
        for code in (0xA7,0x100):
            memory,args=fixture(code)
            for w in self.forms:
                m=MetricsOracle(w,memory,args).run()
                self.assertEqual([read(m.memory,OUTPUT+i*4) for i in (3,4)],[read(memory,OUTPUT+i*4) for i in (3,4)])
                self.assertEqual(sum(e[0]=='R' for e in m.events),0 if code<0xA8 else 1)
        self.receipt('faults',fired_triplets=faults,all_public_private_pool_and_constant_accesses=True,
            low_invalid_skips_factor_home_high_invalid_reads_it=True,invalid_mode_factor_untouched=True,
            no_portable_C_fault_or_hardware_claim=True)

    @staticmethod
    def negatives():
        return (
            ('lower-gate',screen.SELECTED.replace('code >= 0xA8','code >= 0xA9'),0xA8,0),
            ('upper-gate',screen.SELECTED.replace('code < 0x100','code < 0x101'),0x100,0),
            ('initial-factor',screen.SELECTED.replace('*factor = 1.0f','*factor = 0.0f'),0xA8,0),
            ('live-constant',screen.SELECTED.replace('*scale = D_80098AFC','*scale = 3.1f'),0xA8,8),
            ('case-order',screen.SELECTED.replace('*mode = 0;\n                *scale = D_80098B08;',
                '*scale = D_80098B08;\n                *mode = 0;'),0xBA,0),
            ('mode-value',screen.SELECTED.replace('*mode = 1','*mode = 2'),0xAA,0),
        )

    def test_04_effective_compiled_controls_and_binding_failure(self):
        for name,body,code,alias in self.negatives():
            if name=='case-order':
                memory,args=fixture(code)
                args=(code,args[1],args[2],args[3],screen.SYMBOLS['D_80098B08'],args[5])
                put(memory,STACK+16,args[4])
            else:memory,args=fixture(code,alias)
            negative_table=0x80100000
            _,words,_=screen.compile_candidate(self.root,self.out,'negative-'+name,body,table=negative_table)
            # The mutated compiler table follows its own changed case placements.
            negative=self.out/('negative-'+name+'-pool.elf')
            pool=sections(negative).get('.rodata',(0,b''))[1]
            memory.update({negative_table+i:v for i,v in enumerate(pool)})
            ref_memory,_=fixture(code,alias)
            if name=='case-order':
                ref_memory=memory.copy()
                for i,v in enumerate(table_targets()):put(ref_memory,screen.TABLE+i*4,v)
            ref=Reference(ref_memory,args).run()
            model=MetricsOracle(words,memory,args).run()
            outputs=[OUTPUT+i for i in range(24)]+[v+i for v in screen.SYMBOLS.values() for i in range(4)]
            self.assertTrue(any(model.memory[a]!=ref.memory[a] for a in outputs),name)
        unbound=self.out/'unbound.ld';unbound.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%screen.ENTRY)
        result=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(unbound),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%v for v in screen.SYMBOLS.items()],'-o',str(self.out/'unbound.elf'),
            str(self.out/'fitted.o')],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertIn(screen.ANCHOR,result.stderr)
        self.receipt('controls',compiled_semantic6=True,live_constant_order_and_bounds_effective=True,
            missing_original_pool_binding_rejected=True)

    def test_05_complete_owner_both_padders_and_original_pool_binding(self):
        def fingerprint(obj,name):
            text,functions,relocs=parse_object(obj);f=functions[name];a,b=f['value'],f['value']+f['size']
            return f['size'],text[a:b],{o-a:r for o,r in relocs.items() if a<=o<b}
        names=set(parse_object(self.owners[0])[1]);self.assertEqual(names,set(parse_object(self.owners[1])[1]))
        for name in names-{screen.FUNCTION}:
            self.assertEqual(fingerprint(self.owners[0],name),fingerprint(self.owners[1],name),name)
        self.assertEqual(fingerprint(self.owners[1],screen.FUNCTION),fingerprint(self.out/'selected.o',screen.FUNCTION))
        routes=[]
        for route in ('pad_c_object.py','pad_generated_object.py'):
            parsed=[]
            for stage,obj in zip(('before','after'),self.owners):
                asm=self.out/(route+'-'+stage+'.s')
                args=[str(obj),str(self.out/'before-layout'),'generated_6E770',str(asm)] if route=='pad_c_object.py' else [
                    str(obj),str(self.root/'conker/asm/6E770.s'),str(asm),'--filename','generated_6E770']
                subprocess.run(['python3',str(self.root/'tools'/route),*args,'--word-patches',str(self.out/'before-guards'),
                    '--rodata-symbol',screen.ANCHOR],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],
                    check=True,capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
                self.assertNotIn('.rodata',sections(asm.with_suffix('.o')))
            start=parsed[1][1][screen.FUNCTION]['value'];expected=bytearray(parsed[0][0])
            expected[start:start+460]=parsed[1][0][start:start+460]
            self.assertEqual(bytes(expected),parsed[1][0])
            self.assertEqual({o:r for o,r in parsed[0][2].items() if not start<=o<start+460},
                {o:r for o,r in parsed[1][2].items() if not start<=o<start+460})
            for name in names-{screen.FUNCTION}:self.assertEqual(parsed[0][1][name],parsed[1][1][name])
            routes.append(parsed[1])
        self.assertEqual(routes[0],routes[1])
        self.receipt('owner',neighbors7=True,all_other_body_extent_relocations_exact=True,
            generated_pool_discarded_existing_table_binding_only=True,actual_no_unroll_GLOBAL_ASM_both_padders=True)

    def test_06_actual_original_callsite_windows(self):
        cases=0
        for start,end,offsets in ((0x15041F0C,0x15041F50,(0x188,0x184,0x108,0x104,0x100)),
                (0x150429C0,0x150429E4,(0x64,0x60,0x5C,0x58,0x54))):
            words=list(struct.unpack_from('>%dI'%((end-start)//4+1),self.rom,start-0x15000000+0x2D4B0))
            for code,phase in itertools.product(range(0xA8,0x100),(0,8)):
                memory,args=fixture(code,phase=phase)
                models=[]
                for body in self.forms:
                    connected={screen.ENTRY+i*4:w for i,w in enumerate(body)}
                    connected[end+4]=0x03C00008;connected[end+8]=0
                    m=WindowOracle(words,memory,(code,0,0,0),start,phase,connected)
                    m.tail=True;m.r[30]=m.before[30]=0xDEAD0000
                    m.r[19]=m.before[19]=code
                    m.run();models.append(m)
                    expected_args=(code,*[STACK+phase+o for o in offsets])
                    self.assertEqual(m.calls,[(screen.ENTRY,*expected_args)])
                    for address in expected_args[1:]:self.assertTrue(address in m.memory)
                for m in models[1:]:
                    self.assertEqual((m.memory,m.events,m.r,m.f),(models[0].memory,models[0].events,models[0].r,models[0].f))
                cases+=1
        self.receipt('caller-windows',cases=cases,two_original_six_arg_call_setups_and_delay_stores=True,
            metrics_actual_no_hooks=True,synthetic_window_exit_not_full_formatter_or_gameplay=True)

    def native_source(self,body):
        return NATIVE+body+NATIVE_MAIN

    def test_07_native32_full_C_and_effective_controls(self):
        source=self.native_source(screen.SELECTED)
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],source,profile),(0,''))
        for name,body,code,alias in self.negatives():
            exit_code,detail=self.run_native('native-negative-'+name,self.native_source(body))
            self.assertEqual(exit_code,1,name);self.assertEqual(len(detail),3,name)
        self.receipt('native',profiles=['O2','O0'],cases_per_profile=4060,
            source_not_pool_or_instruction_projection=True,public_output_global_alias_canaries=True,
            effective_controls6=True,pointer_and_float_bytes4=True,no_64bit_private_home_hardware_claim=True)

    def test_08_literal_source_whole_ELF_binding_and_nine_inputs(self):
        before=(self.out/'before-source').read_text();current=(self.root/screen.SOURCE).read_text();changed=current!=before
        self.assertEqual(current,screen.install(before) if changed else before)
        actual=(self.root/self.paths['elf']).read_bytes();expected=bytearray(self.before)
        start=elf_slot_offset(self.before,screen.ENTRY,460)
        extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12)
        if changed:
            struct.pack_into('>115I',expected,start,*self.retail);struct.pack_into('>I',expected,extent,460)
            expected=reorder_linker_metadata(expected)
        self.assertEqual(actual,bytes(expected))
        for name,path in self.paths.items():
            old=(self.out/('before-'+name)).read_bytes()
            self.assertEqual(hashlib.sha256(old).hexdigest(),self.baseline[name])
            if name not in ('source','elf'):
                expected_input=screen.bind_pool_bytes(old) if changed and name=='makefile' else old
                self.assertEqual((self.root/path).read_bytes(),expected_input,name)
        data=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(data['exact'],data)
        self.receipt('linked',installed=changed,ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            target_bytes=sum(a!=b for a,b in zip(self.before[start:start+460],actual[start:start+460])),
            extent_bytes=sum(a!=b for a,b in zip(self.before[extent:extent+4],actual[extent:extent+4])),
            symbol_and_string_bytes=207 if changed else 0,eight_exact_metadata_cycles=METADATA_CYCLES,
            original_pool_and_all_other_data_exact=True,nine_inputs_including_guards_progress_exact=True,
            makefile_only_existing_pool_binding=True,literal_exact_measured_metadata_permutations_only=True,protected_data=data)

    def test_09_effective_stale_and_integrity_controls(self):
        for source in (screen.install(self.old_source),self.old_source+'\n'+screen.ORIGINAL):
            with self.assertRaises(AssertionError):screen.install(source)
        with self.assertRaises(AssertionError):screen.bind_pool(screen.bind_pool((self.out/'before-makefile').read_text()))
        rt,rb=Path.read_text,Path.read_bytes
        source=self.root/screen.SOURCE;current=source.read_text()
        with patch.object(Path,'read_text',lambda p,*a,**k:current+'\n' if p==source else rt(p,*a,**k)):
            with self.assertRaises(AssertionError):self.test_08_literal_source_whole_ELF_binding_and_nine_inputs()
        elf=self.root/self.paths['elf'];actual=elf.read_bytes();start=elf_slot_offset(actual,screen.ENTRY,460)
        extent=installed.symbol_size_offset(actual,screen.FUNCTION,screen.ENTRY)
        metadata=next(record for record in symbol_records(actual) if record[0]=='D_80098B08')
        for offset in (start+4,start+460,extent+3,elf_slot_offset(actual,screen.TABLE,76)+4,
                metadata[2]+4,metadata[3]+2):
            wrong=bytearray(actual);wrong[offset]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(wrong) if p==elf else rb(p)):
                with self.assertRaises(AssertionError):self.test_08_literal_source_whole_ELF_binding_and_nine_inputs()
        makefile=self.root/self.paths['makefile'];body=makefile.read_bytes()
        with patch.object(Path,'read_bytes',lambda p:body+b'\n' if p==makefile else rb(p)):
            with self.assertRaises(AssertionError):self.test_08_literal_source_whole_ELF_binding_and_nine_inputs()
        self.receipt('integrity-controls',source1_ELF6_including_symbol_and_string_binding1_stale_source2_duplicate_binding1=True,all_effective=True)


NATIVE=r'''
typedef int s32;typedef unsigned int u32;typedef float f32;
static f32 D_80098AFC,D_80098B00,D_80098B04,D_80098B08,D_80098B0C;
static u32 cells[16],wanted[16],globals[5],wantGlobals[5];
static s32 *w,*h,*m;static f32 *s,*f;static u32 *ww,*wh,*wm,*ws,*wf;
static u32 bits(f32 v){union{f32 f;u32 u;}x;x.f=v;return x.u;}
static f32 value(u32 v){union{f32 f;u32 u;}x;x.u=v;return x.f;}
static int report(u32 a,u32 b,u32 c){u32 data[3]={a,b,c};int r;
    __asm__ volatile("int $0x80":"=a"(r):"a"(4),"b"(2),"c"(data),"d"(12):"memory");return 1;}
static void reset(int alias){
    static const u32 initial[5]={0x40466666,0x3F1A5E35,0xBFCCCCCD,0x3E4CCCCD,0x3F39DB23};
    f32 *gs[5]={&D_80098AFC,&D_80098B00,&D_80098B04,&D_80098B08,&D_80098B0C};
    for(int i=0;i<16;i++)cells[i]=wanted[i]=0xA5123400u+(u32)i;
    for(int i=0;i<5;i++){*gs[i]=value(initial[i]);globals[i]=wantGlobals[i]=initial[i];}
    w=(s32 *)(cells+1);h=(s32 *)(cells+2);s=(f32 *)(cells+3);m=(s32 *)(cells+4);f=(f32 *)(cells+5);
    ww=wanted+1;wh=wanted+2;ws=wanted+3;wm=wanted+4;wf=wanted+5;
    if(alias==1){h=(s32 *)w;s=(f32 *)w;m=w;f=(f32 *)w;wh=ws=wm=wf=ww;}
    if(alias==2){h=w;m=(s32 *)s;wh=ww;wm=ws;}
    if(alias>=3&&alias<8){f=gs[alias-3];wf=wantGlobals+alias-3;}
    if(alias>=8&&alias<13){w=(s32 *)gs[alias-8];ww=wantGlobals+alias-8;}
    if(alias==13){m=(s32 *)&D_80098B08;wm=wantGlobals+3;}
}
static void reference(s32 code){
    if(code<0xA8||code>=0x100){*ws=0;*ww=0;*wh=0;return;}
    *wf=0x3F800000;
    switch(code){
    case 0xA8:case 0xA9:*ww=32;*wh=18;*ws=wantGlobals[0];*wm=1;return;
    case 0xAA:case 0xAB:case 0xAC:case 0xAD:*ww=32;*wh=27;*ws=0x40000000;*wm=1;*wf=wantGlobals[1];return;
    case 0xAE:*ww=16;*wh=17;*ws=wantGlobals[2];*wm=1;return;
    case 0xAF:case 0xB0:*ww=46;*wh=16;*ws=0x40000000;*wm=1;return;
    case 0xB6:case 0xB7:case 0xB8:case 0xB9:*ww=16;*wh=12;*ws=0x40000000;*wm=0;return;
    case 0xBA:*wm=0;*ws=wantGlobals[3];*ww=55;*wh=12;return;
    case 0xB1:*ww=38;*wh=24;*ws=0x40000000;*wm=1;*wf=wantGlobals[4];return;
    default:*ww=12;*wh=16;*ws=0x40000000;*wm=0;return;
    }
}
'''
NATIVE_MAIN=r'''
static int run(void){u32 cases=0;
    if(sizeof(void *)!=4||sizeof(s32)!=4||sizeof(f32)!=4)return 2;
    for(s32 code=-16;code<=271;code++)for(int alias=0;alias<14;alias++,cases++){
        reset(alias);reference(code);func_150415E0(code,w,h,s,m,f);
        for(u32 i=0;i<16;i++)if(cells[i]!=wanted[i])return report(cases,0,i);
        u32 now[5]={bits(D_80098AFC),bits(D_80098B00),bits(D_80098B04),bits(D_80098B08),bits(D_80098B0C)};
        for(u32 i=0;i<5;i++)if(now[i]!=wantGlobals[i])return report(cases,1,i);
    }
    for(u32 j=0;j<2;j++)for(int alias=0;alias<14;alias++,cases++){
        s32 code=j?2147483647:(-2147483647-1);reset(alias);reference(code);func_150415E0(code,w,h,s,m,f);
        for(u32 i=0;i<16;i++)if(cells[i]!=wanted[i])return report(cases,2,i);
        u32 now[5]={bits(D_80098AFC),bits(D_80098B00),bits(D_80098B04),bits(D_80098B08),bits(D_80098B0C)};
        for(u32 i=0;i<5;i++)if(now[i]!=wantGlobals[i])return report(cases,3,i);
    }
    return cases==4060?0:3;
}
void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':
    unittest.main()
