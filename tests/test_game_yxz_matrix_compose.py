"""Direct matrix construction: argument bits, private matrix, real kernels and ABI."""
import itertools
import json
import math
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_yxz_matrix_compose as source
from tools.tests import game_packet_rectangle_oracle as base
from tools.tests.test_game_projected_packet_draw import native_command

OUTPUT,RECORDS,TABLE=0x30000,0x40000,0x800BE628
COS,SIN=0x150AD780,0x150AD78C
ANGLES=tuple(itertools.product((0,0x80000000,0x3F800000,0x42B40000),repeat=3))+(
    (1,0x80000001,0x3F000000),(0x7F7FFFFF,0xFF7FFFFF,0),
    (0x7F800000,0xFF800000,0x7FC12345),(0x7FC12345,0x7FC54321,0x80000000))


def fixture(angles=ANGLES[0],high=0):
    output=OUTPUT+(0x80000000 if high else 0)
    memory={base.STACK+i:(i*13+0xA5)&255 for i in range(-0x240,0x140)}
    memory.update({output+i:(i*7+0xA5)&255 for i in range(-16,80)})
    return memory,(output,*angles)


def opaque_effect(memory,target,args):
    if target==source.ROTATE:
        output,x,y,z=args
        for i in range(16):
            base.put(memory,output+i*4,((x+0x12345*(i+1))^(y*33)^(z*65599))&0xFFFFFFFF)
    else:
        left,right,output=args
        a=[base.read(memory,left+i*4) for i in range(16)]
        b=[base.read(memory,right+i*4) for i in range(16)]
        for i in range(16):
            v=b[(i+1)%16]
            base.put(memory,output+i*4,a[i]^(((v<<7)|(v>>25))&0xFFFFFFFF)^0x9E3779B9)


def reference(initial,args,temporary):
    output,x,y,z=args
    memory=dict(initial)
    calls=[(source.ROTATE,(output,0,y,0)),(source.ROTATE,(temporary,x,0,0)),
        (source.PRODUCT,(output,temporary,output)),(source.ROTATE,(temporary,0,0,z)),
        (source.PRODUCT,(output,temporary,output))]
    for target,arguments in calls:opaque_effect(memory,target,arguments)
    return memory,calls


class MatrixOracle(base.RectangleOracle):
    def __init__(self,words,memory,args,poison_homes=False,real=False,**kwargs):
        self.poison_homes,self.real,self.entered=poison_homes,real,False
        self.trig=[]
        super().__init__(words,memory,args,entry=kwargs.pop('entry',source.ENTRY),**kwargs)

    def record_call(self,target):
        if target==source.ENTRY:
            self.entered=True
        elif target in (COS,SIN):
            self.trig.append((target,self.f[12]))
        elif target in (source.ROTATE,source.PRODUCT):
            self.calls.append((target,tuple(self.arguments(4 if target==source.ROTATE else 3))))
        else:raise AssertionError(('unconnected matrix call',hex(target)))

    def hook(self,target):
        value=None
        if target in (COS,SIN):
            angle=base.floating(self.f[12])
            value=base.bits(math.cos(angle) if target==COS else math.sin(angle))
        else:
            if self.real:raise AssertionError('Real matrix helper was not connected')
            opaque_effect(self.memory,target,self.calls[-1][1])
        if self.poison_homes:
            for i in range(4):base.put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        for register in range(20):self.f[register]=0x3F800000+register
        if value is not None:self.f[0]=value
        self.hi,self.lo=0x12345678,0x89ABCDEF


def product(a,b):
    result=[]
    for row in range(4):
        for col in range(4):
            value=base.rounded(a[row*4]*b[col])
            for k in range(1,4):value=base.rounded(value+base.rounded(a[row*4+k]*b[k*4+col]))
            result.append(value)
    return result


def rotation(x,y,z,scale):
    cx,cy,cz=[base.rounded(math.cos(base.rounded(v*scale))) for v in (x,y,z)]
    sx,sy,sz=[base.rounded(math.sin(base.rounded(v*scale))) for v in (x,y,z)]
    m=base.rounded
    return [m(cy*cz),m(cy*sz),-sy,0.,m(m(m(sx*sy)*cz)-m(cx*sz)),
        m(m(m(sx*sy)*sz)+m(cx*cz)),m(sx*cy),0.,m(m(m(cx*sy)*cz)+m(sx*sz)),
        m(m(m(cx*sy)*sz)-m(sx*cz)),m(cx*cy),0.,0.,0.,0.,1.]


def controls():
    body=source.SELECTED
    return {
        'wrong-initial-axis':body.replace('matrix, 0.0f, y, 0.0f','matrix, y, 0.0f, 0.0f'),
        'reversed-product':body.replace('func_150A7A48(matrix, temporary, matrix);',
            'func_150A7A48(temporary, matrix, matrix);',1),
        'drop-final-product':body.rsplit('    func_150A7A48(matrix, temporary, matrix);',1)[0]+'}\n',
        'wrong-final-destination':body.rsplit('    func_150A7A48(matrix, temporary, matrix);',1)[0]+
            '    func_150A7A48(matrix, temporary, temporary);\n}\n',
    }


