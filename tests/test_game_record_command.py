"""Record flag/value semantics, two real dispatch paths and closed image gates."""

import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_record_command as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT = Path(__file__).resolve().parents[2]
SYMBOLS = dict(D_800D3010=0x800D3010, D_800D3014=0x800D3014)
PACKET, TABLE, COUNT = 0x800D2F60, 0x800884D4, 0x800D3840
INPUT = 0x30000
COMMANDS = (0, 1, 2, 3, 0x100, 0x80000000, 0xFFFFFFFF)
VALUES = (0, 1, 0x80000000, 0x7FFFFFFF, 0xFFFFFFFF, 0x12345678)


def fixture(byte=0xA5, index=0, anchors=None):
    s = anchors or SYMBOLS
    m = {STACK+i:(i*17+0xA5)&255 for i in range(-0x200,0x100)}
    for base, length in ((s['D_800D3010']-16,160),(s['D_800D3014']-16,160),
                         (INPUT-16,64),(PACKET-16,96),(TABLE,64),(COUNT-16,36)):
        for i in range(length):
            m.setdefault(base+i,(i*13+0xA5)&255)
    m[(s['D_800D3010']+index*12)&0xFFFFFFFF] = byte
    put(m,INPUT+8,0x87654321)
    put(m,TABLE+40,source.ENTRY)
    put(m,COUNT,0x12345678)
    return m


def reference(memory, args, anchors=None):
    s = anchors or SYMBOLS
    m = dict(memory)
    index, command, payload = args
    if command in (0,1):
        at = (s['D_800D3010']+index*12)&0xFFFFFFFF
        m[at] = m[at]|0x40 if command==0 else m[at]&0xBF
    elif command==2:
        value = read(m,(payload+8)&0xFFFFFFFF)
        put(m,(s['D_800D3014']+index*12)&0xFFFFFFFF,value)
    return m, int(command in (0,1,2))


def public(m):
    return {a:v for a,v in m.items() if not STACK-0x200<=a<STACK+0x100}


class RecordOracle(TimingOracle):
    def __init__(self, words, memory, args, phase=0, entry=source.ENTRY, connected=None, script=False):
        self.trace = []
        super().__init__(words,memory,phase=phase,entry=entry,arguments=args,connected=connected)
        if script:
            # This script window uses S7 as link scratch, not the standard C ABI.
            self.before[23] = self.before[31]

    def get(self, address, size):
        value = super().get(address,size)
        if self.own_instruction:
            self.trace.append(('R',address,size,value))
        return value

    def put(self, address, value, size):
        if self.recording and self.own_instruction:
            assert all(address+i in self.memory for i in range(size)),('unmapped store',address,size)
        super().put(address,value,size)
        if self.recording and self.own_instruction:
            self.trace.append(('W',address,size,value&((1<<(size*8))-1)))

    def record_call(self, target):
        assert target==source.ENTRY,hex(target)
        args = tuple(self.r[4:7])
        self.calls.append((target,args))
        self.events.append(('CALL',target,args))

    def hook(self, target):
        raise AssertionError('Unconnected record command callback')


def native_harness(body):
    body = body.replace('    extern u8 D_800D3014[];\n','')
    return """typedef unsigned int u32;typedef int s32;typedef unsigned char u8;
typedef struct{u8 status,pad1[3];s32 value,unk8;}GeneratedCD5A0Record;
typedef struct{u32 before[4];GeneratedCD5A0Record records[10];s32 payload[3];u32 after[4];}State;
typedef char Width[(sizeof(void*)==4&&sizeof(GeneratedCD5A0Record)==12)?1:-1];
static State state,expected;
#define D_800D3010 state.records
#define D_800D3014 ((u8*)&state.records[0].value)
""" + body + """
static int run(void){u32 byte,index,k,n,j,ret,want;u8 *a=(u8*)&state,*b=(u8*)&expected;
 const u32 commands[]={0,1,2,3,256,0x80000000u,0xFFFFFFFFu};
 const u32 values[]={0,1,0x80000000u,0x7FFFFFFFu,0xFFFFFFFFu,0x12345678u};
 for(byte=0;byte<256;byte++)for(index=0;index<10;index++)for(k=0;k<7;k++)for(n=0;n<6;n++){
  for(j=0;j<sizeof(State);j++)a[j]=(u8)(j*13+0xA5);
  state.records[index].status=(u8)byte;state.payload[0]=123;state.payload[1]=456;state.payload[2]=(s32)values[n];
  for(j=0;j<sizeof(State);j++)b[j]=a[j];
  if(commands[k]==0)expected.records[index].status|=0x40;
  else if(commands[k]==1)expected.records[index].status&=0xBF;
  else if(commands[k]==2)expected.records[index].value=state.payload[2];
  want=commands[k]<3;
  ret=func_150A02D0(index,(s32)commands[k],commands[k]==2?state.payload:(const s32*)0);
  if(ret!=want)return 23;
  for(j=0;j<sizeof(State);j++)if(a[j]!=b[j])return 23;
 }return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
"""


class RecordCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = ROOT/source.BUILD
        cls.installed = source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:
            source.audit(ROOT,cls.out)
        else:
            source.qualify(ROOT,cls.out)
            source.make_shadow(ROOT,cls.out)
            source.predict(ROOT,cls.out)
        cls.values = source.snapshot(cls.out)
        cls.rom = cls.values['conker/conker.us.bin']
        cls.obj,diagnostics = source.compile_owner(ROOT,cls.out,
            '#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diagnostics:
            raise ValueError(diagnostics)
        data,fs = source.link_owner(ROOT,cls.out,cls.obj,source.OWNER)
        cls.words = list(struct.unpack_from('>41I',data,fs[source.FUNCTION]['value']))
        cls.truth = list(struct.unpack_from('>41I',cls.rom,source.ROM))
        cls.receipt = dict(installed=cls.installed)

    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('record command qualification:',cls.receipt)

    def compare(self, memory, args, phase=0, anchors=None, images=None, entry=source.ENTRY):
        expected,result = reference(memory,args,anchors)
        models = [RecordOracle(code,memory,args,phase,entry).run() for code in images or (self.truth,self.words)]
        for m in models:
            self.assertEqual(m.memory,expected)
            self.assertEqual(m.r[2],result)
            self.assertFalse(m.calls)
        self.assertEqual(complete(models[0]),complete(models[1]))
        self.assertEqual(models[0].trace,models[1].trace)
        return models

    def test_01_direct_extent_GNU_bindings_owner_Make_and_old_stub(self):
        self.assertEqual(self.words,self.truth)
        raw,bindings = source.payload(self.obj)
        self.assertEqual((len(raw),source.digest(raw)),(164,source.RAW_SHA))
        self.assertEqual(bindings,{44:[('R_MIPS_HI16','D_800D3010')],48:[('R_MIPS_LO16','D_800D3010')],
            84:[('R_MIPS_HI16','D_800D3010')],88:[('R_MIPS_LO16','D_800D3010')],
            136:[('R_MIPS_HI16','D_800D3014')],152:[('R_MIPS_LO16','D_800D3014')]})
        self.assertEqual(source.payload(source.original(ROOT,self.out)),(raw,bindings))
        self.assertFalse(any(w>>26==9 and w>>21&31==29 and w>>16&31==29 for w in self.words))
        q=json.loads((self.out/'qualification.json').read_text())
        self.assertEqual((q['preserved_neighbors'],q['new_guards']),(4,0))
        self.assertEqual(json.loads((self.out/'make-shadow.json').read_text())['actual_Make_commands'],3)
        old=self.values['conker/build/conker.us.elf']
        at=source.elf_slot_offset(old,source.ENTRY,164)
        m=fixture(0)
        model=RecordOracle(struct.unpack_from('>41I',old,at),m,(0,0,0)).run()
        self.assertNotEqual((model.memory,model.r[2]),reference(m,(0,0,0)))
        self.receipt.update(words=41,frame=0,bindings=6,new_guards=0,neighbors=4,actual_Make_commands=3)

    def test_02_all_flag_bytes_fullword_commands_values_aliases_and_accesses(self):
        visits=set();count=0
        for byte,index,command,phase in itertools.product(range(256),(0,9),COMMANDS,(0,8)):
            m=fixture(byte,index)
            args=(index,command,INPUT if command==2 else 0)
            models=self.compare(m,args,phase)
            visits.update(models[0].visits);count+=1
            self.assertEqual([(r[0],r[1],r[2])for r in models[0].trace],
                [('R',SYMBOLS['D_800D3010']+index*12,1),('W',SYMBOLS['D_800D3010']+index*12,1)]
                if command in (0,1) else [('R',INPUT+8,4),('W',SYMBOLS['D_800D3014']+index*12,4)]
                if command==2 else [])
        aliases=0
        for index,value,offset,phase in itertools.product((0,1,9),VALUES,(-8,-4,0,4,8),(0,8)):
            m=fixture(index=index);payload=SYMBOLS['D_800D3014']+index*12+offset
            put(m,payload+8,value)
            self.compare(m,(index,2,payload),phase);aliases+=1
        # Guest-only modular address arithmetic, not portable invalid C pointers.
        wraps=0
        for index,command in itertools.product((0x40000000,0x80000000,0xC0000000),COMMANDS):
            self.compare(fixture(),(index,command,INPUT));wraps+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+164,4)))
        self.receipt.update(flag_command_phases=count,guest_alias_phases=aliases,guest_wrap_cases=wraps,
            all41_words_visited=True,exact_access_order=True,NULL_untouched_for_noncopy=True)

    def native(self, body, label, opt='-O2'):
        path=self.out/(label+opt+'.c');exe=path.with_suffix('.elf')
        path.write_text(native_harness(body))
        p=subprocess.run(['gcc','-m32','-std=c99',opt,'-fno-pie','-no-pie','-nostdlib',
            '-fno-stack-protector','-fno-builtin','-fsanitize=undefined','-fsanitize-undefined-trap-on-error',
            '-Werror=implicit-function-declaration','-Wl,-e,_start',str(path),'-o',str(exe)],
            capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        return subprocess.run([str(exe)],capture_output=True).returncode

    def test_03_native32_typed_fences_and_effective_wrong_C(self):
        b=source.SELECTED
        for opt in ('-O0','-O2','-O3'):
            self.assertEqual(self.native(b,'native',opt),0)
        controls={
            'wrong-set':b.replace('| 0x40','| 0x20'),
            'clobber-set':b.replace('(D_800D3010[index].status & ~0x40) | 0x40','0x40'),
            'wrong-clear':b.replace('status &= ~0x40','status &= ~0x20'),
            'wrong-payload':b.replace('payload[2]','payload[1]'),
            'wrong-stride':b.replace('index * 12','index * 8'),
            'byte-copy':b.replace('*(s32 *)(D_800D3014 + index * 12)','*(u8 *)(D_800D3014 + index * 12)'),
            'handled-zero':b.replace('return 1;','return 0;'),
            'default-one':b.replace('    return 0;','    return 1;'),
        }
        for label,body in controls.items():
            self.assertNotEqual(body,b)
            self.assertEqual(self.native(body,label),23,label)
        self.receipt.update(native_optimizations=3,native_cases_per_run=256*10*7*6,
            native_wrong_C_rejected=len(controls),trap_UBSan=True,native_invalid_pointers_or_aliases_claimed=False)

    def test_04_complete92word_variadic_caller_and_result_forwarding(self):
        words=list(struct.unpack_from('>92I',self.rom,0xC9460))
        count=0;visits=set()
        for n,index,command,phase in itertools.product((-1,0,1,2,3,4,5,7,8),(0,9),COMMANDS,(0,8)):
            m=fixture(index=index)
            values=[0x81020304+i*0x01020304 for i in range(8)]
            for i,v in enumerate(values[1:]):
                put(m,STACK+phase+16+i*4,v)
            args=(n&0xFFFFFFFF,0xAB000000|0xB000|index,command,values[0])
            expected=dict(m);put(expected,PACKET,index);put(expected,PACKET+4,command)
            for i in range(max(0,n)):
                put(expected,PACKET+8+i*4,values[i])
            expected,result=reference(expected,(index,command,PACKET))
            models=[]
            for code in (self.truth,self.words):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+164,4),code))
                model=RecordOracle(words,m,args,phase,0x1509BFB0,connected).run()
                self.assertEqual(public(model.memory),public(expected))
                self.assertEqual(model.r[2],result)
                self.assertEqual(model.calls,[(source.ENTRY,(index,command,PACKET))])
                self.assertEqual(read(model.memory,COUNT),0x12345678)
                models.append(model);visits.update(model.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(0x1509BFB0,0x1509C120,4))<=visits)
        self.receipt.update(complete_caller_words=92,variadic_caller_phases=count,all92_caller_words_visited=True,
            remainder_and_unrolled_copy=True,count_global_restored=True,result_forwarded=True,other_callback_slots_claimed=False)

    def test_05_script26word_window_selector_zero_and_S7_link_scratch(self):
        words=list(struct.unpack_from('>26I',self.rom,0xDB5DC))
        count=0;visits=set()
        for index,command,selector,phase in itertools.product((0,9),COMMANDS,(0,11),(0,8)):
            m=fixture(index=index)
            put(m,INPUT,(0x40000000|selector<<12|index));put(m,INPUT+4,command)
            expected,result=reference(m,(0x40000000|index,command,INPUT)) if selector else (m,0)
            models=[]
            for code in (self.truth,self.words):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+164,4),code))
                model=RecordOracle(words,m,(INPUT,),phase,0x150AE12C,connected,script=True).run()
                self.assertEqual(public(model.memory),public(expected));self.assertEqual(model.r[2],result)
                self.assertEqual(model.r[23],0xDEAD0000)
                self.assertEqual(model.calls,[(source.ENTRY,(0x40000000|index,command,INPUT))] if selector else [])
                models.append(model);visits.update(model.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(0x150AE12C,0x150AE194,4))<=visits)
        pointer=struct.pack('>I',source.ENTRY)
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==pointer],[0x22CFBC])
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF))
        self.assertFalse(any(self.rom[i:i+4]==jal for i in range(0,len(self.rom),4)))
        self.receipt.update(script_window_words=26,script_phases=count,all26_window_words_visited=True,
            selector_zero_bypass=True,high_index_bits_retained=True,S7_nonstandard_link_scratch=True,
            full_script_parent_or_hardware_claimed=False)

    def test_06_independent_GNU_rebases_and_signed_low_carries(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        original=source.original(ROOT,self.out);count=0
        for i in range(3):
            anchors=dict(D_800D3010=0x80107FFC+i*0x10000,D_800D3014=0x80208000+i*0x10000)
            entry=0x1700FFFC+i*0x10000;images=[]
            for label,obj in (('original',original),('C',self.obj)):
                text,fs,rs=source.parse_object(obj)
                assembly,unknown=emit_function(text,fs[source.FUNCTION],rs,source.FUNCTION,anchors)
                self.assertEqual(unknown,[])
                stem=self.out/('rebase-%d-%s'%(i,label))
                asm=stem.with_suffix('.s');out=stem.with_suffix('.o');ld=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                asm.write_text(assembly);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(out),str(asm)],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in anchors.items()],'-o',str(elf),str(out)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>41I',sections(elf)['.text'][1])))
            self.assertEqual(images[0],images[1])
            for index,command,phase in itertools.product((0,9),COMMANDS,(0,8)):
                self.compare(fixture(index=index,anchors=anchors),(index,command,INPUT),phase,anchors,images,entry);count+=1
        self.receipt.update(independent_GNU_links=6,rebase_phases=count,all6_bindings_rebased=True,anchors_independent=True)

    def test_07_fired_guest_access_fault_prefixes(self):
        count=0
        for command,phase in itertools.product((0,1,2),(0,8)):
            args=(0,command,INPUT);m=fixture()
            good=RecordOracle(self.truth,m,args,phase).run()
            for cut in range(good.root_accesses):
                models=[RecordOracle(code,m,args,phase)for code in (self.truth,self.words)]
                for model in models:
                    model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):
                        model.run()
                self.assertEqual(complete(models[0]),complete(models[1]))
                self.assertEqual((models[0].trace,models[0].current_pc,models[0].delay_of),
                                 (models[1].trace,models[1].current_pc,models[1].delay_of));count+=1
        self.assertEqual(count,12)
        self.receipt.update(fired_target_fault_prefixes=count,portable_fault_or_hardware_MMU_claimed=False)

    def test_08_strict_image_current_historical_inputs_and_corruptions(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+164]
        expected=source.predicted_image(before,truth)
        self.assertEqual(expected,(self.out/'first-linked.elf').read_bytes())
        at=source.elf_slot_offset(before,source.ENTRY,164)
        for offset in (0,at-1,at,at+160,at+164,len(before)-1):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):
                source.check_image(before,bytes(bad),truth)
        with self.assertRaises(ValueError):
            source.check_image(before,expected[:-1],truth)
        for name,wanted in source.INPUTS.items():
            old=self.values[name]
            self.assertEqual(source.digest(old),wanted)
            current=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else expected if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),current)
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        self.receipt.update(strict_image_corruptions_rejected=7,frozen_and_current_inputs=len(source.INPUTS),
            entire_guard_manifest_unchanged=True,metadata_exclusions=0)


if __name__=='__main__':
    unittest.main()
