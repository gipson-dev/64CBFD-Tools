"""Three selector callbacks: byte ABI, aliases, complete dispatcher and strict image."""

import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_actor_selector_flag as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT = Path(__file__).resolve().parents[2]
ACTOR, EVENT, TABLE, PARENT, HELPER = 0x28000, 0x30000, 0x8008A02C, 0x151416E8, 0x1516972C
COMMANDS = (0,0x22,0x24,0x25,0x36,0x37,0xFF,0xAB000036)
FLAGS = (0,2,0xFFFFFFFF,0x80000000,0x7FFFFFFF,0x12345678)


def fixture(selector=3, flags=0x12345678, slot=14):
    m = {STACK+i:(i*17+0xA5)&255 for i in range(-0x200,0x100)}
    for base,length in ((ACTOR-16,0x1A0),(EVENT-16,40),(TABLE,72)):
        m.update({base+i:(i*13+0xA5)&255 for i in range(length)})
    put(m,ACTOR+0x58,flags);m[EVENT]=selector;m[ACTOR+0x168]=slot
    for i in range(18):
        put(m,TABLE+i*4,0)
    for name,row in source.TARGETS.items():
        put(m,TABLE+row['slot']*4,row['entry'])
    return m


def leaf_reference(memory, name, actor, event, command, sp):
    m = dict(memory);put(m,sp+8,command)
    if command&255==0x36:
        selector=m[event];value=read(m,actor+0x58)
        if selector==3 or selector in source.TARGETS[name]['red']:
            put(m,actor+0x58,value|2)
            m[actor+0x28],m[actor+0x29],m[actor+0x2A] = (0,255,0) if selector==3 else (255,0,0)
        else:
            put(m,actor+0x58,value&0xFFFFFFFD)
    return m


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-0x200<=a<STACK+0x100}


class SelectorOracle(TimingOracle):
    def __init__(self, words, memory, arguments, phase=0, entry=None, connected=None):
        self.trace=[]
        super().__init__(words,memory,phase=phase,entry=entry or source.TARGETS[source.FUNCTIONS[0]]['entry'],
            arguments=arguments,connected=connected)

    def get(self, address, size):
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value

    def put(self, address, value, size):
        if self.recording and self.own_instruction:
            assert all(address+i in self.memory for i in range(size)),('unmapped selector store',address,size)
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))

    def record_call(self, target):
        entries={v['entry']for v in source.TARGETS.values()}
        assert target in entries or target==HELPER,hex(target)
        args=tuple(self.r[4:7])if target in entries else (self.r[4],)
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self, target):
        assert target==HELPER
        # Opaque void provider: qualify the packet and caller ABI, not its implementation.
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x87654321,0x12345678


