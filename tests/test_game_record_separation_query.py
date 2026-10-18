"""Packed word arithmetic, signed record scans and strict conversion-domain limits."""
import itertools
import csv
import io
import json
import math
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_record_separation_query as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_view_point_projection_oracle as base
from tools.tests.test_game_record_heading_setter import SetterOracle
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command

put,read,STACK=base.put,base.read,base.STACK
RECORDS,COMMAND=0x30000,0x80000
HEADER='#include <ultra64.h>\nextern u8 *D_800872A0;\nextern s8 D_800D2398;\n'
HEIGHTS=((0,1.25,0,-2.75),(-32768,-0.0625,32767,0.0625),
    (32767,134217720.,-32768,-134217728.),(0,-134217728.,0,0.),
    (0,0.,0,-134217728.),(1,0.062499996,-1,-0.062500007),
    (-1,-0.,1,0.),(32767,-134217728.,-32768,134217720.))
PAIRS=((-128,1),(-1,0),(0,0xFFFFFFFF),(127,1),(-128,0x100),
    (1,0x7FFFFFFF),(1,0xFFFFFFFF),(-1,128))


class OutsideConversionDomain(Exception):pass


def signed(v,width=32):return ((v&((1<<width)-1))^(1<<(width-1)))-(1<<(width-1))


def scaled(bits):
    sign,e,m=bits>>31,(bits>>23)&255,bits&0x7FFFFF
    if e==255:raise OutsideConversionDomain('Nonfinite quantized input')
    if e<123:return 0
    m|=0x800000
    value=m<<(e-146) if e>=146 else m>>(146-e)
    if value>(0x80000000 if sign else 0x7FFFFFFF):raise OutsideConversionDomain('Scaled float outside signed word')
    return (-value if sign else value)&0xFFFFFFFF


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x100<=a<STACK+0x100}


