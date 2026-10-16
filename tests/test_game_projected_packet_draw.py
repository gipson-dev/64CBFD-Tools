"""Joint ABI recovery, guarded data flow, native SDK macros, and isolated scope."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_projected_packet_draw as source
from tools.pad_generated_object import parse_object
from tools.tests import game_projected_packet_oracle as guest
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_record_constructor_match import elf_slot_offset


def controls():
    p,b = source.SELECTED_PROJECTOR,source.SELECTED
    return {
        'unsigned-coordinate': (p,b.replace('packet[0], packet[1], packet[2]', '(u16)packet[0], packet[1], packet[2]')),
        'wrong-coordinate-stride': (p,b.replace('packet[0], packet[1], packet[2]', 'packet[0], packet[1], packet[4]')),
        'wrong-depth-scale': (p,b.replace('* 32.0f','* 16.0f')),
        'wrong-viewport-component': (p,b.replace('.vp.vscale[2]','.vp.vscale[1]')),
        'wrong-draw-flag': (p,b.replace('divisor, 1, 0, 0, 0','divisor, 0, 0, 0, 0')),
        'ignored-projection-rejection': (p,b.replace('4000.0f) == 0','4000.0f) == 7')),
        'upper-bound-equality': (p.replace('maximum <= transformedW','maximum < transformedW'),b),
        'near-bound-equality': (p.replace('transformedW <= D_800D9B20','transformedW < D_800D9B20'),b),
    }


def native_command(opt,valid=True):
    flags = ['cc','-m32',opt,'-std=gnu99','-ffreestanding','-nostdlib','-static','-fno-pie','-no-pie',
        '-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard',
        '-Wall','-Wextra','-Werror','-Wno-unknown-pragmas','-Wno-unused-parameter','-Wno-misleading-indentation',
        '-D_LANGUAGE_C','-D_FINALROM','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32','-nostdinc',
        '-I','conker/include','-I','conker/include/2.0L','-I','conker/include/2.0L/PR','-I','conker/include/libc']
    return flags+(['-fsanitize=undefined','-fsanitize-undefined-trap-on-error'] if valid else [])


def native_rows():
    rows = []
    for coords,w,frame,view,mode in itertools.product(((-32768,0,32767),(32767,-12345,-32768),(17,-91,255)),
            (1.,1.5,2.,3999.,4000.,4096.),(0,1),(0,3),(0,1)):
        pz = (-2.5,.25,100.)[coords[0]%3]
        memory,args,transformed = guest.fixture(coords,(17.25,-91.5,pz,w),frame,view)
        output_addresses = (0x30100,0x30104,0x30108,0x3010C)
        expected,active = guest.project_reference(memory,output_addresses,transformed,mode=mode)
        drawn,_,_ = guest.draw_reference(memory,args,transformed,mode=mode)
        rows.append('{ {%s}, {%s}, %d,%d,%d,%d, {%s},0x%Xu }'%(','.join(map(str,coords)),
            ','.join('0x%Xu'%b for b in transformed),frame,view,mode,active,
            ','.join('0x%Xu'%guest.read(expected,a) for a in output_addresses),guest.read(drawn,guest.OUTPUT+12)))
    return rows


def native_harness():
    return '#include <ultra64.h>\n'+source.VIEW+r'''
struct Case{s16 coords[3];u32 transformed[4];u32 frame,view,mode,active,outputs[4],depthWord;};
static const struct Case cases[]={ROWS};static const struct Case*c;
s32 D_80082FA4;u8*D_800BE628;u8 D_800BE9C0;f32 D_800D2CA8[2][4][4];f32 D_800D9B20;
static ProjectedViewFrame95760 frames[2];static s16 packet[24];static Gfx output[16];static u32 calls,error;
static f32 real(u32 b){union{u32 b;f32 f;}v;v.b=b;return v.f;}
static u32 word(f32 f){union{u32 b;f32 f;}v;v.f=f;return v.b;}
void func_150A7A00(f32 m[4][4],f32 x,f32 y,f32 z,f32*a,f32*b,f32*d,f32*w){
 if(m!=D_800D2CA8[c->frame]||x!=(f32)c->coords[0]||y!=(f32)c->coords[1]||z!=(f32)c->coords[2])error=20;
 *a=real(c->transformed[0]);*b=real(c->transformed[1]);*d=real(c->transformed[2]);*w=real(c->transformed[3]);calls++;
 if(c->mode){D_80082FA4^=1;D_800BE9C0=D_800BE9C0==0?3:0;}}
s32 func_15095A90(s32 out,s32 p,f32 x,f32 y,f32 w,s32 flags,s32 a,s32 b,s32 d){
 if(!c->active||out!=(s32)(output+2)||p!=(s32)packet||word(x)!=c->outputs[0]||word(y)!=c->outputs[1]||
 word(w)!=c->outputs[3]||flags!=1||a||b||d)error=21;calls++;return (s32)(output+3);}
s32 func_1509563C(f32,f32,f32,f32*,f32*,f32*,f32*,f32);Gfx*func_15095760(Gfx*,s16*);
static void setup(void){u32 i,j;for(i=0;i<2;i++){
 frames[i].scaleX=17.25f+i*13.5f;frames[i].scaleY=-23.125f+i*4.75f;
 frames[i].translateX=311.5f-i*17.25f;frames[i].translateY=199.25f+i*31.5f;
 for(j=0;j<4;j++){frames[i].viewports[j].vp.vscale[2]=j==0?-32768:32767;
 frames[i].viewports[j].vp.vtrans[2]=j==0?-16384:32767;}}
 for(i=0;i<24;i++)packet[i]=(s16)0xA5A5;for(i=0;i<3;i++)packet[i]=c->coords[i];
 for(i=0;i<16;i++)output[i].words.w0=output[i].words.w1=0xA5A5A5A5u;
 D_800BE628=(u8*)&frames;D_80082FA4=(s32)c->frame;D_800BE9C0=(u8)c->view;D_800D9B20=1.f;calls=error=0;}
static int run(void){u32 n,i;f32 out[4];s32 active;Gfx*end;
 if(sizeof(void*)!=4||sizeof(ProjectedViewFrame95760)!=0x180||sizeof(Vp)!=16||
 __builtin_offsetof(ProjectedViewFrame95760,viewports)!=0x40)return 29;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];setup();
 active=func_1509563C((f32)packet[0],(f32)packet[1],(f32)packet[2],out,out+1,out+2,out+3,4000.f);
 if(error||calls!=1||active!=(s32)c->active)return 22;
 for(i=0;i<4;i++)if(word(out[i])!=c->outputs[i])return 23;
 setup();end=func_15095760(output,packet);if(error||calls!=1+c->active)return 24;
 if(end!=output+(c->active?3:0))return 25;
 if(c->active){if(output[0].words.w0!=0xE7000000u||output[0].words.w1||
 output[1].words.w0!=0xEE000000u||output[1].words.w1!=c->depthWord)return 26;}
 else if(output[0].words.w0!=0xA5A5A5A5u||output[1].words.w1!=0xA5A5A5A5u)return 27;
 if(output[2].words.w0!=0xA5A5A5A5u)return 28;}return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''.replace('ROWS',',\n'.join(native_rows()))


class ProjectedPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/source.BUILD
        cls.obj,cls.padded,cls.words,cls.projection,cls.row = source.qualify(cls.root,cls.out)
        cls.rom = (cls.out/'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>84I',cls.rom,source.ROM))
        cls.project_truth = list(struct.unpack_from('>73I',cls.rom,0xC2AEC))

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_shape_all_seventeen_neighbors_and_closed_projection_dag(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(source.output_dag(self.projection),source.output_dag(self.project_truth))
        obj,diag = source.build.compile_owner(self.root,self.out,(self.out/'before-packet_owner').read_text(),'neighbor-baseline')
        self.assertFalse(diag)
        old,new = parse_object(obj),parse_object(self.obj)
        self.assertEqual(set(old[1]),set(new[1]))
        for name,f in old[1].items():
            if name in (source.FUNCTION,'func_1509563C'):
                continue
            g = new[1][name]
            self.assertEqual(old[0][f['value']:f['value']+f['size']],new[0][g['value']:g['value']+g['size']],name)
            relative = lambda o,f:{a-f['value']:v for a,v in o[2].items() if f['value']<=a<f['value']+f['size']}
            self.assertEqual(relative(old,f),relative(new,g),name)
        self.assertEqual(len(old[1])-2,17)
        self.receipt('shape',draw_words=84,draw_frame=72,project_words=73,project_frame=40,
            draw_guards=0,project_guards=10,neighbors=17,closed_IEEE_expression_trees_and_output_order=True)

    def test_02_native32_real_SDK_O2_O0_and_UBSan(self):
        harness = self.out/'native-harness.c'
        harness.write_text(native_harness())
        candidate = self.out/'native-selected.c'
        exits = {}
        for label,opt,p,b,valid in [('O2','-O2',source.SELECTED_PROJECTOR,source.SELECTED,True),
                ('O0','-O0',source.SELECTED_PROJECTOR,source.SELECTED,True)]+[
                (n,'-O2',p,b,False) for n,(p,b) in controls().items()]:
            body = b.replace('typedef struct { u8 prefix[0x40]; Vp viewports[20]; } ProjectedViewFrame95760;\n\n','')
            candidate.write_text('#include <ultra64.h>\ns32 func_15095A90(s32,s32,f32,f32,f32,s32,s32,s32,s32);\n'+
                source.DECLARATIONS+source.VIEW+p+body)
            exe = self.out/('native-'+label)
            r = subprocess.run([*native_command(opt,valid),str(candidate),str(harness),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr[:5000])
            r = subprocess.run([str(exe)],timeout=60)
            self.assertIn(r.returncode,(0,) if valid else tuple(range(20,29)),label)
            exits[label]=r.returncode
        self.receipt('native',cases_per_O2_O0=len(native_rows()),real_SDK_headers=True,separate_units=True,
            selected_UBSan=True,finite_nonzero_divisors_and_valid_signed_conversions=True,exits=exits)

    def test_03_paired_whole_sequences_live_view_changes_and_raw_C_outputs(self):
        count = 0
        visits = set()
        for coordinates,w,frame,view,phase,mode,alias in itertools.product(
                ((-32768,0,32767),(32767,-12345,-32768),(17,-91,255)),(1.,1.5,2.,3999.,4000.,4096.),
                (0,1),(0,3),(0,8),(0,1),(False,True)):
            memory,args,transformed = guest.fixture(coordinates,(17.25,-91.5,100.,w),frame,view,alias)
            expected,result,calls = guest.draw_reference(memory,args,transformed,phase,mode)
            models = []
            for draw,projection in ((self.truth,self.project_truth),(self.words,self.project_truth),(self.words,self.projection)):
                m = guest.ProjectionOracle(draw,memory,args,transformed,phase=phase,mode=mode,
                    connected=dict(zip(range(source.PROJECT,source.PROJECT+292,4),projection))).run()
                self.assertEqual((guest.public(m.memory),m.r[2],m.calls),(guest.public(expected),result,calls))
                models.append(m)
            self.assertEqual(guest.edge.state(models[0]),guest.edge.state(models[1]))
            visits.update(models[0].visits)
            count += 1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+336,4))<=visits)
        self.receipt('sequences',three_way_cases=count,all_84_draw_words_visited=True,
            raw_C_public_outputs=True,normalized_runtime_literal_state=True,guest_packet_output_aliases=True,
            no_full_FCSR_or_gameplay_claim=True)

    def test_04_direct_projector_output_aliases_and_clipping(self):
        count = 0
        for w,phase,mode,alias in itertools.product((1.,1.5,2.,4000.,4096.),(0,8),(0,1),range(4)):
            memory,_,transformed = guest.fixture(transformed=(17.25,-91.5,100.,w))
            base = 0x31000
            memory.update({base+i:0xA5 for i in range(32)})
            outputs = ((base,base+4,base+8,base+12),(base,base,base+8,base+12),
                (base,base+4,base+8,base),(guest.VIEWS+0xC,guest.VIEWS+0x10,base+8,base+12))[alias]
            expected,active = guest.project_reference(memory,outputs,transformed,mode=mode)
            for words in (self.project_truth,self.projection):
                args = (0,0,guest.bits(32767.),*outputs,guest.bits(4000.))
                m = guest.ProjectionOracle(words,memory,args,transformed,entry=source.PROJECT,phase=phase,mode=mode)
                m.f[12],m.f[14] = guest.bits(-32768.),guest.bits(0.)
                m.run()
                self.assertEqual((guest.public(m.memory),m.r[2]),(guest.public(expected),active))
            count += 1
        self.receipt('aliases',raw_original_C_pairs=count,overlapping_outputs_and_view_fields=True,
            both_outputs_read_before_either_store=True,native_stack_or_fault_claim=False)

    def test_05_effective_compiled_guest_negatives(self):
        cases = [((-32768,0,32767),w,view,z) for w,view,z in itertools.product((1.,1.5,2.,3.25,4000.),(0,3),(.25,100.))]
        rejected = []
        for name,(p,b) in controls().items():
            with patch.object(source,'SELECTED_PROJECTOR',p):
                obj,_,_ = source.measure(self.root,self.out,'negative-'+name,b)
            data,fs = source.build.link_owner(self.root,self.out,obj,source.OWNER)
            relocated_project = 0x15300000
            raw,funcs,rel = parse_object(obj)
            f = funcs[source.FUNCTION]
            relative = {a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
            links = dict(func_1509563C=relocated_project,func_15095A90=source.DRAW,
                D_80082FA4=source.FRAME_INDEX,D_800BE628=source.VIEW_BASE,D_800BE9C0=source.VIEW_INDEX)
            asm,missing = emit_function(raw[f['value']:f['value']+f['size']],dict(value=0,size=f['size']),
                relative,source.FUNCTION,links)
            self.assertFalse(missing)
            path = self.out/('negative-'+name+'-call.s')
            path.write_text(asm)
            path.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(path.with_suffix('.ld')),'-e',source.FUNCTION,
                *['--defsym=%s=0x%X'%v for v in links.items()],'-o',str(path.with_suffix('.elf')),str(path.with_suffix('.o'))],check=True,capture_output=True)
            draw = list(struct.unpack_from('>%dI'%(f['size']//4),sections(path.with_suffix('.elf'))['.text'][1]))
            info = fs['func_1509563C']
            projection = struct.unpack_from('>%dI'%(info['size']//4),data,info['value'])
            code = dict(zip(range(relocated_project,relocated_project+len(projection)*4,4),projection))
            for coords,w,view,z in cases:
                memory,args,transformed = guest.fixture(coords,(17.25,-91.5,z,w),view=view)
                expected,result,calls = guest.draw_reference(memory,args,transformed)
                m = guest.ProjectionOracle(draw,memory,args,transformed,connected=code,
                    bindings={relocated_project:source.PROJECT}).run()
                if (guest.public(m.memory),m.r[2],m.calls)!=(guest.public(expected),result,calls):
                    rejected.append(name)
                    break
            else:
                self.fail('Ineffective compiled negative: '+name)
        self.receipt('negatives',compiled_observable_rejections=rejected,unsupported_instruction_or_compile_failures_accepted=False)

    def test_06_normalized_instruction_fault_prefixes(self):
        count = 0
        for w,phase,alias in itertools.product((1.,2.),(0,8),(False,True)):
            memory,args,transformed = guest.fixture(transformed=(17.25,-91.5,100.,w),alias=alias)
            connected = dict(zip(range(source.PROJECT,source.PROJECT+292,4),self.project_truth))
            complete = guest.ProjectionOracle(self.truth,memory,args,transformed,phase=phase,connected=connected).run()
            for fault in range(complete.accesses):
                models = []
                for words in (self.truth,self.words):
                    m = guest.ProjectionOracle(words,memory,args,transformed,phase=phase,fault=fault,connected=connected)
                    with self.assertRaises(guest.edge.AccessFault):
                        m.run()
                    self.assertEqual(m.accesses,fault)
                    models.append(m)
                self.assertEqual(guest.edge.state(models[0]),guest.edge.state(models[1]))
                count += 1
        self.receipt('faults',fired_prefix_pairs=count,normalized_projection_words_literal_retail=True,
            emitted_guest_instruction_order_only=True)

    def test_07_raw_words_bindings_and_every_guard_are_fail_closed(self):
        measured = (self.obj,self.words,self.row)
        text,funcs,rel = parse_object(self.obj)
        for name,count in ((source.FUNCTION,84),('func_1509563C',73)):
            f = funcs[name]
            for i in range(count):
                bad = bytearray(text)
                bad[f['value']+i*4]^=1
                with patch.object(source,'measure',return_value=measured),patch.object(source,'parse_object',return_value=(bytes(bad),funcs,rel)):
                    with self.assertRaises(ValueError):
                        source.qualify(self.root,self.out)
            for at in (source.RELOCATIONS if count==84 else source.PROJECT_RELOCATIONS):
                bad = dict(rel)
                bad[f['value']+at]=[(rel[f['value']+at][0][0],'wrong')]
                with patch.object(source,'measure',return_value=measured),patch.object(source,'parse_object',return_value=(text,funcs,bad)):
                    with self.assertRaises(ValueError):
                        source.qualify(self.root,self.out)
        guards = (self.out/'proposed-guards.csv').read_bytes()
        self.assertEqual(guards,source.proposed_guards((self.out/'before-guards').read_bytes()))
        for at,(expected,replacement) in source.GUARDS.items():
            self.assertNotEqual(expected,replacement)
            bad = list(self.project_truth)
            bad[at//4]^=1
            try:
                mutated = source.output_dag(bad)
            except ValueError:
                continue
            self.assertNotEqual(source.output_dag(self.projection),mutated)
        self.receipt('corruptions',raw_words=157,bindings=19,guards=10,prior_guard_history_fixed=True)

    def test_08_preinstall_prediction_all_frozen_inputs(self):
        row = source.prelink_prediction(self.root,self.out)
        self.assertEqual((row['changed_ELF_bytes'],row['metadata_exclusions']),(490,0))
        expected = source.expected_inputs(self.root,self.out)
        self.assertEqual(row['after'],{k:hashlib.sha256(v).hexdigest() for k,v in expected.items()})
        live = {k:hashlib.sha256((self.root/p).read_bytes()).hexdigest() for k,p in source.PATHS.items()}
        self.assertIn(live,(source.BASELINE,dict(source.BASELINE,**row['after'])))
        rb = Path.read_bytes
        for key in source.PATHS:
            path = self.out/('before-'+key)
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                with self.assertRaisesRegex(ValueError,'fixture'):
                    source.freeze(self.root,self.out)
        self.receipt('scope',inputs=len(source.PATHS),unchanged_inputs=len(source.PATHS)-3,predicted=row)

    def test_09_original_caller_windows_and_current_placeholder_limit(self):
        class Stop(guest.ProjectionOracle):
            def record_call(self,target):
                assert target==source.ENTRY
                self.forwarded=self.arguments(2)
                raise guest.edge.CallBoundary
        image=(self.out/'before-elf').read_bytes()
        count=0
        for call,rom,start,count_words,offset in ((0x1516D980,0x19AE30,0x1516D980,2,0x84),
                (0x15167D68,0x195218,0x15167D64,3,0x5C),(0x15168640,0x195AF0,0x1516863C,3,0x94),
                (0x1502C5D4,0x59A84,0x1502C5CC,4,0x6C)):
            self.assertEqual(image[elf_slot_offset(image,call,8):][:8],bytes(8))
            data=self.rom[rom-(call-start):rom-(call-start)+count_words*4]
            words=list(struct.unpack('>%dI'%count_words,data))
            for phase,out in itertools.product((0,8),(guest.OUTPUT,guest.OUTPUT+32)):
                memory,args,transformed=guest.fixture()
                m=Stop(words,memory,(out,guest.STACK+phase+offset),transformed,entry=start,phase=phase)
                m.r[2]=out
                m.r[14]=32767
                m.f[4]=0xFFFF8001
                guest.put(m.memory,guest.STACK+phase+offset,-32768,2)
                with self.assertRaises(guest.edge.CallBoundary):
                    m.run()
                self.assertEqual(m.forwarded,(out,guest.STACK+phase+offset))
                if call==0x1502C5D4:
                    self.assertEqual([guest.half(guest.read(m.memory,m.forwarded[1]+i*2,2)) for i in range(3)],
                        [-32768,-32767,32767])
                count+=1
        self.receipt('callers',original_window_captures=count,current_call_windows_zero=True,
            all_four_callers_still_unrestored=True,no_current_caller_or_gameplay_claim=True)

    def test_10_independent_original_rebases_and_guarded_runtime_connections(self):
        original=(self.out/'before-packet_original').read_text()
        path=self.out/'original-pair.s'
        body='.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\n'
        for name in ('func_1509563C',source.FUNCTION):
            inner=original.split('glabel '+name+'\n',1)[1].split('endlabel '+name,1)[0]
            body+='.type '+name+', @function\nglabel '+name+'\n'+inner+'\n.size '+name+', . - '+name+'\n'
        path.write_text(body)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        objects=[parse_object(path.with_suffix('.o')),parse_object(self.padded)]
        count=0
        for number,delta in enumerate((0,0x10000,0x20000)):
            links=dict(func_1509563C=0x15200000+delta,func_15095760=0x15210000+delta,
                func_15095A90=0x15220000+delta,func_150A7A00=0x15230000+delta,
                D_80082FA4=0x80217FF8+delta,D_800BE628=0x8022FFF8+delta,D_800BE9C0=0x80237FFF+delta,
                D_800D2CA8=0x80247FC0+delta,D_800D9B20=0x80258004+delta)
            streams=[]
            for variant,(data,funcs,rel) in enumerate(objects):
                code={}
                for name in ('func_1509563C',source.FUNCTION):
                    f=funcs[name]
                    relative={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
                    asm,missing=emit_function(data[f['value']:f['value']+f['size']],dict(value=0,size=f['size']),relative,name,links)
                    self.assertFalse(missing)
                    file=self.out/('rebase-%d-%d-%s.s'%(number,variant,name))
                    file.write_text(asm)
                    file.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%links[name])
                    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(file.with_suffix('.o')),str(file)],check=True,capture_output=True)
                    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(file.with_suffix('.ld')),'-e',name,
                        *['--defsym=%s=0x%X'%v for v in links.items()],'-o',str(file.with_suffix('.elf')),str(file.with_suffix('.o'))],check=True,capture_output=True)
                    size=292 if name=='func_1509563C' else 336
                    words=struct.unpack_from('>%dI'%(size//4),sections(file.with_suffix('.elf'))['.text'][1])
                    code.update(zip(range(links[name],links[name]+size,4),words))
                streams.append(code)
            self.assertEqual(streams[0],streams[1])
            address_map={source.FRAME_INDEX:links['D_80082FA4'],source.VIEW_BASE:links['D_800BE628'],
                source.VIEW_INDEX:links['D_800BE9C0'],guest.NEAR:links['D_800D9B20']}
            remap=lambda memory:{(links['D_800D2CA8']+a-guest.MATRIX if guest.MATRIX<=a<guest.MATRIX+128 else
                address_map.get(a,a) if a in address_map else next((new+a-old for old,new in address_map.items()
                if old<=a<old+(1 if old==source.VIEW_INDEX else 4)),a)):v for a,v in memory.items()}
            for w,frame,view,phase in itertools.product((1.,2.),(0,1),(0,3),(0,8)):
                memory,args,transformed=guest.fixture(transformed=(17.25,-91.5,.25,w),frame=frame,view=view)
                expected,result,calls=guest.draw_reference(memory,args,transformed,phase=phase)
                calls=[(c[0],links['D_800D2CA8']+frame*64,*c[2:]) if c[0]=='matrix' else c for c in calls]
                models=[]
                for code in streams:
                    draw=[code[a] for a in range(links[source.FUNCTION],links[source.FUNCTION]+336,4)]
                    m=guest.ProjectionOracle(draw,remap(memory),args,transformed,phase=phase,
                        entry=links[source.FUNCTION],connected=code,bindings={links['func_1509563C']:source.PROJECT,
                        links['func_15095A90']:source.DRAW,links['func_150A7A00']:guest.MATRIX_CALL}).run()
                    self.assertEqual((guest.public(m.memory),m.r[2],m.calls),(guest.public(remap(expected)),result,calls))
                    models.append(m)
                self.assertEqual(guest.edge.state(models[0]),guest.edge.state(models[1]))
                count+=1
        self.receipt('rebases',independent_original_sets=3,paired_cases=count,all_nine_symbols_changed=True,
            normalized_projection_and_direct_draw_literal_state=True)


if __name__=='__main__':
    unittest.main()