def native_harness(bodies, parent):
    functions='\n\n'.join(bodies[name]for name in source.FUNCTIONS)
    return """typedef unsigned char u8;typedef signed char s8;typedef unsigned int u32;typedef int s32;
typedef struct{u8 prefix[0x28],channels[3],gap[0x58-0x2B];u32 flags;u8 tail[0x180-0x5C];}Actor;
typedef Actor struct102;
typedef struct{u32 before[4];Actor actor;u8 event[4];u32 after[4];}State;
typedef char Width[(sizeof(void*)==4&&sizeof(Actor)==0x180&&__builtin_offsetof(Actor,flags)==0x58)?1:-1];
static State state,expected;static u32 calls;static struct102 *last;
#define NULL ((void*)0)
typedef void(*Callback)(u8*,u8*,u8);
static Callback D_8008A02C[18];
void func_1516972C(struct102 *p){calls++;last=p;}
""" + functions + '\n' + parent + """
static int run(void){u32 variant,mode,selector,fi,ci,alias,j,slot,command,value,selected,want;
 u8 *a=(u8*)&state,*b=(u8*)&expected,*actor=(u8*)&state.actor,*ev;
 const u32 commands[]={0,0x22,0x24,0x25,0x36,0xFF,0xAB000036u};
 const u32 flags[]={0,2,0xFFFFFFFFu,0x80000000u,0x7FFFFFFFu,0x12345678u};
 Callback leaves[]={func_150D7420,func_150D74DC,func_150D758C};
 for(j=0;j<18;j++)D_8008A02C[j]=0;
 for(j=0;j<3;j++)D_8008A02C[12+j]=leaves[j];
 for(variant=0;variant<3;variant++)for(mode=0;mode<3;mode++)for(selector=0;selector<256;selector++)
 for(fi=0;fi<6;fi++)for(ci=0;ci<7;ci++)for(alias=0;alias<4;alias++){
  for(j=0;j<sizeof(State);j++)a[j]=(u8)(j*13+0xA5);
  slot=mode==2?0:variant+12;actor[0x168]=(u8)slot;state.actor.flags=flags[fi];
  ev=alias==0?state.event:alias==1?actor+0x28:alias==2?actor+0x29:actor+0x58;
  *ev=(u8)selector;selected=*ev;command=commands[ci]&255;
  for(j=0;j<sizeof(State);j++)b[j]=a[j];
  if(command==0x36&&mode!=2){
   value=expected.actor.flags;
   if(selected==3||(variant==0&&(selected==1||selected==2))||(variant==1&&selected==2)){
    expected.actor.flags=value|2;
    expected.actor.channels[0]=(u8)(selected==3?0:255);
    expected.actor.channels[1]=(u8)(selected==3?255:0);expected.actor.channels[2]=0;
   }else expected.actor.flags=value&=0xFFFFFFFDu;
  }
  want=(mode!=0&&command==0x22&&selected==slot);calls=0;last=0;
  if(mode!=0&&(command==0x24||command==0x25)&&selected==slot)
   ((u8*)&expected.actor)[0x169]=(u8)(command==0x24?255:2);
  if(mode==0)leaves[variant](command==0x36?actor:(u8*)0,command==0x36?ev:(u8*)0,(u8)commands[ci]);
  else func_151416E8(actor,ev,(u8)commands[ci]);
  if(calls!=want||(want&&last!=&state.actor))return 23;
  for(j=0;j<sizeof(State);j++)if(a[j]!=b[j])return 23;
 }return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
"""


class ActorSelectorFlagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD
        cls.installed=source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:
            source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin']
        cls.words={};cls.truth={};cls.objects={}
        for name,row in source.TARGETS.items():
            obj,diagnostics=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.SELECTED[name],'fresh-'+name)
            if diagnostics:raise ValueError(diagnostics)
            cls.objects[name]=obj;cls.words[name]=list(struct.unpack('>%dI'%(row['size']//4),source.payload(obj,name)[0]))
            cls.truth[name]=list(struct.unpack_from('>%dI'%(row['size']//4),cls.rom,row['rom']))
        before=cls.values['conker/src/game_16DC80.c'].decode()
        lo,hi=source.function_span(before,'func_151416E8');cls.parent=before[lo:hi]
        cls.receipt=dict(installed=cls.installed)

    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('actor selector qualification:',cls.receipt)

    def compare(self, name, memory, args, phase=0, images=None, entry=None):
        target=source.TARGETS[name];entry=entry or target['entry']
        expected=leaf_reference(memory,name,*args,STACK+phase)
        models=[SelectorOracle(code,memory,args,phase,entry).run()for code in images or (self.truth[name],self.words[name])]
        for m in models:
            self.assertEqual(m.memory,expected)
            self.assertFalse(m.calls)
        self.assertEqual(complete(models[0]),complete(models[1]))
        self.assertEqual(models[0].trace,models[1].trace)
        return models

    def test_01_three_direct_payloads_GNU_owner_Make_and_old_stubs(self):
        before=self.values['conker/build/conker.us.elf']
        for name,row in source.TARGETS.items():
            self.assertEqual(self.words[name],self.truth[name])
            raw,bindings=source.payload(self.objects[name],name)
            self.assertEqual((len(raw),source.digest(raw),bindings),(row['size'],row['SHA256'],{}))
            self.assertEqual(source.payload(source.original(ROOT,self.out,name),name),(raw,{}))
            self.assertFalse(any(w>>26==9 and w>>21&31==29 and w>>16&31==29 for w in self.words[name]))
            at=source.elf_slot_offset(before,row['entry'],row['size'])
            old=struct.unpack_from('>%dI'%(row['size']//4),before,at);m=fixture()
            model=SelectorOracle(old,m,(ACTOR,EVENT,0x36),entry=row['entry']).run()
            self.assertNotEqual(public(model.memory),public(leaf_reference(m,name,ACTOR,EVENT,0x36,STACK)))
        q=json.loads((self.out/'qualification.json').read_text())
        self.assertEqual((q['total_words'],q['preserved_neighbors'],q['new_guards']),(132,4,0))
        self.assertEqual(json.loads((self.out/'make-shadow.json').read_text())['actual_Make_commands'],5)
        self.receipt.update(targets=3,words=[47,44,41],frames=[0,0,0],bindings=0,new_guards=0,
            neighbors=4,actual_Make_commands=5,old_stubs_effectively_rejected=3)

    def test_02_all_selector_bytes_command_width_flags_and_reachability(self):
        count=0
        for name in source.FUNCTIONS:
            row=source.TARGETS[name];visits=set()
            for selector,command,phase in itertools.product(range(256),COMMANDS,(0,8)):
                memory=fixture(selector,FLAGS[selector%len(FLAGS)])
                args=(ACTOR,EVENT,command)if command&255==0x36 else (0,0,command)
                models=self.compare(name,memory,args,phase);visits.update(models[0].visits);count+=1
                trace=models[0].trace
                self.assertEqual(trace[0],('W',STACK+phase+8,4,command))
                if command&255!=0x36:self.assertEqual(len(trace),1)
                else:
                    colored=selector==3 or selector in row['red']
                    access=[('W',STACK+phase+8,4),('R',EVENT,1),('R',ACTOR+0x58,4)]
                    access += [('W',ACTOR+0x28,1),('W',ACTOR+0x29,1),('W',ACTOR+0x58,4),('W',ACTOR+0x2A,1)]if colored else [('W',ACTOR+0x58,4)]
                    self.assertEqual([x[:3]for x in trace],access)
            wanted=set(range(row['entry'],row['entry']+row['size'],4))
            unreachable=row['entry']+row['size']-24
            self.assertEqual(visits,wanted-{unreachable})
        self.receipt.update(leaf_phases=count,all256_selector_bytes_each=True,exact_access_order=True,
            reachable_target_words=129,unreachable_duplicate_loads_reproduced_statically=3,NULL_untouched_off_command=True)

    def test_03_guest_event_and_argument_home_aliases(self):
        count=0
        for name,offset,command,phase in itertools.product(source.FUNCTIONS,(-1,0x28,0x29,0x2A,0x58,0x59,0x168),
                                                          (0x36,0x03000036,0xAB000036),(0,8)):
            m=fixture();event=EVENT if offset==-1 else ACTOR+offset
            m[event]=3
            self.compare(name,m,(ACTOR,event,command),phase);count+=1
        for name,actor_in_home,event_in_home,command,phase in itertools.product(source.FUNCTIONS,(False,True),
                (False,True),(0x36,0x03000036,0xAB000036),(0,8)):
            actor=STACK+phase+8-0x58 if actor_in_home else ACTOR
            event=STACK+phase+8 if event_in_home else EVENT
            m=fixture();m[event]=3
            self.compare(name,m,(actor,event,command),phase);count+=1
        self.receipt.update(guest_alias_phases=count,full_incoming_command_word_home_preserved=True,
            home_aliases_not_portable_native_C_claim=True)

    def native(self,bodies,label,opt='-O2'):
        path=self.out/(label+opt+'.c');exe=path.with_suffix('.elf')
        path.write_text(native_harness(bodies,self.parent))
        p=subprocess.run(['gcc','-m32','-std=c99',opt,'-fno-pie','-no-pie','-nostdlib',
            '-fno-stack-protector','-fno-builtin','-fsanitize=undefined','-fsanitize-undefined-trap-on-error',
            '-Werror=implicit-function-declaration','-Wl,-e,_start',str(path),'-o',str(exe)],
            capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        return subprocess.run([str(exe)],capture_output=True).returncode

    def test_04_native32_typed_fences_real_C_dispatcher_and_wrong_C(self):
        for opt in ('-O0','-O2','-O3'):self.assertEqual(self.native(source.SELECTED,'native',opt),0)
        transforms={
            'wrong-command':lambda b:b.replace('command == 0x36','command == 0x37'),
            'wrong-clear':lambda b:b.replace('&= ~2','&= ~4'),
            'wrong-set':lambda b:b.replace('|= 2','|= 4'),
            'clobber-flags':lambda b:b.replace('|= 2','= 2'),
            'missing-channel':lambda b:b.replace('                actor[0x2A] = 0;\n',''),
            'wrong-green':lambda b:b.replace('actor[0x29] = 0xFF','actor[0x29] = 0x7F'),
            'default-set':lambda b:b.replace('            default:\n                *(u32 *)(actor + 0x58) &= ~2;',
                                            '            default:\n                *(u32 *)(actor + 0x58) |= 2;'),
            'opaque-byte-write':lambda b:b.replace('                actor[0x2A] = 0;','                actor[0x2A] = 0;\n                actor[0x2B] = 0;'),
        }
        for label,transform in transforms.items():
            bodies={name:transform(body)for name,body in source.SELECTED.items()}
            self.assertNotEqual(bodies,source.SELECTED)
            self.assertEqual(self.native(bodies,label),23,label)
        self.receipt.update(native_optimizations=3,native_cases_per_run=3*3*256*6*7*4,
            typed_fenced_actor_and_byte_aliases=True,actual_C_parent_compiled=True,trap_UBSan=True,
            effective_wrong_C_controls=8,opaque_helper_implementation_not_claimed=True)

    def test_05_complete55word_current_dispatcher_NULL_slot_and_unused_result(self):
        parent=list(struct.unpack_from('>55I',self.rom,0x16EB98))
        before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,PARENT,220)
        self.assertEqual(list(struct.unpack_from('>55I',before,at)),parent)
        visits=set();count=helper_calls=0
        for slot,selector,command,phase in itertools.product((0,12,13,14),(0,1,2,3,12,13,14,255),COMMANDS,(0,8)):
            m=fixture(selector,FLAGS[selector%6],slot);expected=dict(m);expected_calls=[]
            if slot:
                name=next(n for n,t in source.TARGETS.items()if t['slot']==slot)
                expected=leaf_reference(expected,name,ACTOR,EVENT,command&255,STACK+phase-24)
                expected_calls.append((source.TARGETS[name]['entry'],(ACTOR,EVENT,command&255)))
            byte=command&255
            if byte in (0x22,0x24,0x25)and expected[EVENT]==expected[ACTOR+0x168]:
                if byte==0x22:expected_calls.append((HELPER,(ACTOR,)));helper_calls+=1
                else:expected[ACTOR+0x169]=255 if byte==0x24 else 2
            models=[]
            for images in (self.truth,self.words):
                connected={}
                for name,code in images.items():
                    entry=source.TARGETS[name]['entry'];connected.update(zip(range(entry,entry+len(code)*4,4),code))
                model=SelectorOracle(parent,m,(ACTOR,EVENT,command),phase,PARENT,connected).run()
                self.assertEqual(public(model.memory),public(expected))
                self.assertEqual(model.calls,expected_calls)
                # The caller reloads its command, never consuming a callback result.
                if not any(c[0]==HELPER for c in expected_calls):self.assertEqual(model.r[2],byte)
                models.append(model);visits.update(model.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertEqual(set(range(PARENT,PARENT+220,4))-visits,{0x15141790,0x15141794})
        self.assertGreater(helper_calls,0)
        for name,row in source.TARGETS.items():
            pointer=struct.pack('>I',row['entry'])
            self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==pointer],
                             [0x22EAEC+row['slot']*4])
            jal=struct.pack('>I',0x0C000000|(row['entry']>>2&0x3FFFFFF))
            self.assertFalse(any(self.rom[i:i+4]==jal for i in range(0,len(self.rom),4)))
        self.receipt.update(current_and_original_caller_words=55,caller_phases=count,caller_reachable_words=53,
            parent_unreachable_branch_and_delay_identified=True,NULL_callback_bypass=True,
            callback_result_unused=True,opaque_helper_calls=helper_calls,other_table_slots_not_claimed=True)

    def test_06_independent_GNU_rebases_of_all_three_relocation_free_leaves(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        links=phases=0
        for name,row in source.TARGETS.items():
            original=source.original(ROOT,self.out,name)
            for i in range(3):
                entry=0x17007FFC+i*0x10000;images=[]
                for label,obj in (('original',original),('C',self.objects[name])):
                    text,fs,rs=source.parse_object(obj)
                    assembly,unknown=emit_function(text,fs[name],rs,name,{})
                    self.assertEqual(unknown,[])
                    stem=self.out/('rebase-%s-%d-%s'%(name,i,label));asm=stem.with_suffix('.s');out=stem.with_suffix('.o');ld=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                    asm.write_text(assembly);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(out),str(asm)],capture_output=True,check=True)
                    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',name,'-o',str(elf),str(out)],capture_output=True,check=True)
                    images.append(list(struct.unpack_from('>%dI'%(row['size']//4),sections(elf)['.text'][1])));links+=1
                self.assertEqual(images[0],images[1])
                for selector,command,phase in itertools.product((0,1,2,3,255),(0,0x36,0xAB000036),(0,8)):
                    self.compare(name,fixture(selector),(ACTOR,EVENT,command),phase,images,entry);phases+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=phases,relocation_free_leaves=True,
            no_absolute_guest_PC_assumption=True)

    def test_07_fired_leaf_fault_prefixes_and_argument_home(self):
        count=0
        for name,selector,command,phase in itertools.product(source.FUNCTIONS,(0,1,2,3,255),(0x36,0x37),(0,8)):
            m=fixture(selector);args=(ACTOR,EVENT,command);row=source.TARGETS[name]
            good=SelectorOracle(self.truth[name],m,args,phase,row['entry']).run()
            for cut in range(good.root_accesses):
                models=[SelectorOracle(code,m,args,phase,row['entry'])for code in (self.truth[name],self.words[name])]
                for model in models:
                    model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                self.assertEqual(complete(models[0]),complete(models[1]))
                self.assertEqual((models[0].trace,models[0].current_pc,models[0].delay_of),
                                 (models[1].trace,models[1].current_pc,models[1].delay_of));count+=1
        self.assertGreater(count,150)
        self.receipt.update(fired_leaf_fault_prefixes=count,own_home_store_and_return_delay_faults=True,
            portable_fault_or_hardware_MMU_claimed=False)

    def test_08_strict_three_body_image_all26_inputs_and_corruptions(self):
        before=self.values['conker/build/conker.us.elf'];expected=source.predicted_image(before,self.rom)
        self.assertEqual(expected,(self.out/'first-linked.elf').read_bytes())
        offsets=[0,len(expected)-1]
        for row in source.TARGETS.values():
            at=source.elf_slot_offset(before,row['entry'],row['size']);offsets.extend((at,at+row['size']-1))
        for offset in offsets:
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),self.rom)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],self.rom)
        for name,wanted in source.INPUTS.items():
            old=self.values[name];self.assertEqual(source.digest(old),wanted)
            current=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else expected if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),current)
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        self.receipt.update(strict_image_corruptions_rejected=len(offsets)+1,live_and_historical_inputs=26,
            complete_guard_manifest_unchanged=True,metadata_exclusions=0)


if __name__=='__main__':
    unittest.main()