def fixture(count=3,index=0,tag=0,offset=0,pattern=4,height=0,active=True,phase=0,table=source.TABLE,count_address=source.COUNT):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x100,0x100)}
    for a,n in ((table,4),(count_address,1),(RECORDS,4*0x84)):
        memory.update({a+i:0xA5 for i in range(n)})
    put(memory,table,RECORDS if active else 0);put(memory,count_address,count,1)
    own_half,own_float,other_half,other_float=HEIGHTS[height]
    own=RECORDS+(index&0xFFFFFFFF)*0x84;own&=0xFFFFFFFF
    wanted=(tag+offset)&0xFFFFFFFF;n=max(0,signed(count,8))
    for i in range(128):
        row=RECORDS+i*0x84
        put(memory,row+0x29,wanted+1,1);put(memory,row+0x24,other_half,2);put(memory,row+8,base.bits(other_float))
    if n:
        hits={1:(0,),2:(n//2,),3:(n-1,),4:(0,n-1),5:()}.get(pattern,())
        for i in hits:put(memory,RECORDS+i*0x84+0x29,wanted,1)
    put(memory,own+0x29,tag,1);put(memory,own+0x24,own_half,2);put(memory,own+8,base.bits(own_float))
    return memory,(index&0xFFFFFFFF,offset&0xFFFFFFFF)


def reference(memory,args,table=source.TABLE,count_address=source.COUNT):
    reads=[(table,4,read(memory,table))];base_address=read(memory,table)
    if not base_address:return 0x10,reads
    count=read(memory,count_address,1);reads.append((count_address,1,count))
    own=(base_address+args[0]*0x84)&0xFFFFFFFF
    tag=read(memory,own+0x29,1);reads.append((own+0x29,1,tag));wanted=(signed(tag,8)+args[1])&0xFFFFFFFF
    for i in range(max(0,signed(count,8))):
        row=(base_address+i*0x84)&0xFFFFFFFF;tag=read(memory,row+0x29,1);reads.append((row+0x29,1,tag))
        if signed(tag,8)&0xFFFFFFFF!=wanted or i==args[0]:continue
        a,b=read(memory,own+8),read(memory,row+8)
        x,y=read(memory,own+0x24,2),read(memory,row+0x24,2)
        reads.extend(((own+8,4,a),(row+8,4,b),(own+0x24,2,x),(row+0x24,2,y)))
        left=(signed(x,16)*16+scaled(a))&0xFFFFFFFF
        right=(signed(y,16)*16+scaled(b))&0xFFFFFFFF
        delta=(left-right)&0xFFFFFFFF
        magnitude=(-delta)&0xFFFFFFFF if delta&0x80000000 else delta
        return ((magnitude<<8)|i)&0xFFFFFFFF,reads
    return 0x10,reads


class SeparationOracle(SetterOracle):
    def __init__(self,words,memory,args,phase=0,entry=source.ENTRY,connected=None):
        self.setter_reads=[];self.setter_writes=[];self.forwarded=[]
        base.PointProjectionOracle.__init__(self,words,memory,args,[],phase,entry,connected)

    def execute(self,word):
        op,rs,rt,rd,fn=word>>26,(word>>21)&31,(word>>16)&31,(word>>11)&31,word&63
        if op==17 and rs==16 and fn==2:
            if not math.isfinite(base.floating(self.f[rd])) or not math.isfinite(base.floating(self.f[rt])):
                raise OutsideConversionDomain('Nonfinite arithmetic is not modeled')
        if op==17 and rs==16 and fn==13:
            f=base.floating(self.f[rd])
            if not math.isfinite(f) or not -0x80000000<=math.trunc(f)<0x80000000:
                raise OutsideConversionDomain('Invalid TRUNC.W.S is not modeled')
        return super().execute(word)

    def record_call(self,target):
        if target!=source.ENTRY:raise AssertionError('Unexpected separation helper call')
        self.forwarded.append(self.arguments(2))

    def hook(self,target):raise AssertionError('Separation query must not call opaque helpers')


def controls():
    b=source.SELECTED
    return {
        'unsigned-count':b.replace('i < D_800D2398','i < (u8)D_800D2398'),
        'unsigned-id':b.replace('(u32)(s32)*(s8 *)(candidate + 0x29)','(u32)*(u8 *)(candidate + 0x29)'),
        'narrow-wanted':b.replace(' + idOffset;',' + idOffset;\n    idOffset = (u8)idOffset;'),
        'include-self':b.replace(' && (u32)i != recordIndex',''),
        'wrong-stride':b.replace('i * 0x84','i * 0x80'),
        'wrong-quantization':b.replace('* 16.0f','* 15.0f'),
        'wrong-integer-scale':b.replace('* 16u','* 15u'),
        'no-magnitude':b.replace('recordIndex = 0u - recordIndex;','recordIndex = recordIndex;'),
        'wrong-packed-slot':b.replace('| (u32)i','| (u32)(i + 1)'),
    }


NATIVE=HEADER+r'''
typedef struct {u8 pad[8];f32 fraction;u8 padC[24];s16 quant;u8 pad26[3];s8 id;u8 tail[90];} Record;
static Record records[128];static u8 before[sizeof(records)];
u8*D_800872A0;s8 D_800D2398;
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static u32 scaled(u32 b){u32 e=(b>>23)&255u,m=(b&0x7FFFFFu)|0x800000u,v;
 if(e<123)return 0;v=e>=146?m<<(e-146):m>>(146-e);return b>>31?0u-v:v;}
static const s32 tags[]={-128,-1,0,127,-128,1,1,-1};
static const u32 offsets[]={1,0,0xFFFFFFFFu,1,0x100u,0x7FFFFFFFu,0xFFFFFFFFu,128};
static const u32 heights[][4]={HEIGHT_ROWS};
u32 func_150882E4(u32,u32);
static int check(u32 c,u32 index,u32 pair,u32 pattern,u32 h,u32 active,u32 overrideHalf){
 u32 i,wanted=(u32)tags[pair]+offsets[pair],count=c<128?c:0,w=0x10,got;
 u32 oldPointer,oldCount;u8*r=(u8*)records;
 D_800872A0=active?r:0;*(u8*)&D_800D2398=(u8)c;
 for(i=0;i<128;i++){*(u8*)&records[i].id=(u8)(wanted+1u);
 records[i].quant=(s16)heights[h][2];records[i].fraction=real(heights[h][3]);}
 if(count){if(pattern==1||pattern==4)*(u8*)&records[0].id=(u8)wanted;
 if(pattern==2)*(u8*)&records[count/2].id=(u8)wanted;
 if(pattern==3||pattern==4)*(u8*)&records[count-1].id=(u8)wanted;}
 if(c==128&&pattern==1)*(u8*)&records[0].id=(u8)wanted;
 records[index].id=(s8)tags[pair];records[index].quant=(s16)(overrideHalf<65536?overrideHalf:heights[h][0]);
 records[index].fraction=real(heights[h][1]);
 if(active)for(i=0;i<count;i++)if((u32)records[i].id==wanted&&i!=index){
 u32 a=(u32)records[index].quant*16u+scaled(word(records[index].fraction));
 u32 b=(u32)records[i].quant*16u+scaled(word(records[i].fraction));
 u32 d=a-b;if(d&0x80000000u)d=0u-d;w=(d<<8)|i;break;}
 for(i=0;i<sizeof(records);i++)before[i]=r[i];oldPointer=(u32)D_800872A0;oldCount=(u8)D_800D2398;
 got=func_150882E4(index,offsets[pair]);if(got!=w)return 23;
 if((u32)D_800872A0!=oldPointer||(u8)D_800D2398!=oldCount)return 23;
 for(i=0;i<sizeof(records);i++)if(r[i]!=before[i])return 23;return 0;}
static int run(void){u32 c,p,i,h,n=0,v,q;int status;
 if(sizeof(void*)!=4||sizeof(Record)!=0x84||__builtin_offsetof(Record,id)!=0x29||
 __builtin_offsetof(Record,quant)!=0x24||__builtin_offsetof(Record,fraction)!=8)return 29;
 for(i=0;i<sizeof(records);i++)((u8*)records)[i]=0xA5;
 status=check(128,127,1,1,0,1,65536);if(status)return status;n++;
 for(c=0;c<256;c++)for(p=0;p<6;p++)for(q=0;q<4;q++)for(i=0;i<2;i++)for(h=0;h<4;h++){
 status=check(c,i?127:0,q,p,h,1,65536);if(status)return status;n++;}
 for(c=0;c<8;c++)for(p=0;p<6;p++)for(i=0;i<2;i++)for(h=0;h<8;h++){
 status=check(16,i?3:0,c,p,h,c!=7,65536);if(status)return status;n++;}
 for(v=0;v<65536;v++){status=check(2,0,1,4,0,1,v);if(status)return status;n++;}
 return n==115457?0:29;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


def native_driver():
    rows=[]
    for x,a,y,b in HEIGHTS:rows.append('{%du,0x%Xu,%du,0x%Xu}'%(x&0xFFFFFFFF,base.bits(a),y&0xFFFFFFFF,base.bits(b)))
    return NATIVE.replace('HEIGHT_ROWS',','.join(rows))


class SeparationQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD;cls.stage=source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin');cls.truth=struct.unpack_from('>51I',cls.rom,source.ROM)
        cls.fixed=source.normalized(cls.words)

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_signed_scan_word_results_read_order_and_complete_slot(self):
        self.assertEqual((self.row['words'],self.row['differences'],self.row['neighbors']),(51,15,72))
        self.assertEqual(self.fixed,list(self.truth));seen=set();count=0
        def cases():
            yield from ((3,0,0,0,4,0,False,p) for p in (0,8))
            yield from ((n,0,*pair,p,h,True,phase) for n,p,pair,h,phase in
                itertools.product(range(256),(0,3),((0,0),(127,1)),(0,2),(0,8)))
            yield from ((n,i,*pair,p,h,True,phase) for n,i,pair,p,h,phase in
                itertools.product((3,16,127),(0,3,127),PAIRS[:4],(1,2,4,5),range(8),(0,8)))
        for n,i,tag,offset,p,h,active,phase in cases():
            memory,args=fixture(n,i,tag,offset,p,h,active,phase);expected,reads=reference(memory,args)
            models=[SeparationOracle(w,memory,args,phase).run() for w in (self.words,self.fixed,self.truth)]
            for m in models:
                self.assertEqual((m.r[2],m.memory,m.setter_reads),(expected,memory,reads))
                self.assertFalse(m.calls);self.assertFalse(m.setter_writes)
                for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            self.assertEqual((models[1].r,models[1].f),(models[2].r,models[2].f));seen.update(models[0].visits);count+=1
        self.assertEqual(count,6402);self.assertTrue(set(range(source.ENTRY,source.ENTRY+204,4))<=seen)
        self.receipt('guest',three_way_cases=count,all256_count_bytes=True,all51_words=True,complete_memory_unchanged=True)

    def test_02_native32_O2_O0_UBSan_word_boundaries_and_controls(self):
        harness=self.out/'native-driver.c';harness.write_text(native_driver())
        for name,opt,body,status in [('O2','-O2',source.SELECTED,0),('O0','-O0',source.SELECTED,0)]+[
                (n,'-O2',b,23) for n,b in controls().items()]:
            unit=self.out/('native-'+name+'.c');unit.write_text(HEADER+body);exe=unit.with_suffix('')
            c=subprocess.run([*native_command(opt),'-mstackrealign',str(unit),str(harness),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(c.returncode,0,c.stderr)
            self.assertEqual(subprocess.run([str(exe)],timeout=180,capture_output=True).returncode,status,name)
        self.receipt('native',cases_per_profile=115457,all256_count_bytes=True,all65536_own_halfwords=True,
            unsigned_arithmetic_wrap=True,UBSan=True,controls=9,finite_signed_float_conversion_only=True)

    def test_03_guest_controls_have_observable_result_differences(self):
        for name,body in controls().items():
            obj,diagnostics=source.compile_owner(self.root,self.out,HEADER+body,'negative-'+name);self.assertFalse(diagnostics)
            data,functions=source.link_owner(self.root,self.out,obj,source.OWNER);f=functions[source.FUNCTION]
            words=struct.unpack_from('>%dI'%(f['size']//4),data,f['value'])
            if name=='unsigned-count':
                memory,args=fixture(128,127,-1,0,1,0);put(memory,RECORDS+0x29,0xFF,1)
                expected,_=reference(memory,args)
                self.assertNotEqual(SeparationOracle(words,memory,args).run().r[2],expected)
                continue
            for n,p,pair,h in itertools.product((3,16,128),(0,1,3,4,5),PAIRS[:5],range(3)):
                memory,args=fixture(n,0,*pair,p,h);expected,_=reference(memory,args)
                m=SeparationOracle(words,memory,args).run()
                if m.r[2]!=expected:break
            else:self.fail('Ineffective separation control: '+name)

    def test_04_independent_original_raw_and_padded_rebased_links(self):
        context=type('OriginalContext',(),dict(root=self.root,out=self.out))
        original=assembly.ViewListSetupTests.original.__func__(context,'original-separation',source.raw_text(self.root/'conker/asm/B3020.s'),source.FUNCTION)
        raws=[]
        for obj in (self.obj,self.padded):
            text,functions,rel=source.parse_object(obj);f=functions[source.FUNCTION]
            raws.append((text[f['value']:f['value']+f['size']],{a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}))
        count=0
        for k,(entry,table,cnt) in enumerate(((source.ENTRY,source.TABLE,source.COUNT),
                (0x16218004,0x12347FFC,0x800D8004),(0x18FFF000,0x12348004,0x800D7FFC))):
            anchors=dict(D_800872A0=table,D_800D2398=cnt);objects=[original]
            for label,(raw,bindings) in zip(('raw','padded'),raws):
                text,missing=emit_function(raw,dict(value=0,size=len(raw)),bindings,source.FUNCTION,anchors);self.assertFalse(missing)
                path=self.out/('rebase-%s-%d.s'%(label,k));path.write_text(text);obj=path.with_suffix('.o')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],check=True,capture_output=True);objects.append(obj)
            bodies=[]
            for j,obj in enumerate(objects):
                script=self.out/('rebase-%d-%d.ld'%(k,j));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
                bodies.append(list(struct.unpack_from('>51I',sections(elf)['.text'][1])))
            self.assertEqual(bodies[0],bodies[2]);self.assertEqual(source.normalized(bodies[1]),bodies[0])
            for n,p,h,phase in itertools.product((0,3,127,128),(0,1,3,4),range(3),(0,8)):
                memory,args=fixture(n,0,-1,0,p,h,phase=phase,table=table,count_address=cnt);expected,reads=reference(memory,args,table,cnt)
                for words in bodies:
                    m=SeparationOracle(words,memory,args,phase,entry).run();self.assertEqual((m.r[2],m.memory,m.setter_reads),(expected,memory,reads))
                count+=1
        self.receipt('rebases',independent_original_raw_padded_links=9,three_way_cases=count,four_bindings=True)

    def test_05_fault_prefixes_and_unqualified_conversions_fail_closed(self):
        count=states=0
        for n,p,h,phase in itertools.product((0,3,128),(0,3,4),range(3),(0,8)):
            memory,args=fixture(n,0,-1,0,p,h,phase=phase);full=SeparationOracle(self.fixed,memory,args,phase).run()
            for fault in range(full.all_accesses):
                pairs=[]
                for words in (self.words,self.fixed,self.truth):
                    m=SeparationOracle(words,memory,args,phase);m.access_fault=fault
                    with self.assertRaises(base.faults.AccessBoundary):m.run()
                    self.assertEqual((m.memory,m.setter_reads),(memory,full.setter_reads[:fault]))
                    pairs.append((m.memory,m.r,m.f,m.events,m.calls,m.setter_reads,m.current_pc,m.delay_of,m.all_accesses))
                self.assertEqual(pairs[1],pairs[2]);count+=1
            states+=1
        rejected=0
        for bits in (0x7FC12345,0x7F800000,0xFF800000,0x4D000000,0xCD000001):
            memory,args=fixture(3,0,-1,0,3);put(memory,RECORDS+8,bits)
            for words in (self.words,self.fixed,self.truth):
                with self.assertRaises(OutsideConversionDomain):SeparationOracle(words,memory,args).run()
            rejected+=1
        self.receipt('faults',states=states,equal_public_fault_prefixes=count,full_normalized_retail_state=True,
            raw_dead_register_equivalence_not_claimed=True,out_of_domain_cases_rejected=rejected,FCSR_not_emulated=True)

    def test_06_bounded_command_caller_delivers_and_forwards_the_word(self):
        entry=0x1509E520;caller=struct.unpack_from('>5I',self.rom,entry-0x14FD2B50)
        common=struct.unpack_from('>3I',self.rom,0x1509E62C-0x14FD2B50)
        self.assertEqual(caller[:3],(0x8CC40008,0x0D4220B9,0x8CC5000C))
        parent=source.raw_text(self.root/'conker/src/game/generated_CB3D0.c');lo,hi=source.function_span(parent,'func_1509E3DC')
        self.assertEqual(parent[lo:hi],'s32 func_1509E3DC() {\n    return 0;\n}')
        count=0
        for n,index,p,h,phase in itertools.product((0,3,127,128),(0,3),(0,3,4),range(3),(0,8)):
            memory,args=fixture(n,index,-1,0,p,h,phase=phase);expected,_=reference(memory,args)
            put(memory,COMMAND+8,args[0]);put(memory,COMMAND+12,args[1])
            for words in (self.words,self.fixed):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+204,4),words))
                connected.update(zip(range(0x1509E62C,0x1509E638,4),common))
                m=SeparationOracle(caller,memory,args,phase,entry,connected);m.r[6]=COMMAND;m.r[4]=m.r[5]=0x12345678
                m.r[29]-=24;put(m.memory,m.r[29]+20,m.r[31]);m.run()
                self.assertEqual(m.forwarded,[args]);self.assertEqual(m.r[2],expected);self.assertEqual(m.r[29],m.before[29])
                self.assertFalse(m.calls)
            count+=1
        self.receipt('caller',paired_bounded_windows=count,actual_argument_loads_and_return=True,parent_production_stub=True)

    def test_07_raw_words_bindings_guards_inputs_and_installed_image(self):
        text,functions,rel=source.parse_object(self.obj);f=functions[source.FUNCTION];raw,bindings=source.checked_object(self.obj)
        for i in range(51):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for i in bindings:
            bad=dict(rel);bad[f['value']+i]=[]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        rows=source.owner_guards(raw,bindings)
        reader=csv.DictReader(io.StringIO(source.raw_read(self.out/'qualified-guards.csv').decode()))
        all_rows=list(reader)
        for row in rows:
            path=self.out/'bad-guard.csv'
            wrong=[dict(r,expected='0x%08X'%(int(r['expected'],16)^1))
                if (r['filename'],r['function'],r['offset'])==(row['filename'],row['function'],row['offset']) else r for r in all_rows]
            with path.open('w',newline='') as stream:
                w=csv.DictWriter(stream,fieldnames=reader.fieldnames);w.writeheader();w.writerows(wrong)
            with self.assertRaisesRegex(ValueError,source.FUNCTION):
                source.emit_padded_assembly(self.obj,self.root/'conker/asm/B3020.s',filename=source.OWNER,word_patches_path=path)
        with source.historical_view(self.root,self.out):
            read_bytes=Path.read_bytes
            for index,p in enumerate(source.INPUTS):
                for path in (self.root/p,self.out/('before-%02d'%index)):
                    with patch.object(Path,'read_bytes',lambda x:read_bytes(x)+b'\n' if x==path else read_bytes(x)):
                        with self.assertRaises(ValueError):source.freeze(self.root,self.out)
            with self.assertRaisesRegex(RuntimeError,'cannot nest'):
                with source.historical_view(self.root,self.out):pass
        self.assertEqual(source.verify(self.root,self.out),self.stage)
        if self.stage=='after':self.assertEqual(source.audit(self.root,self.out)['functions'],6057)


if __name__=='__main__':unittest.main()
