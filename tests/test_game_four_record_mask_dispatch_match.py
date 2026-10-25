"""Four-player health dispatch: live bytes, real caller/case 5, and literal ABI."""
from pathlib import Path
from unittest.mock import patch
import itertools
import json
import struct
import subprocess
import unittest
from tools.experiments import game_four_record_mask_dispatch_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT = Path(__file__).resolve().parents[2]
SYMBOLS = dict(D_800D18A8=0x800D18A8, D_800CC2D0=0x800CC2D0, func_15085710=0x15085710)
TABLE, STATUS = 0x8009D970, 0x800D2145
PARENT, PARENT_ROM = 0x15018DFC, 0x462AC
HELPER_TABLE = (0x15085750, 0x1508576C, 0x15085788, 0x150857B8, 0x15085804, 0x15085840,
                0x1508585C, 0x150858A8, 0x150858EC, 0x15085908, 0x15085924, 0x1508596C)


def fixture(mask=15, disable=0, pattern=0, symbols=SYMBOLS, phase=0):
    m = {STACK+i: (i*17+0xA5)&255 for i in range(-512, 256)}
    for i in range(26):
        for offset in (-1, 0, 1):
            m[symbols['D_800CC2D0']+i*0x32C+0x1CA+offset] = (pattern*73+i*61+offset)&255
        m[STATUS+i*28] = 0xA5
    m[symbols['D_800D18A8']] = disable
    for i, word in enumerate(HELPER_TABLE):
        put(m, TABLE+4*i, word)
    return m


def mutate(m, slot, mode, symbols):
    if mode&1:
        m[symbols['D_800D18A8']] = 255
    if mode&2 and slot < 3:
        address = symbols['D_800CC2D0']+(slot+1)*0x32C+0x1CA
        m[address] ^= 0xE7


def reference(initial, mask, mode=0, symbols=SYMBOLS, phase=0):
    m, calls = dict(initial), []
    put(m, STACK+phase, mask&0xFFFFFFFF)
    if not m[symbols['D_800D18A8']]:
        for slot in range(4):
            if mask & (1 << slot):
                value = m[symbols['D_800CC2D0']+slot*0x32C+0x1CA]
                calls.append((symbols['func_15085710'], (slot, 5, value)))
                m[STATUS+slot*28] = value
                mutate(m, slot, mode, symbols)
    return m, calls


def public(m, symbols=SYMBOLS):
    addresses = {symbols['D_800D18A8']}
    addresses.update(symbols['D_800CC2D0']+i*0x32C+0x1CA+o for i in range(26) for o in (-1,0,1))
    return {a: b for a,b in m.items() if not STACK-512 <= a < STACK+256 or a in addresses}


class DispatchOracle(RayOracle):
    def __init__(self, words, memory, mask=15, mode=0, phase=0, symbols=SYMBOLS,
                 entry=source.ENTRY, connected=None, parent=False, real=False):
        TimingOracle.__init__(self, words, memory, phase=phase, entry=entry,
                              arguments=(mask&0xFFFFFFFF,), connected=connected)
        self.mode, self.symbols, self.real, self.parent = mode, symbols, real, parent
        self.hi, self.lo = 0x89ABCDEF, 0x76543210

    def record_call(self, target):
        args = self.arguments(3 if target==self.symbols['func_15085710'] else
                              1 if target in (source.ENTRY,0x150A09D0) else 0)
        self.calls.append((target,args))
        self.events.append(('CALL',target,args))

    def hook(self, target):
        if target==self.symbols['func_15085710']:
            slot, mode, value = self.arguments(3)
            assert 0<=slot<4 and mode==5 and 0<=value<256
            self.memory[STATUS+slot*28] = value
            mutate(self.memory, slot, self.mode, self.symbols)
        else:
            assert self.parent and target in (0x150A09D0,0x150619A8,0x1501C870,
                                               0x1502378C,0x1504A730,0x1507C370,0x1507C8FC)
        for i in range(4):
            self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):
            self.r[reg] = 0xA5000000+reg
        self.f[:20] = [0xA5000000+i for i in range(20)]
        self.hi, self.lo = 0x87654321, 0x12345678


