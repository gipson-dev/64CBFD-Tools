"""Qualify one transform; the unmatched slot-provider drafts are not installed."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_packed_point_transform as source
from tools.tests.test_game_actor_mask_scan_match import MaskOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_table_range_loader import STACK
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_classifier_candidates import sections

POINTS,SOURCE,OUTPUT,MATRIX=0x20000,0x22000,0x24000,0x28000
PROVIDER,TRANSFORM,CONTEXT=0x1509499C,0x150A7960,0x800D2C20


def fixture(value,pattern=0,alias=0):
    memory={STACK+i:(i*17+13)&255 for i in range(-0x300,0x140)}
    for base,size in ((POINTS,320),(SOURCE,256),(OUTPUT,288),(MATRIX,64),(CONTEXT,4)):
        memory.update({base+i:0xA5 for i in range(size)})
    coords=(-32768,-3,0,1,32767)
    for index,axis in itertools.product(range(16),range(3)):
        put(memory,POINTS+index*16+axis*2,coords[(index+axis+pattern)%5]&65535,2)
    values=[0.0]*16
    values[0],values[5],values[10],values[15]=1.0,-0.5,2.0,1.0
    values[12:15]=[0.25,-4.5,7.75]
    for index,value_f in enumerate(values):
        put(memory,MATRIX+index*4,bits(value_f))
    put(memory,CONTEXT,MATRIX)
    put(memory,SOURCE+1,value,1)
    put(memory,SOURCE+4,POINTS)
    output=(OUTPUT,POINTS,POINTS+4,SOURCE)[alias]
    return memory,(SOURCE,output)


def public(memory):
    return {a:b for a,b in memory.items() if not STACK-0x300<=a<STACK+0x140}


def reference(memory,args):
    result=dict(memory)
    value=read(result,args[0]+1,1)
    first,end=value&15,(value>>4)+1
    base=read(result,args[0]+4)
    calls=[]
    fp=lambda value:floating(bits(value))
    for slot in range(first,end):
        point=base+(slot-first)*16
        xyz=[]
        for axis in range(3):
            v=read(result,point+axis*2,2)
            xyz.append(float(v-65536 if v&32768 else v))
        matrix=read(result,CONTEXT)
        destination=args[1]+slot*12
        calls.append((TRANSFORM,matrix,*map(bits,xyz),destination,destination+4,destination+8))
        for axis in range(3):
            m=[floating(read(result,matrix+(axis+row*4)*4)) for row in range(4)]
            value_f=fp(fp(fp(m[0]*xyz[0])+fp(m[1]*xyz[1]))+fp(fp(m[2]*xyz[2])+m[3]))
            put(result,destination+axis*4,bits(value_f))
    return public(result),calls


class PackedOracle(MaskOracle):
    def record_call(self,target):
        args=self.arguments({PROVIDER:2,TRANSFORM:7}[target])
        self.calls.append((target,*args))
        self.events.append(('CALL',target,args))

    def hook(self,target):
        raise AssertionError(('Opaque packed-point helper is not accepted',hex(target)))


def native_harness():
    declarations=source.DECLARATIONS.replace('void func_1509499C(PackedPointSource948C0 *, s16 **);',
        's32 func_1509499C();')
    return '#include <ultra64.h>\n'+declarations+r'''
void func_150948C0(PackedPointSource948C0 *, f32 [][3]);
static s16 points[16][8];static f32 output[24][3],expected[16][3],matrix[4][4];
f32 (*D_800D2C20)[4];static u32 calls;
static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
s32 func_1509499C(PackedPointSource948C0 *source,s16 **slots){
 u32 i,first=source->slotRange&15,end=(source->slotRange>>4)+1;
 for(i=0;i<16;i++)slots[i]=i>=first&&i<end?source->points[i-first]:0;return 0;}
void func_150A7960(f32 m[4][4],f32 x,f32 y,f32 z,f32 *ox,f32 *oy,f32 *oz){
 f32 *out[3];u32 a;out[0]=ox;out[1]=oy;out[2]=oz;calls++;
 for(a=0;a<3;a++){f32 p=m[0][a]*x,q=m[1][a]*y,r=m[2][a]*z;
 *out[a]=(p+q)+(r+m[3][a]);}}
static int run(void){static const s16 edge[]={-32768,-3,0,1,32767};
 PackedPointSource948C0 source;u32 mask,p,mode,i,a,j,first,end;f32 x,y,z;
 if(sizeof(void*)!=4||sizeof(source)!=8||__builtin_offsetof(PackedPointSource948C0,points)!=4)return 29;
 source.points=points;D_800D2C20=matrix;
 for(mask=0;mask<256;mask++)for(p=0;p<5;p++)for(mode=0;mode<2;mode++){
  source.slotRange=(u8)mask;first=mask&15;end=(mask>>4)+1;
  for(i=0;i<16;i++)for(a=0;a<8;a++)points[i][a]=a<3?edge[(i+a+p)%5]:1234;
  for(i=0;i<24;i++)for(a=0;a<3;a++)output[i][a]=123.25f;
  for(i=0;i<16;i++)for(a=0;a<3;a++)expected[i][a]=123.25f;
  for(i=0;i<4;i++)for(j=0;j<4;j++)matrix[i][j]=i==j?(mode?-0.5f:1.0f):0;
  matrix[3][0]=0.25f;matrix[3][1]=-4.5f;matrix[3][2]=7.75f;
  for(i=first;i<end;i++){x=points[i-first][0];y=points[i-first][1];z=points[i-first][2];
   for(a=0;a<3;a++){f32 q0=matrix[0][a]*x,q1=matrix[1][a]*y,q2=matrix[2][a]*z;
    expected[i][a]=(q0+q1)+(q2+matrix[3][a]);}}
  calls=0;func_150948C0(&source,output);
  if(calls!=(end>first?end-first:0))return 22;
  for(i=0;i<16;i++)for(a=0;a<3;a++)if(word(output[i][a])!=word(expected[i][a]))return 21;
  for(i=16;i<24;i++)for(a=0;a<3;a++)if(output[i][a]!=123.25f)return 23;
 }
 return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class PackedPointTransformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.words,_,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>55I',cls.rom,source.ROM))
        _,functions,_=parse_object(cls.obj)
        cls.raw=list(struct.unpack_from('>55I',sections(cls.out/'qualified.elf')['.text'][1],functions[source.FUNCTION]['value']))
        cls.connected={PROVIDER+i*4:w for i,w in enumerate(struct.unpack_from('>71I',cls.rom,0xC1E4C))}
        cls.connected.update({TRANSFORM+i*4:w for i,w in enumerate(struct.unpack_from('>40I',cls.rom,0xD4E10))})

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def models(self,memory,args,phase):
        result=[PackedOracle(words,memory,phase=phase,entry=source.ENTRY,arguments=args,
            connected=self.connected).run() for words in (self.truth,self.raw,self.words)]
        state=lambda m:(m.r,m.f,m.memory,m.calls,m.events,m.lo,m.condition,m.accesses)
        self.assertEqual(state(result[0]),state(result[1]))
        self.assertEqual(state(result[0]),state(result[2]))
        return result[0]

    def test_01_all_range_bytes_original_provider_matrix_and_live_aliases(self):
        count=0
        for value,phase,alias in itertools.product(range(256),(0,8),range(4)):
            memory,args=fixture(value,value%5,alias)
            expected,calls=reference(memory,args)
            model=self.models(memory,args,phase)
            self.assertEqual(public(model.memory),expected,(value,phase,alias))
            self.assertEqual(model.calls[0],(PROVIDER,args[0],STACK+phase-144+80))
            self.assertEqual(model.calls[1:],calls)
            count+=1
        self.receipt('guest',cases=count,original_provider_words=71,original_matrix_words=40,
            complete_modeled_state_three_way=True,installed_provider_completion_not_claimed=True)

    def test_02_native32_O2_O0_UBSan_and_effective_controls(self):
        harness=self.out/'native-harness.c'
        harness.write_text(native_harness())
        controls={
            'wrong-count':source.SELECTED.replace('index != 16','index != 15'),
            'unsigned-coordinate':source.SELECTED.replace('point[0], point[1], point[2]',
                '((u16 *)point)[0], ((u16 *)point)[1], ((u16 *)point)[2]'),
            'wrong-stride':source.SELECTED.replace('index * 12','index * 16'),
            'wrong-coordinate':source.SELECTED.replace('point[0], point[1], point[2]','point[1], point[1], point[2]'),
        }
        exits={}
        for label,opt,body,valid in [('O2','-O2',source.SELECTED,True),('O0','-O0',source.SELECTED,True)]+[
                (label,'-O2',body,False) for label,body in controls.items()]:
            self.assertNotEqual(body,source.SELECTED) if not valid else None
            selected=self.out/'native-body.c'
            declarations=source.DECLARATIONS.replace('void func_1509499C(PackedPointSource948C0 *, s16 **);',
                's32 func_1509499C();')
            selected.write_text('#include <ultra64.h>\n'+declarations+body)
            exe=self.out/('native-'+label)
            result=subprocess.run([*native_command(opt,valid),str(selected),str(harness),'-o',str(exe)],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run([str(exe)],capture_output=True,timeout=30)
            self.assertIn(result.returncode,(0,) if valid else (21,22,23),label)
            exits[label]=result.returncode
        self.receipt('native',cases_per_selected=2560,separate_units_native32_O2_O0_UBSan=True,exits=exits)

    def test_03_eighteen_neighbors_provider_and_rectangle_are_unchanged(self):
        obj,diagnostics=source.build.compile_owner(self.root,self.out,(self.out/'before-packet_owner').read_text(),'neighbor-before')
        self.assertFalse(diagnostics)
        before,after=parse_object(obj),parse_object(self.obj)
        self.assertEqual(set(before[1]),set(after[1]))
        for name,f in before[1].items():
            if name==source.FUNCTION:
                continue
            g=after[1][name]
            self.assertEqual(before[0][f['value']:f['value']+f['size']],after[0][g['value']:g['value']+g['size']],name)
            bindings=lambda obj,f:{a-f['value']:v for a,v in obj[2].items() if f['value']<=a<f['value']+f['size']}
            self.assertEqual(bindings(before,f),bindings(after,g),name)
        self.assertEqual(len(before[1])-1,18)
        self.assertEqual(self.words,self.truth)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['guards']),(55,144,2,2))

    def test_04_word_binding_pool_and_frozen_input_corruptions(self):
        source.checked_object(self.obj)
        text,functions,rel=parse_object(self.obj)
        f=functions[source.FUNCTION]
        for index in range(55):
            bad=bytearray(text)
            bad[f['value']+index*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        for at in source.RELOCATIONS:
            bad=dict(rel)
            bad[f['value']+at]=[(rel[f['value']+at][0][0],'wrong')]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
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

    def test_05_complete_first_prediction_not_metadata_exclusions(self):
        row=source.prelink_prediction(self.root,self.out)
        self.assertEqual((row['changed_ELF_bytes'],row['metadata_serialization_bytes'],row['metadata_exclusions']),(208,40,0))
        self.assertEqual(row['after'],{k:hashlib.sha256(v).hexdigest() for k,v in source.expected_inputs(self.root,self.out).items()})
        slot=(self.out/'predicted-slot.bin').read_bytes()
        for at in (0,48,52,216):
            bad=bytearray(slot)
            bad[at]^=1
            with self.assertRaises(ValueError):
                source.slot_expected_image((self.out/'before-elf').read_bytes(),bytes(bad))

    def test_06_two_relocation_guards_and_exact_stub_preservation(self):
        import csv
        import io
        before=(self.out/'before-guards').read_bytes()
        after=source.proposed_guards(before)
        self.assertTrue(after.startswith(before))
        rows=list(csv.DictReader(io.StringIO(after.decode())))[-2:]
        self.assertEqual([(r['offset'],r['expected'],r['replacement'],r['expected_relocations'],r['replacement_relocations'])
            for r in rows],[('0x30','0x00008025','0x26520000','-','R_MIPS_LO16:D_800D2C20'),
                ('0x34','0x26520000','0x00008025','R_MIPS_LO16:D_800D2C20','-')])
        with self.assertRaises(ValueError):
            source.proposed_guards(after)
        old=(self.out/'before-packet_owner').read_text()
        new=source.recovered_owner(old)
        lo,hi=source.build.function_span(new,'func_1509499C')
        self.assertEqual(new[lo:hi],'s32 func_1509499C() {\n    return 0;\n}')
        with self.assertRaises(ValueError):
            source.recovered_owner(new)

    def test_07_rectangle_step_and_corner_hypotheses_remain_rejected(self):
        from tools.experiments import game_packet_rectangle_step_lifetime as step
        out=self.root/step.BUILD
        step.freeze(self.root,out)
        before=(out/'before-packet_owner').read_text()
        truth=struct.unpack_from('>346I',(out/'before-retail_rom').read_bytes(),step.ROM)
        forms=list(step.forms())
        self.assertEqual(len(forms),12)
        for label,body in forms:
            self.assertEqual((out/(label+'.c')).read_text(),step.recovered_owner(before,body))
            row=json.loads((out/(label+'.json')).read_text())
            text,functions,rel=parse_object(out/(label+'.o'))
            f=functions[step.FUNCTION]
            self.assertEqual(hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),row['raw_sha256'])
            bindings={str(a-f['value']):v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
            self.assertEqual(bindings,{a:[tuple(v) for v in values] for a,values in row['relocations'].items()})
            data=sections(out/(label+'.elf'))['.text'][1]
            words=struct.unpack_from('>%dI'%(f['size']//4),data,f['value'])
            differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-346)
            self.assertEqual((len(words),(-words[0])&65535,differences,row['diagnostics']),
                (row['words'],row['frame'],row['differences'],''))
            self.assertGreaterEqual(differences,18)
        self.assertEqual(step.SELECTED,step.INITIAL)


if __name__=='__main__':
    unittest.main()
