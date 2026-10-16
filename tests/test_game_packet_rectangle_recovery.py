"""Semantic renderer recovery; keep the unresolved retail word mismatch explicit."""
import itertools
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_packet_rectangle as source
from tools.tests import game_packet_rectangle_oracle as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_packet_visibility import types as visibility_types
from tools.pad_generated_object import parse_object
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections


def cases():
    for scales,position,flip,inset,tint,extent,divisor in itertools.product(
            ((2.5,3.25),(-2.5,3.25),(2.5,-3.25),(-2.5,-3.25)),
            ((4.25,8.75),(-4.75,-2.125),(-.75,-.125),(8192.25,-8192.25),(-16384.5,16383.75)),
            (0,1,2,3),(0,1),(0,1),((.5,.25,5),(2.,1.,-5),(32.5,20.25,0)),(1.5,-2.25,4096.)):
        yield guest.fixture((*scales,*position,divisor,*extent[:2]),flip,tint,animation=3,frame=43,
            speed=7,timestep=3,offsets=(-137,inset,extent[2]),dimensions=(65535,32768))


def controls():
    body=source.SELECTED
    return {
        'wrong-width-floor':body.replace('width < 2.0f','width < 1.0f').replace('width = 2.0f','width = 1.0f'),
        'wrong-height-floor':body.replace('    height = D_800D2C88;',
            '    height = D_800D2C88;\n    if (height < 2.0f) height = 2.0f;'),
        'wrong-alpha':body.replace('packet->alpha);','(u8)(packet->alpha + 1));'),
        'wrong-inset':body.replace('(width + width) / divisor','width / divisor'),
        'wrong-X-flip':body.replace('if (flipFlags & 1)','if (flipFlags & 4)'),
        'narrowed-Y-sign-check':body.replace('(s32)((u32)integerY << 2)','(s16)((u32)integerY << 2)'),
        'wrong-animation-modulo':body.replace('packet->animationFrame -= descriptor->unkA << 3;',
            'packet->animationFrame %= descriptor->unkA << 3;'),
        'wrong-animation-rate':body.replace('packet->animationStep * D_800BE9A0','packet->animationStep'),
    }


def types():
    return visibility_types().replace('    u8 paddingA[6];',source.PACKET_FIELDS)