TYPES='''#include <ultra64.h>
void func_150A8050(f32 [4][4], f32, f32, f32);
void func_150A7A48(f32 [4][4], f32 [4][4], f32 [4][4]);
'''


def native_harness():
    rows=',\n'.join('{'+','.join('0x%Xu'%v for v in a)+'}' for a in ANGLES)
    return TYPES+'static const u32 angles[][3]={'+rows+'};\n'+r'''
static f32 output[4][4];static u32 count,error,log[5][5];static f32(*temporary)[4];
static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 floating(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
static u32 role(f32 m[4][4]){return m==output?0:m==temporary?1:2;}
void func_150A8050(f32 m[4][4],f32 x,f32 y,f32 z){u32 i,a=word(x),b=word(y),c=word(z);
 if(count>=5){error=21;return;}if(count==1)temporary=m;
 log[count][0]=0;log[count][1]=role(m);log[count][2]=a;log[count][3]=b;log[count++][4]=c;
 for(i=0;i<16;i++)((f32*)m)[i]=floating((a+0x12345u*(i+1))^(b*33u)^(c*65599u));}
void func_150A7A48(f32 a[4][4],f32 b[4][4],f32 c[4][4]){u32 i,left[16],right[16],v;
 if(count>=5){error=21;return;}log[count][0]=1;log[count][1]=role(a);
 log[count][2]=role(b);log[count][3]=role(c);log[count++][4]=0;
 for(i=0;i<16;i++){left[i]=word(((f32*)a)[i]);right[i]=word(((f32*)b)[i]);}
 for(i=0;i<16;i++){v=right[(i+1)%16];((f32*)c)[i]=floating(left[i]^((v<<7)|(v>>25))^0x9E3779B9u);}}
void func_151102CC(f32 [4][4],f32,f32,f32);
static int run(void){u32 k,i,j,expected[5][5],saved[16],actual[16];f32 temp[4][4];
 if(sizeof(void*)!=4||sizeof(temp)!=64)return 29;
 for(k=0;k<sizeof(angles)/sizeof(angles[0]);k++){
 count=error=0;temporary=temp;
 func_150A8050(output,0.,floating(angles[k][1]),0.);
 func_150A8050(temp,floating(angles[k][0]),0.,0.);func_150A7A48(output,temp,output);
 func_150A8050(temp,0.,0.,floating(angles[k][2]));func_150A7A48(output,temp,output);
 for(i=0;i<5;i++)for(j=0;j<5;j++)expected[i][j]=log[i][j];
 for(i=0;i<16;i++){saved[i]=word(((f32*)output)[i]);((f32*)output)[i]=floating(0xA5A5A5A5u);}
 count=error=0;temporary=0;
 func_151102CC(output,floating(angles[k][0]),floating(angles[k][1]),floating(angles[k][2]));
 if(count!=5||error)return 23;
 for(i=0;i<5;i++)for(j=0;j<5;j++)if(log[i][j]!=expected[i][j])return 24;
 for(i=0;i<16;i++){actual[i]=word(((f32*)output)[i]);if(actual[i]!=saved[i])return 25;}
 }return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class YxzMatrixComposeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.stage=source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):
            cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin')
        cls.truth=struct.unpack_from('>37I',cls.rom,source.ROM)

    def test_01_complete_bits_private_matrix_and_call_ABI(self):
        count=0
        for angles,high,phase,poison in itertools.product(ANGLES,(0,1),(0,8),(False,True)):
            memory,args=fixture(angles,high)
            expected,calls=reference(memory,args,base.STACK+phase-0x40)
            model=MatrixOracle(self.words,memory,args,phase=phase,poison_homes=poison).run()
            self.assertEqual(model.calls,calls)
            self.assertEqual(base.base.public(model.memory),base.base.public(expected));count+=1
        self.assertEqual(count,544)

    def test_02_native32_O2_O0_UBSan_and_effective_controls(self):
        harness=self.out/'native-harness.c';harness.write_text(native_harness())
        for label,opt,body,valid in [('O2','-O2',source.SELECTED,True),('O0','-O0',source.SELECTED,True)]+[
                (name,'-O2',body,False) for name,body in controls().items()]:
            p=self.out/('native-'+label+'.c');p.write_text(TYPES+body);exe=p.with_suffix('')
            result=subprocess.run([*native_command(opt,valid),'-mstackrealign',str(p),str(harness),'-o',str(exe)],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn(subprocess.run([str(exe)],timeout=30).returncode,(0,) if valid else (21,23,24,25),label)

    def test_03_effective_compiled_guest_controls(self):
        with source.historical_view(self.root,self.out):
            for name,body in controls().items():
                _,words,row=source.measure(self.root,self.out,'negative-'+name,body)
                self.assertFalse(row['diagnostics'])
                for angles in ANGLES:
                    memory,args=fixture(angles);expected,calls=reference(memory,args,base.STACK-0x40)
                    model=MatrixOracle(words,memory,args).run()
                    if model.calls!=calls or base.base.public(model.memory)!=base.base.public(expected):break
                else:self.fail('Ineffective matrix control: '+name)

    def test_04_real_rotation_and_cached_right_product_kernels(self):
        connected={}
        image=source.raw_read(self.root/'conker/build/conker.us.elf')
        for entry,words in ((source.ROTATE,83),(source.PRODUCT,78)):
            at=source.elf_slot_offset(image,entry,words*4)
            rom_at=entry-0x15000000+0x2D4B0
            self.assertEqual(image[at:at+words*4],self.rom[rom_at:rom_at+words*4])
            for i,w in enumerate(struct.unpack_from('>%dI'%words,self.rom,entry-0x15000000+0x2D4B0)):
                connected[entry+i*4]=w
        scale_at=source.elf_slot_offset(image,0x8009F6C0,4)
        scale=struct.unpack_from('>f',image,scale_at)[0]
        count=0
        for angles,phase in itertools.product(((0.,0.,0.),(30.,45.,60.),(-90.,15.,270.),
                (360.,-180.,0.125),(1.25,-2.5,3.75)),(0,8)):
            memory,args=fixture(tuple(base.bits(a) for a in angles))
            base.put(memory,0x8009F6C0,base.bits(scale))
            model=MatrixOracle(self.words,memory,args,phase=phase,real=True,connected=connected).run()
            expected=product(product(rotation(0.,angles[1],0.,scale),rotation(angles[0],0.,0.,scale)),
                rotation(0.,0.,angles[2],scale))
            self.assertEqual([base.read(model.memory,args[0]+i*4) for i in range(16)],list(map(base.bits,expected)))
            self.assertEqual(len(model.trig),18);count+=1
        self.assertEqual(count,10)

    def test_05_real_wrapper_with_record_alias_and_snapshot_ABI(self):
        caller=struct.unpack_from('>26I',self.rom,0x13D810)
        connected=dict(zip(range(source.ENTRY,source.ENTRY+148,4),self.words))
        for slot,alias,phase in itertools.product((0,1,7),(0,1),(0,8)):
            angles=tuple(base.bits(a) for a in (1.25,-2.5,7.0));memory,args=fixture(angles)
            memory.update({RECORDS+i:(i*19+0xA5)&255 for i in range(8*0x180)})
            base.put(memory,TABLE,RECORDS)
            output=RECORDS+slot*0x180+0xBC if alias else OUTPUT
            arguments=(slot,output,*angles)
            expected,calls=reference(memory,(output,*angles),base.STACK+phase-0x18-0x40)
            final=(source.PRODUCT,(output,RECORDS+slot*0x180+0xBC,output))
            opaque_effect(expected,*final);calls.append(final)
            model=MatrixOracle(caller,memory,arguments,entry=source.WRAPPER,phase=phase,
                poison_homes=True,connected=connected).run()
            self.assertTrue(model.entered);self.assertEqual(model.calls,calls)
            self.assertEqual(base.base.public(model.memory),base.base.public(expected))

    def test_06_all_target_memory_fault_prefixes(self):
        count=0
        for angles,phase in itertools.product(ANGLES[::8],(0,8)):
            memory,args=fixture(angles)
            complete=MatrixOracle(self.words,memory,args,phase=phase,poison_homes=True).run()
            for fault in range(complete.accesses):
                pairs=[]
                for words in (self.words,self.truth):
                    model=MatrixOracle(words,memory,args,phase=phase,poison_homes=True,fault=fault)
                    with self.assertRaises(base.base.edge.AccessFault):model.run()
                    pairs.append((model.memory,model.events,model.calls,model.accesses))
                self.assertEqual(*pairs);count+=1
        (self.out/'fault-prefixes.json').write_text(json.dumps(dict(states=18,equal_prefixes=count,
            provider_faults_not_modeled=True),indent=2)+'\n')

    def test_07_pinned_words_bindings_inputs_and_installed_image(self):
        text,functions,rel=source.parse_object(self.obj);f=functions[source.FUNCTION]
        raw,bindings=source.checked_object(self.obj)
        self.assertEqual(len(raw),148);self.assertEqual(len(bindings),5)
        for i in range(37):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for i in bindings:
            bad=dict(rel);bad[f['value']+i]=[('R_MIPS_26','func_151102CC')]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        with source.historical_view(self.root,self.out):
            read=Path.read_bytes
            for index,p in enumerate(source.INPUTS):
                for path in (self.root/p,self.out/('before-%02d'%index)):
                    with patch.object(Path,'read_bytes',lambda x:read(x)+b'\n' if x==path else read(x)):
                        with self.assertRaises(ValueError):source.freeze(self.root,self.out)
            with self.assertRaisesRegex(RuntimeError,'cannot nest'):
                with source.historical_view(self.root,self.out):pass
        self.assertEqual(source.verify(self.root,self.out),self.stage)
        if self.stage=='after':self.assertEqual(source.audit(self.root,self.out)['functions'],6057)


if __name__=='__main__':unittest.main()
