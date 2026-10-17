"""Threshold boundaries, halfword masks, sparse guest addresses and first image."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_indexed_threshold_mask as source
from tools.tests import game_view_point_projection_oracle as point
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

STACK,BASE,MASK=point.STACK,0x30000,0x70000


def fixture(index=0,y=-1001.,x=841.,threshold=-1000.,mask=0xa55a,alias=0,symbols=None):
    s=symbols or source.SYMBOLS;record=(BASE+(index&0xffffffff)*0x9a0)&0xffffffff
    dest=(MASK,(record+0x300)&0xffffffff,(record+0x2fc)&0xffffffff,
        s['D_800A1970'],s['D_800DBFF0'],s['D_800D9A40'])[alias]
    memory={STACK+i:(i*17+0xa5)&255 for i in range(-128,128)}
    for base,size in ((s['D_800DBFF0']-4,12),(s['D_800D9A40']-4,12),
            (s['D_800A1970']-4,12),(record+0x2f8,20),(MASK-4,12)):
        memory.update({(base+i)&0xffffffff:0xa5 for i in range(size)})
    put(memory,s['D_800DBFF0'],BASE);put(memory,s['D_800D9A40'],dest)
    for address,value in ((s['D_800A1970'],threshold),(record+0x300,y),(record+0x2fc,x)):
        put(memory,address&0xffffffff,value if isinstance(value,int) else point.bits(value))
    if alias==0:put(memory,dest,mask,2)
    return memory


def reference(initial,index,symbols=None):
    s=symbols or source.SYMBOLS;memory=dict(initial)
    record=(read(memory,s['D_800DBFF0'])+(index&0xffffffff)*0x9a0)&0xffffffff
    if point.floating(read(memory,(record+0x300)&0xffffffff))<point.floating(read(memory,s['D_800A1970'])):
        dest=read(memory,s['D_800D9A40']);mask=read(memory,dest,2);bit=1<<(index&31)
        mask=(mask|bit) if point.floating(read(memory,(record+0x2fc)&0xffffffff))>840. else (mask&~bit)
        put(memory,dest,mask&65535,2)
    return memory


class Oracle(point.PointProjectionOracle):
    def execute(self,word):
        if word>>26==0 and word&63==39:
            rs,rt,rd=(word>>21)&31,(word>>16)&31,(word>>11)&31
            self.r[rd]=~(self.r[rs]|self.r[rt])&0xffffffff;self.r[0]=0
        else:super().execute(word)


def oracle(words,memory,index,phase=0,entry=source.ENTRY):
    return Oracle(words,memory,(index&0xffffffff,),[],phase,entry)


def state(m):return point.state(m),m.condition,m.lo


class ThresholdMaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.truth=list(struct.unpack_from('>42I',(cls.out/'before-retail_rom').read_bytes(),source.ROM))

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,index=0,y=-1001.,x=841.,threshold=-1000.,mask=0xa55a,alias=0,phase=0,images=None,entry=source.ENTRY,symbols=None):
        memory=fixture(index,y,x,threshold,mask,alias,symbols)
        machines=[oracle(w,memory,index,phase,entry).run() for w in (images or [self.truth,*self.images])]
        for m in machines:self.assertEqual(m.memory,reference(memory,index,symbols));self.assertFalse(m.calls)
        for m in machines[1:]:self.assertEqual(state(machines[0]),state(m))
        return machines

    def test_01_literal_words_bindings_and_owner_isolation(self):
        for a,b in itertools.product((0,1,0x80000000,0xffffffff),repeat=2):
            m=oracle(self.truth,fixture(),0);m.r[8],m.r[9]=a,b
            m.execute((8<<21)|(9<<16)|(10<<11)|39)
            self.assertEqual(m.r[10],0xffffffff^(a|b));self.assertEqual(m.r[0],0)
        self.assertEqual(self.images,[self.truth,self.truth]);source.checked_parts(*source.parts(self.obj))
        self.assertEqual(self.row['unchanged_raw_padded_neighbors'],11)
        raw,bindings=source.parts(self.obj)
        wrong=bytearray(raw);wrong[4]^=1
        with self.assertRaises(ValueError):source.checked_parts(bytes(wrong),bindings)
        wrong=dict(bindings);wrong[16]=[('R_MIPS_HI16','D_800D9A40')]
        with self.assertRaises(ValueError):source.checked_parts(raw,wrong)
        self.receipt('shape',words=42,frame=0,guards=0,raw_padded_retail_exact=True,unchanged_neighbors=11)

    def test_02_thresholds_mask_width_and_sparse_shift_domain(self):
        core=0
        for index,y,x,mask,phase in itertools.product((0,1,3,15,16,31),
                (-float('inf'),-1001.,-1000.,float('inf'),0x7fc12345),
                (839.5,840.,840.5,float('inf'),0x7fc54321),(0,0x7fff,0x8000,0xffff),(0,8)):
            self.compare(index,y,x,mask=mask,phase=phase);core+=1
        sparse=0
        for index,threshold,y,x,phase in itertools.product((-2,-1,32,0x10000,0x7fffffff,0x80000000),
                (-0.,0x7f800000,0x7fc11111),(-0.,-1.,0x7f812345),(840.,841.),(0,8)):
            self.compare(index,y,x,threshold,phase=phase);sparse+=1
        aliases=0
        for index,alias,x,y,phase in itertools.product((0,3,15,31),range(1,6),(839.,841.),(-1001.,-999.),(0,8)):
            self.compare(index,y,x,alias=alias,phase=phase);aliases+=1
        # A blocked first gate must not touch the second float or mask pointer.
        memory=fixture(y=-999.)
        for at in (BASE+0x2fc,source.SYMBOLS['D_800D9A40']):
            for i in range(4):memory.pop(at+i)
        for w in (self.truth,*self.images):self.assertEqual(oracle(w,memory,0).run().memory,memory)
        self.receipt('semantics',core=core,sparse_wrap_shift=sparse,aliases=aliases,lazy_gate=True,
            no_writes_outside_halfword=True,guest_word_wrap_not_portable_C=True,hardware_FP_exceptions_not_modeled=True)

    def test_03_every_selected_access_fault_prefix(self):
        count=0
        for index,y,x,alias,phase in itertools.product((0,3,31),(-1001.,-999.),(840.,841.),(0,1,4,5),(0,8)):
            memory=fixture(index,y,x,alias=alias);done=oracle(self.truth,memory,index,phase).run()
            for cut in range(done.all_accesses):
                machines=[oracle(w,memory,index,phase) for w in (self.truth,*self.images)]
                for m in machines:
                    m.access_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(state(machines[0]),state(machines[1]));self.assertEqual(state(machines[0]),state(machines[2]));count+=1
        self.receipt('faults',complete_modeled_access_prefixes=count,three_way_private_equal=True)

    def test_04_independent_symbol_rebases(self):
        count=0
        for group,entry in enumerate((0x15207ff0,0x15610000,0x15228000)):
            addresses=((0x80317ffc,0x80328000,0x80337ff0),
                (0x80418004,0x80427ffc,0x80438000),(0x80517ff0,0x80528004,0x80537ffc))[group]
            symbols=dict(zip(source.SYMBOLS,addresses))
            raw=source.raw_object(self.root,self.out,self.obj,'rebase-'+str(group),symbols)
            asm=raw.with_suffix('.ld');elf=raw.with_suffix('.elf')
            asm.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(asm),'-e',source.FUNCTION,
                *['--defsym=%s=0x%X'%p for p in symbols.items()],'-o',str(elf),str(raw)],capture_output=True,check=True)
            words=list(struct.unpack_from('>42I',source.projection.sections(elf)['.text'][1]))
            for index,y,x in itertools.product((0,3,31),(-1001.,-999.),(840.,841.)):
                self.compare(index,y,x,images=[words],entry=entry,symbols=symbols);count+=1
        self.receipt('rebases',independent_links=3,cases=count,all_three_symbols_independently_bound=True)

    def test_05_native32_typed_objects_and_effective_controls(self):
        head='#include <ultra64.h>\nextern u8 *D_800DBFF0;\n'+source.TYPE
        driver=self.out/'native-driver.c';driver.write_text(head+NATIVE)
        controls={'threshold':source.SELECTED.replace('> 840.0f','> 841.0f'),
            'bit':source.SELECTED.replace('1 << index','1 << (index + 1)'),
            'gate':source.SELECTED.replace('< D_800A1970','<= D_800A1970')}
        for opt in ('-O2','-O0'):
            for label,body in (('selected',source.SELECTED),*controls.items()):
                path=self.out/('native-'+label+'.c');path.write_text(head+body+'\n');exe=self.out/('native-'+label+opt)
                subprocess.run(native_command(opt)+['-mstackrealign','-fno-builtin',str(path.relative_to(self.root)),str(driver.relative_to(self.root)),'-o',str(exe)],cwd=self.root,capture_output=True,check=True)
                result=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual(result.returncode,0 if label=='selected' else 22,(opt,label,result.stderr))
        self.receipt('native',cases_per_profile=2000,profiles=['O2','O0'],UBSan=True,
            typed_record_mask_canaries=True,effective_controls=6,sparse_and_signed_overflow_domains_excluded=True)

    def historical(self,path):
        from tools.tests import actor_scale_timer_checkpoint as latest
        return latest.previous_input((self.root/path).read_bytes(),path,self.root)

    def test_06_caller_and_frozen_boundaries(self):
        caller=(self.root/'conker/asm/13BB20.s').read_text()
        self.assertIn('13D1B4 1510FD04 0D43CCFE',caller);self.assertIn('13D1B8 1510FD08 02002025',caller)
        source.freeze(self.root,self.out)
        self.assertEqual(self.historical('conker/retail_word_patches.us.csv'),(self.out/'before-guards').read_bytes())
        self.receipt('inputs',protected_entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),
            actual_caller_A0_S0_window_checked=True,no_complete_caller_or_hardware_claim=True)

    def test_07_complete_first_image_and_historical_adapters(self):
        from tools.experiments import game_indexed_threshold_mask_installation as install
        from tools.tests import indexed_threshold_mask_checkpoint as checkpoint
        out=self.root/install.BUILD;expected=install.expected_inputs(self.root,out)
        self.assertEqual(json.loads((out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual((out/'prelink-prediction.elf').read_bytes(),expected['elf'])
        if not (out/'after-elf').exists():self.receipt('installation',installed=False,first_image_qualified=True);return
        original=Path.read_bytes;count=0
        for key,data in expected.items():
            self.assertEqual(self.historical(source.PATHS[key]),data)
            self.assertEqual(checkpoint.previous_input(data,source.PATHS[key],self.root),(out/('before-'+key)).read_bytes())
            for stage in ('before','after'):
                path=out/(stage+'-'+key);wrong=bytearray(path.read_bytes());wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(p):return wrong if p==path else original(p)
                with patch.object(Path,'read_bytes',altered):
                    with self.assertRaisesRegex(AssertionError,'Changed threshold-mask checkpoint fixture'):
                        checkpoint.previous_input(data,source.PATHS[key],self.root)
                count+=1
        old,_,oa=load_elf_functions(str(out/'before-elf'),'mips-linux-gnu-objdump')
        new,_,na=load_elf_functions(str(out/'after-elf'),'mips-linux-gnu-objdump')
        self.assertEqual(oa,na);self.assertEqual(set(old),set(new));self.assertEqual([n for n in old if old[n]!=new[n]],[source.FUNCTION])
        old_symbols=[(n,(f[1],source.SIZE if n==source.FUNCTION else f[2],*f[3:])) for _,n,f,_ in symbol_rows((out/'before-elf').read_bytes())]
        self.assertEqual(sorted(old_symbols),sorted((n,f[1:]) for _,n,f,_ in symbol_rows(expected['elf'])))
        owned={source.PATHS[k] for k in expected}
        for key,path in source.PATHS.items():
            if path not in owned:self.assertEqual(self.historical(path),(out/('before-'+key)).read_bytes())
        data=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        self.receipt('installation',installed=True,whole_first_image_exact=True,metadata_exclusions=0,
            compared_bodies=len(old),only_target_changed=True,all_addresses_preserved=True,game_data=data,
            checkpoint_controls=count,all_other_protected_inputs_unchanged=True)


NATIVE=r'''
void func_150F33F8(s32);
typedef struct {u8 pad[0x2FC];f32 x,y;u8 tail[0x69C];} Record;
static Record records[4];static struct {u16 before;s16 mask;u16 after;} flags;
u8 *D_800DBFF0=(u8 *)records;s16 *D_800D9A40=&flags.mask;f32 D_800A1970;
static f32 values[5]={-1001.f,-1000.f,840.f,840.5f,841.f};
static int run(void){int i,x,y,t,k;u16 expected,initial[4]={0,0x7fff,0x8000,0xffff};
if(sizeof(void*)!=4||sizeof(Record)!=0x9A0||__builtin_offsetof(Record,y)!=0x300)return 20;
for(i=0;i<4;i++)for(x=0;x<5;x++)for(y=0;y<5;y++)for(t=0;t<5;t++)for(k=0;k<4;k++){
records[i].x=values[x];records[i].y=values[y];D_800A1970=values[t];
flags.before=0xa55a;flags.after=0x5aa5;flags.mask=(s16)initial[k];expected=initial[k];
if(values[y]<values[t]){if(values[x]>840.f)expected|=(u16)(1u<<i);else expected&=(u16)~(1u<<i);}
func_150F33F8(i);if((u16)flags.mask!=expected||flags.before!=0xa55a||flags.after!=0x5aa5)return 22;
}return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''

if __name__=='__main__':unittest.main()
