"""Packet visibility ABI, precise FP dataflow, native32 and whole-image scope."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_packet_visibility as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests import game_packet_visibility_oracle as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_one_shot_timer_match import canonical_symbols


def controls():
    body=source.SELECTED
    return {
        'signed-dimension':body.replace('(f32)(u32)descriptor->unk4','(f32)(s16)descriptor->unk4'),
        'unsigned-extent':body.replace('extentX = packet->extentX','extentX = (u16)packet->extentX'),
        'byte-clear':body.replace('*visible = 0;','*(u8 *)visible = 0;'),
        'byte-mode':body.replace('projected != 0','(u8)projected != 0'),
        'wrong-view-stride':body.replace('(ProjectedViewFrame95760 *)D_800BE628 + D_80082FA4',
            '(ProjectedViewFrame95760 *)(D_800BE628 + D_80082FA4 * 0x100)'),
        'exclusive-left-bound':body.replace('view->clipLeft <= x + width','view->clipLeft < x + width'),
        'inclusive-right-bound':body.replace('x < view->clipRight','x <= view->clipRight'),
        'missing-width-output':body.replace('D_800D2C84 = width;','D_800D2C84 = 0.0f;'),
        'wrong-reciprocal':body.replace('inverse = 1.0f / divisor;','inverse = divisor;'),
    }


def cases():
    for extents,dimensions,mode,frame,scales,divisor,position in itertools.product(
            ((0,1),(1,0),(1,1),(-32768,32767),(32767,-1)),
            ((0,0),(1,2),(32768,65535),(65535,32768)),(0,1,0x100,0xFFFFFFFF),(0,1),
            ((1.,1.),(-.5,2.)),(2.,-4.),((0.,0.),(1000000.,-1000000.))):
        yield guest.fixture(extents,dimensions,position,divisor,mode,frame,scales)
    for mode,frame in itertools.product((0,1),(0,1)):
        memory,args=guest.fixture(projected=mode,frame=frame)
        expected=guest.reference(memory,args)
        width,height=[guest.floating(guest.read(expected,guest.OUTPUT+i)) for i in (20,24)]
        for x,y in ((-100.-width/2,0.),(100.+width/2,0.),(0.,-80.-height/2),(0.,80.+height/2)):
            yield guest.fixture(position=(x,y),projected=mode,frame=frame)


def types():
    descriptor='''typedef struct {u32 unk0;u16 unk4,unk6;u8 unk8,unk9,unkA,unkB;} structC1D70Descriptor;
'''
    view=source.previous.previous.VIEW.replace('    u8 padding14[0x20];',source.VIEW_FIELDS)
    return '#include <ultra64.h>\n'+descriptor+view+source.PACKET


def native_harness():
    rows=[]
    for memory,args in cases():
        expected=guest.reference(memory,args)
        values=[guest.base.half(guest.read(memory,guest.PACKET+i,2)) for i in (6,8)]
        dims=[guest.read(memory,guest.DESCRIPTOR+i,2) for i in (4,6)]
        words=[*args[1:4],guest.read(memory,guest.SCALE_X),guest.read(memory,guest.SCALE_Y),
            args[4],guest.read(memory,guest.base.source.FRAME_INDEX),guest.read(expected,args[5]),
            *[guest.read(expected,guest.OUTPUT+i*4) for i in range(7)]]
        rows.append('{{%s},{%s},{%s},{%s},%s}'%(','.join(map(str,values)),','.join(map(str,dims)),
            ','.join('0x%Xu'%v for v in words[:3]),','.join('0x%Xu'%v for v in words[3:5]),
            ','.join('0x%Xu'%v for v in words[5:])))
    return types()+r'''
f32 D_800380A0,D_800380A4,D_800D2C70,D_800D2C74,D_800D2C78,D_800D2C7C,D_800D2C80,D_800D2C84,D_800D2C88;
s32 D_80082FA4;u8 *D_800BE628;
static ProjectedViewFrame95760 frames[2];static ProjectedPacket95B08 packet;static structC1D70Descriptor descriptor;
static f32*outputs[]={&D_800D2C70,&D_800D2C74,&D_800D2C78,&D_800D2C7C,&D_800D2C80,&D_800D2C84,&D_800D2C88};
struct Case{s16 extents[2];u16 dimensions[2];u32 input[3],scales[2],mode,frame,visible,output[7];};
static const struct Case cases[]={ROWS};
void func_15095B08(s32,f32,f32,f32,s32,s32*);
static f32 real(u32 b){union{u32 b;f32 f;}v;v.b=b;return v.f;}
static u32 word(f32 f){union{u32 b;f32 f;}v;v.f=f;return v.b;}
static int run(void){u32 n,i;const struct Case*c;s32 visible;
 if(sizeof(void*)!=4||sizeof(ProjectedPacket95B08)!=20||sizeof(ProjectedViewFrame95760)!=0x180||
 __builtin_offsetof(ProjectedPacket95B08,descriptor)!=16||__builtin_offsetof(ProjectedViewFrame95760,clipLeft)!=0x2C)return 29;
 for(i=0;i<2;i++){frames[i].flatScaleX=.25f+i*.5f;frames[i].flatScaleY=.5f+i*.25f;
 frames[i].projectedScaleX=1.25f+i*.5f;frames[i].projectedScaleY=2.f+i*.75f;
 frames[i].clipTop=-80.f;frames[i].clipBottom=80.f;frames[i].clipLeft=-100.f;frames[i].clipRight=100.f;}
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];
 D_800BE628=(u8*)frames;D_80082FA4=(s32)c->frame;D_800380A0=real(c->scales[0]);D_800380A4=real(c->scales[1]);
 packet.extentX=c->extents[0];packet.extentY=c->extents[1];descriptor.unk4=c->dimensions[0];descriptor.unk6=c->dimensions[1];
 packet.descriptor=packet.extentX&&packet.extentY?&descriptor:(void*)0;
 for(i=0;i<7;i++)*outputs[i]=real(0xA5A5A5A5u);visible=0x12345678;
 func_15095B08((s32)&packet,real(c->input[0]),real(c->input[1]),real(c->input[2]),(s32)c->mode,&visible);
 if((u32)visible!=c->visible)return 20;
 for(i=0;i<7;i++)if(word(*outputs[i])!=c->output[i])return 21;
 }return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''.replace('ROWS',',\n'.join(rows))


class PacketVisibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>129I',cls.rom,source.ROM))
        data,functions=source.build.link_owner(cls.root,cls.out,cls.padded,source.OWNER)
        cls.normalized=list(struct.unpack_from('>129I',data,functions[source.FUNCTION]['value']))

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_shape_eighteen_neighbors_and_FP_dataflow(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['guards']),(129,24,7))
        self.assertEqual(self.normalized,self.truth)
        self.assertEqual(source.initial_dag(self.words),source.initial_dag(self.truth))
        bad=list(self.words)
        word=bad[0x5C//4]
        bad[0x5C//4]=(word&~((31<<16)|(31<<11)))|((word>>16&31)<<11)|((word>>11&31)<<16)
        self.assertNotEqual(source.initial_dag(bad),source.initial_dag(self.truth))
        bad=list(self.words)
        bad[0x70//4]=0x44085000
        with self.assertRaisesRegex(ValueError,'remains live'):
            source.closed_scratch(bad)
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
        self.receipt('shape',words=129,frame=24,guards=7,neighbors=18,
            exact_initial_expression_trees_memory_order=True,all_downstream_scratch_paths_closed=True,
            effective_DAG_and_live_scratch_controls=True)

    def test_02_native32_O2_O0_UBSan_and_effective_controls(self):
        harness=self.out/'native-harness.c'
        harness.write_text(native_harness())
        exits={}
        for label,opt,body,valid in [('O2','-O2',source.SELECTED,True),('O0','-O0',source.SELECTED,True)]+[
                (n,'-O2',b,False) for n,b in controls().items()]:
            path=self.out/'native-selected.c'
            path.write_text(types()+source.DECLARATIONS+'extern s32 D_80082FA4;extern u8 *D_800BE628;\n'+body)
            exe=self.out/('native-'+label)
            r=subprocess.run([*native_command(opt,valid),'-Wno-missing-braces',str(path),str(harness),'-o',str(exe)],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr[:2500])
            r=subprocess.run([str(exe)],timeout=30)
            self.assertIn(r.returncode,(0,) if valid else (20,21),label)
            exits[label]=r.returncode
        self.receipt('native',cases_per_selected=sum(1 for _ in cases()),real_SDK_types=True,separate_units=True,
            O2_O0_UBSan=True,finite_nonzero_divisors_no_native_alias_or_FCSR_claim=True,exits=exits)

    def test_03_complete_public_outputs_aliases_early_exits_and_boundaries(self):
        count=0
        visits=set()
        for memory,args in cases():
            expected=guest.reference(memory,args)
            for phase,words in itertools.product((0,8),(self.truth,self.words)):
                m=guest.run(words,memory,args,phase)
                self.assertEqual(guest.base.public(m.memory),guest.base.public(expected))
                self.assertFalse(m.calls)
                visits.update(m.visits)
            count+=1
        aliases=0
        for alias,mode,phase in itertools.product(range(8),(0,1),(0,8)):
            memory,args=guest.fixture(projected=mode,alias=alias,frame=1)
            expected=guest.reference(memory,args)
            for words in (self.truth,self.words):
                self.assertEqual(guest.base.public(guest.run(words,memory,args,phase).memory),guest.base.public(expected))
            aliases+=1
        for extents in ((0,1),(1,0)):
            memory,args=guest.fixture(extents=extents)
            guest.put(memory,guest.PACKET+16,0)
            for words in (self.truth,self.words):
                self.assertEqual(guest.base.public(guest.run(words,memory,args).memory),guest.base.public(guest.reference(memory,args)))
        self.receipt('sequences',cases=count,stack_phases=2,alias_pairs=aliases,
            target_words_visited=len(visits&set(range(source.ENTRY,source.ENTRY+516,4))),
            NULL_descriptor_early_exit=True,void_return_not_compared=True,guest_aliases_not_portable_C_claim=True)

    def test_04_nonfinite_division_guest_only_and_fired_fault_prefixes(self):
        special=0
        for divisor,x in itertools.product((0.,-0.,float('inf'),float('-inf'),float('nan')),(0.,float('nan'))):
            memory,args=guest.fixture(divisor=divisor,position=(x,0.))
            expected=guest.reference(memory,args)
            for words in (self.truth,self.words):
                self.assertEqual(guest.base.public(guest.run(words,memory,args).memory),guest.base.public(expected))
            special+=1
        faults=0
        for extents,phase in itertools.product(((0,1),(1,0),(1,1)),(0,8)):
            memory,args=guest.fixture(extents=extents)
            complete=guest.run(self.truth,memory,args,phase)
            for fault in range(complete.accesses):
                models=[]
                for words in (self.truth,self.normalized):
                    m=guest.base.edge.EdgeOracle(words,memory,args,phase=phase,entry=source.ENTRY,fault=fault)
                    with self.assertRaises(guest.base.edge.AccessFault):
                        m.run()
                    self.assertEqual(m.accesses,fault)
                    models.append(m)
                self.assertEqual(guest.base.edge.state(models[0]),guest.base.edge.state(models[1]))
                faults+=1
        self.receipt('faults',special_guest_pairs=special,fired_literal_normalized_prefix_pairs=faults,
            hardware_FCSR_flags_traps_NaN_payload_and_raw_C_fault_state_not_claimed=True)

    def test_05_effective_compiled_guest_negatives(self):
        rejected=[]
        samples=list(cases())
        for label,body in controls().items():
            _,words,_=source.measure(self.root,self.out,'negative-'+label,body)
            for memory,args in samples:
                expected=guest.reference(memory,args)
                if guest.base.public(guest.run(words,memory,args).memory)!=guest.base.public(expected):
                    rejected.append(label)
                    break
            else:
                self.fail('Ineffective compiled guest control: '+label)
        self.receipt('negatives',compiled_observable_rejections=rejected,
            no_compile_failures_or_unsupported_instructions_accepted=True)

    def test_06_physical_words_all_bindings_guards_and_proof_corruptions(self):
        text,funcs,rel=parse_object(self.obj)
        f=funcs[source.FUNCTION]
        for i in range(129):
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
        guards=(self.out/'proposed-guards.csv').read_bytes()
        for at,(expected,_) in source.GUARDS.items():
            mask=0xFFFF0000 if at in source.RELOCATIONS else 0xFFFFFFFF
            old=('%s,0x%X,0x%08X'%(source.FUNCTION,at,expected&mask)).encode()
            new=('%s,0x%X,0x%08X'%(source.FUNCTION,at,(expected&mask)^1)).encode()
            bad=guards.replace(old,new)
            self.assertNotEqual(bad,guards)
            path=self.out/'bad-guard.csv'
            path.write_bytes(bad)
            with self.assertRaises(ValueError):
                emit_padded_assembly(self.obj,self.root/source.PATHS['packet_original'],filename=source.OWNER,word_patches_path=path)
        self.receipt('corruptions',raw_words=129,bindings=len(source.RELOCATIONS),guards=7)

    def test_07_full_prediction_and_all_98_fixtures(self):
        row=source.prelink_prediction(self.root,self.out)
        self.assertEqual((row['changed_ELF_bytes'],row['metadata_exclusions'],row['metadata_serialization_bytes']),(551,0,157))
        expected=source.expected_inputs(self.root,self.out)
        self.assertEqual(row['after'],{k:hashlib.sha256(v).hexdigest() for k,v in expected.items()})
        structural=source.slot_expected_image((self.out/'before-elf').read_bytes(),self.rom)
        self.assertEqual(canonical_symbols(structural),canonical_symbols(expected['elf']))
        self.assertEqual((self.out/'slot-only-rejected.elf').read_bytes(),structural)
        for at in (0,2803712+4,2897120+4,2913808+4,2927088+4,2928096+4,2970400+4,2995008+4):
            bad=bytearray(structural)
            bad[at]^=1
            with self.assertRaises(ValueError):
                source.serialize_symbols(bytes(bad))
        self.assertEqual(len(source.PATHS),98)
        rb=Path.read_bytes
        for key in source.PATHS:
            path=self.out/('before-'+key)
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                with self.assertRaisesRegex(ValueError,'fixture'):
                    source.freeze(self.root,self.out)
        self.receipt('scope',inputs=98,unchanged_inputs=95,prediction=row)

    def test_08_independent_original_rebases_and_connected_provider(self):
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
            streams=[]
            entry=0x15200000+delta
            for variant,obj in enumerate((path.with_suffix('.o'),self.padded)):
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
                streams.append(struct.unpack_from('>129I',sections(file.with_suffix('.elf'))['.text'][1]))
            self.assertEqual(*streams)
            addresses={int(name[2:],16):value for name,value in links.items()}
            remap=lambda m:{next((new+a-old for old,new in addresses.items() if old<=a<old+4),a):v for a,v in m.items()}
            for mode,frame,phase,extents in itertools.product((0,1),(0,1),(0,8),((0,1),(1,1))):
                memory,args=guest.fixture(projected=mode,frame=frame,extents=extents)
                expected=remap(guest.reference(memory,args))
                models=[guest.base.edge.EdgeOracle(words,remap(memory),args,phase=phase,entry=entry).run() for words in streams]
                self.assertEqual(guest.base.public(models[0].memory),guest.base.public(expected))
                self.assertEqual(guest.base.edge.state(models[0]),guest.base.edge.state(models[1]))
                count+=1
        self.receipt('rebases',sets=3,paired_runs=count,external_symbols=len(names),entry_changed=True)

    def test_09_real_projection_depth_visibility_connection(self):
        depth_words=list(struct.unpack_from('>102I',self.rom,source.previous.ROM))
        projection=struct.unpack_from('>73I',self.rom,0xC2AEC)
        count=0
        for w,extent,bounds,phase,frame in itertools.product((1.,2.,4000.),(0,1),(100.,10000.),(0,8),(0,1)):
            memory,leaf_args=guest.fixture(extents=(extent,1),frame=frame)
            for i in range(2):
                for at,v in ((0x24,-bounds),(0x28,bounds),(0x2C,-bounds),(0x30,bounds)):
                    guest.put(memory,guest.base.VIEWS+i*0x180+at,guest.bits(v))
            args=(guest.base.OUTPUT,guest.PACKET,guest.STATUS)
            transformed=tuple(map(guest.bits,(17.25,-91.5,100.,w)))
            expected,result=guest.connected_reference(memory,args,transformed,phase)
            for leaf in (self.truth,self.words):
                connected=dict(zip(range(0x1509563C,0x15095760,4),projection))
                connected.update(zip(range(source.ENTRY,source.ENTRY+516,4),leaf))
                m=guest.depth.VisibleDepthOracle(depth_words,memory,args,transformed,phase=phase,connected=connected).run()
                self.assertEqual((guest.base.public(m.memory),m.r[2]),(guest.base.public(expected),result))
            count+=1
        self.receipt('connections',paired_sequences=count,real_projector_and_depth_routine_and_visibility_provider=True,
            matrix_provider_bounded=True,no_host_renderer_or_full_gameplay_claim=True)


if __name__=='__main__':
    unittest.main()