def native_harness():
    rows=[]
    for memory,args in cases():
        expected,cursor,trap=guest.reference(memory,args)
        assert trap is None
        inputs=[guest.read(memory,a) for a in guest.GLOBALS]
        after=[guest.read(expected,a) for a in guest.GLOBALS]
        output=[guest.read(expected,args[0]+i*4) for i in range(16)]
        rows.append('{{%s},{%s},%d,%d,%d,%d,{%s},{%s},%d}'%(
            ','.join('0x%Xu'%v for v in inputs),','.join('0x%Xu'%v for v in args[2:]),
            guest.read(memory,guest.PACKET+13,1),guest.read(memory,guest.TINT_LOCK,1),
            cursor-args[0],guest.read(expected,guest.PACKET+12,1),
            ','.join('0x%Xu'%v for v in after),','.join('0x%Xu'%v for v in output),0))
    return types()+r'''
f32 D_800D2C70,D_800D2C74,D_800D2C78,D_800D2C7C,D_800D2C80,D_800D2C84,D_800D2C88;
u8 D_800D2DA8,D_800D2DA9,D_800D2DAA,D_800D2DAB,D_800BE9A0;
static f32*globals[]={&D_800D2C70,&D_800D2C74,&D_800D2C78,&D_800D2C7C,&D_800D2C80,&D_800D2C84,&D_800D2C88};
static Gfx output[8];static ProjectedPacket95B08 packet;static structC1D70Descriptor descriptor;
s32 func_15095D34(Gfx*,ProjectedPacket95B08*,s32,s32,s32);
struct Case{u32 input[7],extra[3],flip,tint,bytes,frame,after[7],words[16],reserved;};
static const struct Case cases[]={ROWS};
static f32 real(u32 b){union{u32 b;f32 f;}v;v.b=b;return v.f;}
static u32 word(f32 f){union{u32 b;f32 f;}v;v.f=f;return v.b;}
static u32 animate(u32 old,u32 delta,u32 flags){u32 next,limit;
 if(!flags)return old;next=(old+((flags&128)&&(old&128)?0u-delta:delta))&255;
 if(flags&128){if(old&128)return next&128?next:old&127;
 return next>=((flags&127)*8)?old|128:next;}
 limit=flags*8;return next>=limit?(next-limit)&255:next;}
static int run(void){u32 n,i,old,speed,t,flag,expected;const struct Case*c;static const u32 flags[]={0,1,2,127,128,129,130,255};s32 cursor;
 if(sizeof(void*)!=4||sizeof(ProjectedPacket95B08)!=20||__builtin_offsetof(ProjectedPacket95B08,animationFrame)!=12)return 29;
 packet.descriptor=&descriptor;descriptor.unk4=65535;descriptor.unk6=32768;descriptor.unkA=3;
 D_800D2DA8=17;D_800D2DA9=128;D_800D2DAA=254;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];
 for(i=0;i<7;i++)*globals[i]=real(c->input[i]);for(i=0;i<8;i++)output[i].words.w0=output[i].words.w1=0xA5A5A5A5u;
 packet.alpha=171;packet.animationStep=7;packet.animationFrame=43;packet.flipFlags=(u8)c->flip;D_800BE9A0=3;D_800D2DAB=(u8)c->tint;
 cursor=func_15095D34(output,&packet,(s32)c->extra[0],(s32)c->extra[1],(s32)c->extra[2]);
 if(cursor!=(s32)((u8*)output+c->bytes))return 20;
 for(i=0;i<8;i++)if(output[i].words.w0!=c->words[i*2]||output[i].words.w1!=c->words[i*2+1])return 21;
 for(i=0;i<7;i++)if(word(*globals[i])!=c->after[i])return 22;
 if(packet.animationFrame!=c->frame)return 23;}
 D_800D2C70=2.5f;D_800D2C74=3.25f;D_800D2C78=4.25f;D_800D2C7C=8.75f;
 D_800D2C80=4096.f;D_800D2C84=32.5f;D_800D2C88=20.25f;D_800D2DAB=1;packet.flipFlags=0;
 for(flag=0;flag<8;flag++)for(t=0;t<2;t++)for(old=0;old<256;old++)for(speed=0;speed<256;speed++){
 descriptor.unkA=(u8)flags[flag];packet.animationStep=(u8)speed;packet.animationFrame=(u8)old;D_800BE9A0=t?255:1;
 expected=animate(old,speed*D_800BE9A0,flags[flag]);func_15095D34(output,&packet,0,0,0);
 if(packet.animationFrame!=expected)return 24;}
 return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''.replace('ROWS',',\n'.join(rows))


class PacketRectangleRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.obj,cls.words,cls.row=source.measure(cls.root,cls.out,'tested')
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>346I',cls.rom,source.ROM))

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_original_and_C_geometry_globals_and_animation(self):
        count=0
        visits=set()
        for memory,args in cases():
            expected,cursor,trap=guest.reference(memory,args)
            self.assertIsNone(trap)
            for phase,words in itertools.product((0,8),(self.truth,self.words)):
                m=guest.RectangleOracle(words,memory,args,phase=phase).run()
                self.assertEqual((guest.base.public(m.memory),m.r[2]),(guest.base.public(expected),cursor))
                if words is self.truth:
                    visits.update(m.visits)
            count+=1
        self.receipt('sequences',cases=count,stack_phases=2,original_and_raw_C_public_memory_and_cursor=True,
            original_words_visited=len(visits&set(range(source.ENTRY,source.ENTRY+1384,4))),
            no_byte_exact_or_hardware_FCSR_claim=True)

    def test_02_native32_O2_O0_UBSan_and_effective_controls(self):
        harness=self.out/'native-harness.c'
        harness.write_text(native_harness())
        exits={}
        for label,opt,body,valid in [('O2','-O2',source.SELECTED,True),('O0','-O0',source.SELECTED,True)]+[
                (n,'-O2',b,False) for n,b in controls().items()]:
            path=self.out/'native-selected.c'
            path.write_text(types()+source.previous.DECLARATIONS+source.DECLARATIONS+body)
            exe=self.out/('native-'+label)
            r=subprocess.run([*native_command(opt,valid),str(path),str(harness),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr[:3000])
            r=subprocess.run([str(exe)],timeout=90)
            self.assertIn(r.returncode,(0,) if valid else tuple(range(20,25)),label)
            exits[label]=r.returncode
        self.receipt('native',geometry_cases=sum(1 for _ in cases()),animation_cases_per_selected=8*2*256*256,
            separate_units_real_SDK_O2_O0_UBSan=True,exits=exits)

    def test_03_eighteen_neighbors_and_explicit_nonmatch(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['diagnostics']),
            (345,136,331,''))
        self.assertFalse(self.row['pools'])
        self.assertNotEqual(self.words,self.truth)
        obj,diag=source.build.compile_owner(self.root,self.out,(self.out/'before-packet_owner').read_text(),'neighbor-baseline')
        self.assertFalse(diag)
        old,new=parse_object(obj),parse_object(self.obj)
        self.assertEqual(set(old[1]),set(new[1]))
        for name,f in old[1].items():
            if name==source.FUNCTION:
                continue
            g=new[1][name]
            self.assertEqual(old[0][f['value']:f['value']+f['size']],new[0][g['value']:g['value']+g['size']],name)
            relative=lambda o,f:{a-f['value']:v for a,v in o[2].items() if f['value']<=a<f['value']+f['size']}
            self.assertEqual(relative(old,f),relative(new,g),name)
        self.assertEqual(len(old[1])-1,18)
        self.receipt('shape',words=345,frame=136,retail_words=346,unresolved_differences=331,
            neighbors=18,new_target_guards=0,raw_match=False)

    def test_04_guest_aliases_preserve_live_descriptor_and_color_reads(self):
        count=0
        for alias,flip,inset,tint,phase in itertools.product(range(5),(0,3),(0,1),(0,1),(0,8)):
            memory,args=guest.fixture(flip=flip,tint=tint,animation=0x81,frame=127,speed=255,timestep=255,
                offsets=(-137,inset,5))
            output=(guest.OUTPUT,guest.DESCRIPTOR,guest.PACKET+24,guest.GLOBALS[4],guest.COLORS[0])[alias]
            for i in range(64):
                memory.setdefault(output+i,0xA5)
            args=(output,*args[1:])
            expected,cursor,trap=guest.reference(memory,args)
            self.assertIsNone(trap)
            for words in (self.truth,self.words):
                m=guest.RectangleOracle(words,memory,args,phase=phase).run()
                self.assertEqual((guest.base.public(m.memory),m.r[2]),(guest.base.public(expected),cursor),
                    (alias,flip,inset,tint,phase))
            count+=1
        self.receipt('aliases',paired_cases=count,flat_guest_aliases_only=True,
            descriptor_reloads_and_global_snapshot_and_color_store_order=True,no_portable_C_alias_claim=True)

    def test_05_guest_division_traps_and_nonfinite_conversion_scope(self):
        count=0
        for scales,divisor,inset in itertools.product(((.5,3.25),(2.5,.5),(-1.,3.25),(2.5,-1.)),
                (4096.,-2097152.),(0,1)):
            memory,args=guest.fixture((*scales,-4.75,-2.125,divisor,32.5,20.25),offsets=(0,inset,0))
            expected,cursor,trap=guest.reference(memory,args)
            for words in (self.truth,self.words):
                m=guest.RectangleOracle(words,memory,args)
                if trap:
                    with self.assertRaises(guest.ArithmeticTrap) as raised:
                        m.run()
                    self.assertEqual(raised.exception.code,trap)
                else:
                    m.run()
                    self.assertEqual(m.r[2],cursor)
                self.assertEqual(guest.base.public(m.memory),guest.base.public(expected))
            count+=1
        special=0
        for divisor in (0.,-0.,float('inf'),float('-inf'),float('nan')):
            memory,args=guest.fixture((2.5,3.25,-4.75,-2.125,divisor,32.5,20.25))
            expected,cursor,trap=guest.reference(memory,args)
            self.assertIsNone(trap)
            for words in (self.truth,self.words):
                m=guest.RectangleOracle(words,memory,args).run()
                self.assertEqual((guest.base.public(m.memory),m.r[2]),(guest.base.public(expected),cursor))
            special+=1
        self.receipt('traps',arithmetic_pairs=count,special_float_pairs=special,
            real_BREAK_6_7_classification_and_public_writes=True,
            exceptional_DIV_LO_HI_and_full_hardware_FCSR_or_portable_invalid_C_cast_not_claimed=True)

    def test_06_effective_compiled_guest_controls(self):
        rejected=[]
        samples=list(cases())
        for label,body in controls().items():
            _,words,_=source.measure(self.root,self.out,'negative-'+label,body)
            for memory,args in samples:
                expected,cursor,trap=guest.reference(memory,args)
                self.assertIsNone(trap)
                m=guest.RectangleOracle(words,memory,args).run()
                if (guest.base.public(m.memory),m.r[2])!=(guest.base.public(expected),cursor):
                    rejected.append(label)
                    break
            else:
                self.fail('Ineffective compiled guest control: '+label)
        self.receipt('negatives',compiled_observable_rejections=rejected,
            no_compile_failures_or_unsupported_instructions_accepted=True)

    def test_07_original_animation_loop_and_both_pingpong_directions(self):
        count=0
        for flags,old,speed,time in itertools.product((0,1,2,127,128,129,130,255),
                (0,7,8,127,128,129,255),(0,1,17,255),(0,1,255)):
            memory,args=guest.fixture(animation=flags,frame=old,speed=speed,timestep=time)
            expected,cursor,trap=guest.reference(memory,args)
            self.assertIsNone(trap)
            self.assertEqual(guest.read(expected,guest.PACKET+12,1),guest.animation_result(old,speed*time,flags))
            for words in (self.truth,self.words):
                m=guest.RectangleOracle(words,memory,args).run()
                self.assertEqual((guest.base.public(m.memory),m.r[2]),(guest.base.public(expected),cursor))
            count+=1
        self.receipt('animation',original_and_raw_C_pairs=count,independent_byte_formula=True)

    def test_08_physical_object_and_all_input_corruption_controls(self):
        source.checked_object(self.obj)
        text,funcs,rel=parse_object(self.obj)
        f=funcs[source.FUNCTION]
        for i in range(345):
            bad=bytearray(text)
            bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),funcs,rel)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        for at in source.RELOCATIONS:
            bad=dict(rel)
            bad[f['value']+at]=[(rel[f['value']+at][0][0],'wrong')]
            with patch.object(source,'parse_object',return_value=(text,funcs,bad)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        with patch.object(source,'sections',return_value={'.rodata':(0,b'x')}):
            with self.assertRaises(ValueError):
                source.checked_object(self.obj)
        rb=Path.read_bytes
        for key in source.PATHS:
            path=self.out/('before-'+key)
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                with self.assertRaisesRegex(ValueError,'fixture'):
                    source.freeze(self.root,self.out)
        self.receipt('corruptions',raw_words=345,bindings=len(source.RELOCATIONS),extra_pool=True,frozen_inputs=len(source.PATHS))

    def test_09_original_and_C_independent_symbol_rebases(self):
        original=(self.out/'before-packet_original').read_text()
        inner=original.split('glabel '+source.FUNCTION+'\n',1)[1].split('endlabel '+source.FUNCTION,1)[0]
        path=self.out/'original.s'
        path.write_text('.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\n'+
            '.type '+source.FUNCTION+', @function\nglabel '+source.FUNCTION+'\n'+inner+
            '\n.size '+source.FUNCTION+', . - '+source.FUNCTION+'\n')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        names=sorted({name for entries in source.RELOCATIONS.values() for _,name in entries})
        count=0
        for number,delta in enumerate((0,0x10000,0x20000)):
            links={name:0x80207FF8+i*0x10000+delta for i,name in enumerate(names)}
            entry=0x15200000+delta
            streams=[]
            for variant,obj in enumerate((path.with_suffix('.o'),self.obj)):
                data,funcs,rel=parse_object(obj)
                f=funcs[source.FUNCTION]
                bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
                asm,missing=emit_function(data[f['value']:f['value']+f['size']],dict(value=0,size=f['size']),bindings,source.FUNCTION,links)
                self.assertFalse(missing)
                file=self.out/('rebase-%d-%d.s'%(number,variant))
                file.write_text(asm)
                file.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(file.with_suffix('.o')),str(file)],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(file.with_suffix('.ld')),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in links.items()],'-o',str(file.with_suffix('.elf')),str(file.with_suffix('.o'))],check=True,capture_output=True)
                streams.append(struct.unpack_from('>%dI'%(f['size']//4),sections(file.with_suffix('.elf'))['.text'][1]))
            sizes={int(n[2:],16):1 if n in ('D_800D2DA8','D_800D2DA9','D_800D2DAA','D_800D2DAB','D_800BE9A0') else 4 for n in names}
            addresses={int(n[2:],16):v for n,v in links.items()}
            remap=lambda m:{next((new+a-old for old,new in addresses.items() if old<=a<old+sizes[old]),a):v for a,v in m.items()}
            for flip,inset,tint,phase in itertools.product((0,3),(0,1),(0,1),(0,8)):
                memory,args=guest.fixture(flip=flip,tint=tint,animation=129,frame=127,speed=255,timestep=255,offsets=(17,inset,-5))
                expected,cursor,trap=guest.reference(memory,args)
                self.assertIsNone(trap)
                for words in streams:
                    m=guest.RectangleOracle(words,remap(memory),args,phase=phase,entry=entry).run()
                    self.assertEqual((guest.base.public(m.memory),m.r[2]),(guest.base.public(remap(expected)),cursor))
                count+=1
        self.receipt('rebases',sets=3,paired_runs=count,external_symbols=len(names),entry_changed=True,
            public_memory_and_cursor_only=True,no_raw_private_state_equality_claim=True)

    def test_10_connected_real_visibility_caller_and_renderer(self):
        class Connected(guest.RectangleOracle):
            def record_call(model,target):
                self.assertIn(target,(source.previous.ENTRY,source.ENTRY))

            def hook(model,target):
                raise AssertionError(('unexpected unconnected provider',hex(target)))

        caller=struct.unpack_from('>30I',self.rom,0xC2F40)
        visibility=struct.unpack_from('>129I',self.rom,source.previous.ROM)
        count=0
        for extent,position,flip,inset,phase in itertools.product((0,8),((0.,0.),(1000.,1000.)),(0,3),(0,1),(0,8)):
            memory,args=guest.fixture(flip=flip,animation=129,frame=127,speed=17,timestep=3)
            guest.put(memory,guest.PACKET+6,extent,2)
            guest.put(memory,guest.PACKET+8,8,2)
            active=guest.STACK+phase-4
            inputs=(guest.OUTPUT,guest.PACKET,*(guest.bits(v) for v in position),guest.bits(4096.),1,17,inset,-5)
            expected=guest.visibility.reference(memory,(guest.PACKET,*inputs[2:5],1,active))
            cursor=guest.OUTPUT
            if guest.read(expected,active):
                expected,cursor,trap=guest.reference(expected,(cursor,guest.PACKET,17,inset&0xFFFFFFFF,(-5)&0xFFFFFFFF))
                self.assertIsNone(trap)
            for words in (self.truth,self.words):
                connected=dict(zip(range(source.previous.ENTRY,source.previous.ENTRY+516,4),visibility))
                connected.update(zip(range(source.ENTRY,source.ENTRY+len(words)*4,4),words))
                m=Connected(caller,memory,inputs,entry=0x15095A90,phase=phase,connected=connected).run()
                self.assertEqual((guest.base.public(m.memory),m.r[2]),(guest.base.public(expected),cursor))
            count+=1
        self.receipt('connections',paired_sequences=count,real_visibility_and_caller_and_renderer=True,
            no_host_renderer_or_gameplay_claim=True)

    def test_11_first_full_image_prediction_uses_emitted_C_not_retail(self):
        row=source.prelink_prediction(self.root,self.out)
        self.assertEqual((row['metadata_exclusions'],row['metadata_serialization_bytes'],row['raw_match']),(0,18,False))
        self.assertEqual(row['after'],{k:hashlib.sha256(v).hexdigest() for k,v in source.expected_inputs(self.root,self.out).items()})
        slot=(self.out/'predicted-slot.bin').read_bytes()
        self.assertEqual(slot,struct.pack('>345I',*self.words)+b'\0'*4)
        self.assertNotEqual(slot,self.rom[source.ROM:source.ROM+1384])
        for at in (0,4,1376,1380):
            bad=bytearray(slot)
            bad[at]^=1
            with self.assertRaises(ValueError):
                source.candidate_slot(bytes(bad))
        structural=source.slot_expected_image((self.out/'before-elf').read_bytes(),slot)
        self.assertEqual((self.out/'slot-only-rejected.elf').read_bytes(),structural)
        bad=bytearray(structural)
        bad[0]^=1
        with self.assertRaises(ValueError):
            source.serialize_symbols(bytes(bad))
        self.receipt('scope',inputs=100,unchanged_inputs=98,prediction=row)


if __name__=='__main__':
    unittest.main()