def controls():
    b = source.SELECTED
    cached = b.replace('    s32 slot;', '    s32 slot;\n    u8 cached[4];\n    for (slot=0; slot<4; slot++) cached[slot]=D_800CC2D0[slot].health;')
    cached = cached.replace('func_15085710((s16)slot, 5, D_800CC2D0[slot].health)',
                            'func_15085710((s16)slot, 5, cached[slot])')
    return dict(wrong_gate=b.replace('!D_800D18A8', 'D_800D18A8'),
                missing_gate=b.replace('!D_800D18A8', '1'),
                missing_fourth=b.replace('slot < 4', 'slot < 3'),
                extra_fifth=b.replace('slot < 4', 'slot < 5'),
                wrong_bit=b.replace('(1 << slot) & mask', '(2 << slot) & mask'),
                signed_health=b.replace('5, D_800CC2D0[slot].health', '5, (s8)D_800CC2D0[slot].health'),
                wrong_record=b.replace('D_800CC2D0[slot].health', 'D_800CC2D0[slot+1].health'),
                wrong_field=b.replace('.health', '.unk1C9'),
                wrong_mode=b.replace('(s16)slot, 5,', '(s16)slot, 6,'),
                reread_gate=b.replace('slot < 4', 'slot < 4 && !D_800D18A8'),
                reversed=b.replace('slot = 0; slot < 4; slot++', 'slot = 3; slot >= 0; slot--'),
                cached_health=cached)


def native_harness(body, exhaustive=True):
    text = '#include <ultra64.h>\n'+source.TYPES+source.DECLARATIONS+'''
struct127 D_800CC2D0[26];
u8 D_800D18A8;
typedef char ABI[(sizeof(void*)==4 && sizeof(struct127)==0x32C &&
 __builtin_offsetof(struct127,health)==0x1CA && sizeof(s16)==2)?1:-1];
static u32 count,error,mutation,expectedCount;
static s32 expectedSlot[5];static u8 expectedValue[5],status[26],health[26];
static u8 expectedBytes[sizeof(D_800CC2D0)];
__attribute__((noinline,noclone)) void func_15085710(s16 slot,s32 mode,s32 value){
 if(count>=expectedCount || slot!=expectedSlot[count] || mode!=5 || value!=expectedValue[count])error=1;
 if(slot>=0 && slot<26)status[slot]=(u8)value;else error=1;
 count++;
 if(mutation&1)D_800D18A8=255;
 if((mutation&2)&&slot>=0&&slot<3)D_800CC2D0[slot+1].health^=0xE7;
}
'''+body+'''
static int one(u32 mask,u32 disabled,u32 pattern,u32 mut){
 u32 i,n,flag=disabled;u8 *p=(u8*)D_800CC2D0;
 error=count=expectedCount=0;mutation=mut;D_800D18A8=(u8)disabled;
 for(i=0;i<26;i++){
  health[i]=(u8)(pattern*73+i*61);D_800CC2D0[i].health=health[i];status[i]=0xA5;
  expectedBytes[i*0x32C+0x1CA]=health[i];
 }
 if(!disabled)for(i=0;i<4;i++)if(mask&(1u<<i)){
  n=expectedCount++;expectedSlot[n]=(s32)i;expectedValue[n]=health[i];
  if(mut&1)flag=255;
  if((mut&2)&&i<3)health[i+1]^=0xE7;
 }
 func_15085ABC((s16)mask);
 if(error||count!=expectedCount||D_800D18A8!=flag)return 23;
 for(i=0;i<26;i++)if(D_800CC2D0[i].health!=health[i])return 23;
 for(i=0;i<26;i++){
  u8 wanted=0xA5;for(n=0;n<expectedCount;n++)if(expectedSlot[n]==(s32)i)wanted=expectedValue[n];
  if(status[i]!=wanted)return 23;
  expectedBytes[i*0x32C+0x1CA]=health[i];
 }
 if((mask&255)==255)for(i=0;i<sizeof(D_800CC2D0);i++)if(p[i]!=expectedBytes[i])return 23;
 return 0;
}
int run(void){
 u32 i,mask,disabled,pattern,mut;u8 *p=(u8*)D_800CC2D0;
 for(i=0;i<sizeof(D_800CC2D0);i++)p[i]=expectedBytes[i]=(u8)(i*17+0x5A);
'''
    if exhaustive:
        text += ' for(mask=0;mask<65536;mask++)for(disabled=0;disabled<2;disabled++)if(one(mask,disabled,mask%4,mask%4))return 23;\n'
    text += ' for(pattern=0;pattern<256;pattern++)for(mut=0;mut<4;mut++)if(one(15,0,pattern,mut))return 23;\n'
    text += ''' for(mask=0;mask<32;mask++)for(disabled=0;disabled<256;disabled++)
  for(pattern=0;pattern<4;pattern++)for(mut=0;mut<4;mut++)if(one(mask,disabled,pattern,mut))return 23;
 return 0;
}
'''+START
    return text


class FourRecordMaskDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT/source.BUILD
        cls.values = source.snapshot(cls.output)
        cls.installed = (ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        if cls.installed:
            source.audit_inputs(ROOT,cls.output)
        else:
            source.freeze(ROOT,cls.output)
        cls.rom = cls.values['conker/conker.us.bin']
        cls.truth = list(struct.unpack_from('>44I',cls.rom,source.ROM))
        cls.obj = cls.output/'after-owner.o'
        linked, funcs = source.link_owner(ROOT,cls.output,cls.obj,source.OWNER)
        cls.words = list(struct.unpack_from('>44I',linked,funcs[source.FUNCTION]['value']))
        cls.receipt = {}

    def test_01_words_owner_Make_inputs_and_effective_guards(self):
        raw,bindings = source.payload(self.obj)
        source.checked_payload(raw,bindings)
        self.assertEqual(self.truth,self.words)
        self.assertEqual(self.rom[source.ROM+176:source.ROM+180],bytes(4))
        q=json.loads((self.output/'qualification.json').read_text())
        self.assertEqual((q['words'],q['frame'],q['preserved_neighbors'],q['new_guards']),(44,48,7,0))
        self.assertEqual((q['typed_caller_ABI'],q['caller_functions_preserved']),('void(s16)',16))
        self.assertEqual((self.output/'proposed-caller.c').read_bytes(),source.typed_caller(self.values[source.CALLER_SOURCE].decode()).encode())
        self.assertEqual(json.loads((self.output/'make-shadow.json').read_text())['actual_Make_commands'],3)
        for i in range(44):
            wrong=bytearray(raw);wrong[4*i]^=1
            with self.assertRaises(ValueError):source.checked_payload(bytes(wrong),bindings)
        for at in bindings:
            wrong=dict(bindings);wrong[at]=[('R_MIPS_26','unknown')]
            with self.assertRaises(ValueError):source.checked_payload(raw,wrong)
        self.receipt.update(words=44,frame=48,bindings=5,new_guards=0,preserved_neighbors=7,
                            alignment_words=1,word_and_binding_negatives=49,typed_caller_functions_preserved=16)

    def test_02_guest_live_health_byte_masks_and_full_register_lifetime(self):
        visits=set();count=0
        cases=[(mask,disabled,pattern,mode) for mask,disabled,pattern,mode in
               itertools.product((0,1,2,4,8,15,16,0x7FFF,0x8000,0xFFFF,0x1234000F),
                                 (0,1,127,128,255),range(4),range(4))]
        cases += [(15,disabled,0,0)for disabled in range(256)]
        cases += [(15,0,pattern,mode)for pattern,mode in itertools.product(range(256),(0,3))]
        for (mask,disabled,pattern,mode),phase in itertools.product(cases,(0,8)):
            m=fixture(mask,disabled,pattern,phase=phase)
            expected,calls=reference(m,mask,mode,phase=phase);models=[]
            for words in (self.truth,self.words):
                model=DispatchOracle(words,m,mask,mode,phase).run()
                self.assertEqual((public(model.memory),model.calls),(public(expected),calls))
                self.assertEqual(read(model.memory,STACK+phase),mask&0xFFFFFFFF)
                self.assertEqual(model.r[29],STACK+phase)
                visits.update(model.visits);models.append(model)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+176,4))<=visits)
        self.receipt.update(guest_phases=count,all44_words_executed=True,
                            disable_byte_sweep=256,live_future_health_and_one_time_gate=True)

    def test_03_native32_all_masks_all_gate_bytes_and_semantic_negatives(self):
        def native(body,label,opt,exhaustive):
            path=self.output/(label+opt+'.c');exe=path.with_suffix('.elf')
            path.write_text(native_harness(body,exhaustive))
            p=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            return subprocess.run([str(exe)],capture_output=True).returncode
        for opt in ('-O0','-O2','-O3'):
            self.assertEqual(native(source.SELECTED,'native',opt,True),0)
        for label,body in controls().items():
            self.assertNotEqual(body,source.SELECTED)
            self.assertEqual(native(body,label,'-O2',False),23,label)
        self.receipt.update(native_optimizations=3,trap_UBSan=True,native_masks_per_optimization=65536,
                            native_gate_bytes=256,effective_semantic_negatives=len(controls()),
                            canonical_record_bytes=812,health_offset=458,portable_alias_claimed=False)

    def test_04_original_case5_helper_and_retained_placeholder_boundary(self):
        helper=list(struct.unpack_from('>167I',self.rom,0xB2BC0))
        connected={SYMBOLS['func_15085710']+4*i:w for i,w in enumerate(helper)}
        before=self.values['conker/build/conker.us.elf']
        at=source.elf_slot_offset(before,TABLE,48)
        self.assertEqual(struct.unpack_from('>12I',before,at),HELPER_TABLE)
        count=0;visits=set()
        for mask,disabled,pattern,phase in itertools.product((0,1,8,15,0x8000,0xFFFF),(0,1),range(4),(0,8)):
            m=fixture(mask,disabled,pattern);expected,calls=reference(m,mask,phase=phase);models=[]
            for words in (self.truth,self.words):
                model=DispatchOracle(words,m,mask,phase=phase,connected=connected,real=True).run()
                self.assertEqual((public(model.memory),model.calls),(public(expected),calls))
                self.assertEqual(model.r[29],STACK+phase);models.append(model);visits.update(model.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        helper_visits=set(connected)&visits
        self.assertIn(0x15085858,helper_visits)
        retained=struct.unpack_from('>3I',before,source.elf_slot_offset(before,0x15085710,12))
        self.assertEqual(retained,(0x00001025,0x03E00008,0))
        self.receipt.update(original_case5_phases=count,helper_words_supplied=167,
                            helper_words_visited=len(helper_visits),retained_helper_stub_bytes=12,
                            helper_recovery_credit=0,other_helper_modes_claimed=False,gameplay_claimed=False)

    def test_05_complete_byte_exact_original_caller_and_mutating_providers(self):
        caller=list(struct.unpack_from('>35I',self.rom,PARENT_ROM));before=self.values['conker/build/conker.us.elf']
        self.assertEqual(struct.unpack_from('>35I',before,source.elf_slot_offset(before,PARENT,140)),tuple(caller))
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[0x46310])
        pointer=struct.pack('>I',source.ENTRY)
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==pointer],[])
        visits=set();count=0
        for mask,paused,kind,disabled,mode,phase in itertools.product((0,1,15,0x8000,0xFFFF),(0,1),(0,1,255),(0,255),(0,3),(0,8)):
            m=fixture(mask,disabled)
            put(m,0x800D2340,mask,2);m[0x800BEAC0]=paused;m[0x800C35EA]=kind
            put(m,0x800BE9E4,0x12345678)
            models=[]
            for words in (self.truth,self.words):
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                model=DispatchOracle(caller,m,mask,mode,phase,entry=PARENT,connected=connected,parent=True).run()
                calls=[t for t,args in model.calls]
                self.assertEqual(calls[:3],[0x150A09D0,0x150619A8,0x1501C870])
                self.assertEqual(calls[-2:],[0x1507C370,0x1507C8FC])
                self.assertEqual(calls.count(source.ENTRY),0 if paused else 1)
                if not paused:
                    self.assertEqual(calls[3],0x1502378C if kind==1 else 0x1504A730)
                    passed=next(args[0]for target,args in model.calls if target==source.ENTRY)
                    self.assertEqual(passed,((mask^0x8000)-0x8000)&0xFFFFFFFF)
                    expected,helper_calls=reference(m,mask,mode,phase=phase-24)
                    self.assertEqual([c for c in model.calls if c[0]==SYMBOLS['func_15085710']],helper_calls)
                    self.assertEqual(public(model.memory),public(expected))
                self.assertEqual(model.r[29],STACK+phase);visits.update(model.visits);models.append(model)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(PARENT,PARENT+140,4))<=visits)
        self.receipt.update(direct_call_sites=1,pointer_sites=0,original_caller_words=35,
                            all35_caller_words_executed=True,connected_caller_phases=count,
                            outer_providers_scripted=True,original_caller_is_already_byte_exact=True)

    def test_06_independent_signed_low_rebases_and_guest_stack_aliases(self):
        count=0
        for index,entry in enumerate((source.ENTRY,0x18017FFC,0x1A028000)):
            symbols=SYMBOLS if index==0 else dict(D_800D18A8=0x80347FFC+index*0x100000,
                D_800CC2D0=0x80358000+index*0x100000,func_15085710=0x15098004+index*0x10000)
            images=[]
            for label,obj in (('original',source.original(ROOT,self.output)),('C',self.obj),('padded',self.output/'qualified-padded.o')):
                data,funcs,rs=source.parse_object(obj);text,unknown=emit_function(data,funcs[source.FUNCTION],rs,source.FUNCTION,symbols)
                self.assertFalse(unknown);stem=self.output/('rebase-%d-%s'%(index,label))
                stem.with_suffix('.s').write_text(text)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(stem.with_suffix('.o')),str(stem.with_suffix('.s'))],capture_output=True,check=True)
                stem.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(stem.with_suffix('.ld')),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in symbols.items()],'-o',str(stem.with_suffix('.elf')),str(stem.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>44I',sections(stem.with_suffix('.elf'))['.text'][1])))
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for phase,mode in itertools.product((0,8),range(4)):
                m=fixture(15,0,1,symbols,phase);expected,calls=reference(m,15,mode,symbols,phase)
                models=[DispatchOracle(w,m,15,mode,phase,symbols,entry).run()for w in images]
                for model in models:self.assertEqual((public(model.memory,symbols),model.calls),(public(expected,symbols),calls))
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]));count+=1
        aliases=0
        for phase,tag_offset in itertools.product((0,8),(-32,-24,-16,0,4)):
            symbols=dict(SYMBOLS,D_800CC2D0=STACK+phase+tag_offset-0x1CA)
            # Re-link globals, not instructions, for each overlapping guest layout.
            obj=self.obj;data,funcs,rs=source.parse_object(obj)
            text,unknown=emit_function(data,funcs[source.FUNCTION],rs,source.FUNCTION,symbols)
            stem=self.output/('stack-alias-%d-%d'%(phase,tag_offset));stem.with_suffix('.s').write_text(text)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(stem.with_suffix('.o')),str(stem.with_suffix('.s'))],capture_output=True,check=True)
            stem.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(stem.with_suffix('.ld')),'-e',source.FUNCTION,
                *['--defsym=%s=0x%X'%p for p in symbols.items()],'-o',str(stem.with_suffix('.elf')),str(stem.with_suffix('.o'))],capture_output=True,check=True)
            words=list(struct.unpack_from('>44I',sections(stem.with_suffix('.elf'))['.text'][1]))
            self.assertEqual(words,relocated(self.truth,SYMBOLS,symbols))
            m=fixture(15,0,1,symbols,phase)
            a=DispatchOracle(words,m,15,3,phase,symbols).run()
            b=DispatchOracle(relocated(self.truth,SYMBOLS,symbols),m,15,3,phase,symbols).run()
            self.assertEqual(complete(a),complete(b));aliases+=1
        self.receipt.update(independent_GNU_links=9,rebase_phases=count,guest_stack_aliases=aliases,
                            signed_low_carry=True,portable_stack_alias_claimed=False)

    def test_07_every_target_access_fault_prefix_is_literal_guest_evidence(self):
        count=0
        for mask,disable,phase in itertools.product((0,1,15),(0,255),(0,8)):
            m=fixture(mask,disable);good=DispatchOracle(self.truth,m,mask,3,phase).run()
            for cut in range(good.root_accesses):
                models=[DispatchOracle(w,m,mask,3,phase)for w in(self.truth,self.words)]
                for model in models:
                    model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                    self.assertEqual(model.root_accesses,cut)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt.update(fired_target_fault_prefixes=count,portable_C_fault_claimed=False)

    def test_08_strict_whole_image_and_frozen_live_input_negatives(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+176]
        predicted=source.predicted_image(before,truth);source.check_image(before,predicted,truth)
        at=source.elf_slot_offset(before,source.ENTRY,176)
        for offset in (0,at-1,at,at+175,at+176,len(before)-1):
            wrong=bytearray(predicted);wrong[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        with self.assertRaises(ValueError):source.check_image(before,predicted[:-1],truth)
        if self.installed:source.audit_inputs(ROOT,self.output)
        else:source.freeze(ROOT,self.output)
        self.receipt.update(strict_image_negatives=7,input_history=len(source.INPUTS),zero_metadata_exclusions=True)

    def test_09_installed_map_rejects_stale_object_and_fourteen_input_mutations(self):
        original=Path.read_bytes;actual={ROOT/name:data for name,data in self.values.items()}
        actual[ROOT/source.SOURCE]=source.recovered_owner(self.values[source.SOURCE].decode()).encode()
        actual[ROOT/source.CALLER_SOURCE]=source.typed_caller(self.values[source.CALLER_SOURCE].decode()).encode()
        actual[ROOT/source.OBJECT]=original(self.output/'qualified-padded.o')
        actual[ROOT/'conker/build/conker.us.elf']=source.predicted_image(self.values['conker/build/conker.us.elf'],self.rom[source.ROM:source.ROM+176])
        def read_input(path):return actual[path]if path in actual else original(path)
        with patch.object(Path,'read_bytes',read_input):source.audit_inputs(ROOT,self.output)
        names=(source.SOURCE,source.OBJECT,'conker/build/conker.us.elf','conker/retail_word_patches.us.csv',
               source.CALLER_SOURCE,source.CALLER_OBJECT,'conker/include/structs.h')
        count=0
        for name in names:
            for path in(ROOT/name,self.output/('before-'+name.replace('/','_'))):
                old=actual[path]if path in actual else original(path);wrong=bytearray(old);wrong[len(wrong)//2]^=1
                with patch.object(Path,'read_bytes',lambda p:bytes(wrong)if p==path else read_input(p)),self.assertRaises(ValueError):
                    source.audit_inputs(ROOT,self.output)
                count+=1
        with patch.object(Path,'read_bytes',lambda p:self.values[source.OBJECT]if p==ROOT/source.OBJECT else read_input(p)),self.assertRaises(ValueError):
            source.audit_inputs(ROOT,self.output)
        self.receipt.update(input_mutations_rejected=count,stale_object_rejected=True,qualified_installed_map_accepted=True)

    def test_10_old_zero_return_target_stub_is_effectively_wrong(self):
        before=self.values['conker/build/conker.us.elf']
        old=struct.unpack_from('>44I',before,source.elf_slot_offset(before,source.ENTRY,176))
        m=fixture();actual=DispatchOracle(old,m).run();wanted=DispatchOracle(self.truth,m).run()
        self.assertFalse(actual.calls);self.assertEqual(len(wanted.calls),4)
        self.assertNotEqual(public(actual.memory),public(wanted.memory))
        self.receipt.update(retained_target_stub_effectively_rejected=True)


def relocated(words,before,after):
    result=list(words)
    for hi,lo,name in ((11,12,'D_800D18A8'),(17,18,'D_800CC2D0')):
        value=after[name]
        result[hi]=(result[hi]&0xFFFF0000)|(((value+0x8000)>>16)&65535)
        result[lo]=(result[lo]&0xFFFF0000)|(value&65535)
    result[31]=0x0C000000|(after['func_15085710']>>2&0x3FFFFFF)
    return result
