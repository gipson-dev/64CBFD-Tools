"""Owner gates, unsigned conversion, private homes and guarded scale-timer words."""
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_scale_timer as source
from tools.tests import game_view_point_projection_oracle as point
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

STACK,ACTOR,OWNER,MODEL,OTHER=point.STACK,0x20000,0x30000,0x40000,0x50000
FCSRS=(0,3,0x800004,0xA5A50003)


def fixture(gate=0,time=4.,limit=5.,base=255.75,decay=2.,step=1.,alias=0,symbols=None):
    s=symbols or source.SYMBOLS;actor=(ACTOR,s['D_800BE9A4']-0x2C,s['D_800BE9A4']-0x30,
        s['D_800BE9A4']-0x5C,s['D_800BE9A4']-0x118)[alias]
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-128,128)}
    for a in (actor,OWNER,OTHER):memory.update({a+i:0xA5 for i in range(0x240)})
    for a in (actor,OTHER):
        put(memory,a+0x110,OWNER);put(memory,a+0x114,0x7f,1)
        for off,v in ((0x118,time),(0x11C,limit),(0x120,1.5),(0x124,base),(0x128,decay)):
            put(memory,a+off,v if isinstance(v,int) else point.bits(v))
    put(memory,OWNER,0 if gate==1 else 1);put(memory,OWNER+0x3B,0xff if gate==2 else 0x7f,1)
    put(memory,OWNER+0x1D4,0 if gate==3 else MODEL)
    put(memory,s['D_800BE9A4'],step if isinstance(step,int) else point.bits(step))
    return memory,actor


def actions(mode,actor,data,stack):
    if mode==1:return [(data+8,point.bits(9.),4),(data+0x10,point.bits(2.),4),
        (data+0x14,point.bits(127.5),4),(data+0x18,point.bits(.25),4)]
    if mode==2:return [(stack+0x18,OTHER+0x110,4),(stack+0x28,OTHER,4)]
    if mode==3:return [(stack+0x28,OTHER,4)]
    if mode==4:return [(stack+0x18,OTHER+0x110,4)]
    return []


def reference(initial,actor,mode=0,phase=0,symbols=None):
    memory=dict(initial);s=symbols or source.SYMBOLS;data=actor+0x110;owner=read(memory,data);calls=[]
    if read(memory,owner)==0 or read(memory,data+4,1)!=read(memory,owner+0x3b,1):return memory,0,calls
    model=read(memory,owner+0x1d4)
    if model==0:return memory,0,calls
    calls.append((s['func_15143134'],(s['D_800A1950'],actor+0x34,model+0x3c0)))
    for i,v in enumerate((11.25,-2.5,3.75)):put(memory,actor+0x34+i*4,point.bits(v))
    stack=STACK+phase-0x28
    for a,v,n in actions(mode,actor,data,stack):
        if not STACK-128<=a<STACK+128:put(memory,a,v,n)
    if mode in (2,3):actor=OTHER
    if mode in (2,4):data=OTHER+0x110
    time=point.floating(read(memory,data+8))
    scale=point.mul(point.bits(math.sqrt(time) if time>=0 else math.nan),read(memory,data+0x10))
    put(memory,actor+0x30,scale);put(memory,actor+0x2c,scale)
    value=point.sub(read(memory,data+0x14),point.mul(point.mul(read(memory,data+0x18),read(memory,data+8)),read(memory,data+8)))
    number=point.floating(value)
    byte=math.trunc(number)&255 if math.isfinite(number) and -1.<number<2**32 else 255
    put(memory,actor+0x5c,byte,1)
    put(memory,data+8,point.add(read(memory,data+8),read(memory,s['D_800BE9A4'])))
    return memory,0 if point.floating(read(memory,data+0xc))<point.floating(read(memory,data+8)) else 1,calls


class Oracle(point.PointProjectionOracle):
    def __init__(self,words,memory,actor,mode=0,phase=0,fcsr=0,entry=source.ENTRY,symbols=None):
        super().__init__(words,memory,(actor,),[],phase,entry)
        self.mode=mode;self.actor=actor;self.data=actor+0x110;self.symbols=symbols or source.SYMBOLS
        self.fcsr=self.initial_fcsr=fcsr

    def execute(self,word):
        op,rs,fn=word>>26,word>>21&31,word&63
        if op==17 and (rs in (2,6) or rs==16 and fn==36):AreaOracle.execute(self,word)
        elif op==17 and rs==16 and fn==4:
            value=point.floating(self.f[word>>11&31]);self.f[word>>6&31]=point.bits(math.sqrt(value) if value>=0 else math.nan)
            self.r[0]=0
        else:super().execute(word)

    def record_call(self,target):
        if target!=self.symbols['func_15143134']:raise ValueError('Unknown scale-timer provider '+hex(target))
        args=self.arguments(3);self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        args=self.calls[-1][1]
        for i,v in enumerate((11.25,-2.5,3.75)):self.put(args[1]+i*4,point.bits(v),4)
        for at,v,n in actions(self.mode,self.actor,self.data,self.r[29]):self.put(at,v,n)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)]


def state(m):return point.state(m),m.condition,m.lo,m.fcsr
def public(memory):return {a:v for a,v in memory.items() if not STACK-128<=a<STACK+128}


class ScaleTimerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.truth=list(struct.unpack_from('>90I',(cls.out/'before-retail_rom').read_bytes(),source.ROM))

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,memory,actor,mode=0,phase=0,fcsr=0,images=None,entry=source.ENTRY,symbols=None):
        expected,result,calls=reference(memory,actor,mode,phase,symbols)
        machines=[Oracle(w,memory,actor,mode,phase,fcsr,entry,symbols).run() for w in (images or [self.truth,*self.images])]
        for m in machines:
            self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.r[2],result)
            self.assertEqual(m.calls,calls);self.assertEqual(m.fcsr,fcsr)
        for m in machines[1:]:self.assertEqual(state(machines[0]),state(m))
        return machines

    def test_01_literal_shape_guards_and_neighbors(self):
        source.checked_parts(*source.parts(self.obj));self.assertEqual(self.row['frame'],40)
        self.assertEqual(self.row['unchanged_raw_padded_neighbors'],11);self.assertEqual(self.images[1],self.truth)
        self.assertEqual([(i*4,b,a) for i,(a,b) in enumerate(zip(self.truth,self.images[0])) if a!=b],list(source.GUARDS))
        raw,bindings=source.parts(self.obj);wrong=bytearray(raw);wrong[120]^=1
        with self.assertRaises(ValueError):source.checked_parts(bytes(wrong),bindings)
        wrong=dict(bindings);wrong[84]=[('R_MIPS_26','func_15143130')]
        with self.assertRaises(ValueError):source.checked_parts(raw,wrong)
        self.assertTrue((self.out/'expected-guards.csv').read_bytes().startswith((self.out/'before-guards').read_bytes()))
        bad=self.out/'bad-guards.csv';bad.write_text((self.out/'expected-guards.csv').read_text().replace('0x46002082','0x46002083'))
        with self.assertRaises(ValueError):source.padded_object(self.root,self.out,self.obj,'bad',bad)
        self.receipt('shape',words=90,frame=40,raw_differences=2,exact_padded=True,guards=2,neighbors=11)

    def test_02_gates_conversion_boundaries_and_aliases(self):
        count=0;seen=set()
        for gate,time,base,decay,limit,phase,fcsr in itertools.product(range(4),(0.,.25,4.),
                (255.75,-.5,-1.,2147483648.,4294967040.,4294967296.,0x7fc12345),
                (0.,2.),(0.,5.),(0,8),FCSRS):
            memory,actor=fixture(gate,time,limit,base,decay)
            seen.update(self.compare(memory,actor,phase=phase,fcsr=fcsr)[0].visits);count+=1
        alias_count=0
        for alias,mode,phase in itertools.product(range(5),range(5),(0,8)):
            self.compare(*fixture(alias=alias),mode=mode,phase=phase);alias_count+=1
        edges=0
        for time,limit,step in itertools.product((-0.,-1.,float('inf'),0x7fc54321),
                (-float('inf'),float('inf'),0x7fc11111),(0.,1.,float('inf'))):
            seen.update(self.compare(*fixture(time=time,limit=limit,step=step))[0].visits);edges+=1
        # Later fields must remain unread behind the first two rejection gates.
        for gate in (1,2):
            memory,actor=fixture(gate)
            for at in (OWNER+0x1D4,actor+0x118,source.SYMBOLS['D_800BE9A4']):
                for i in range(4):memory.pop(at+i,None)
            self.compare(memory,actor)
        self.receipt('semantics',core=count,FP_model_edges=edges,aliases_and_call_home_mutations=alias_count,reachable_words=len(seen),
            bounded_unsigned_conversion=True,FCSR_restored=True,provider_is_opaque=True,no_hardware_FP_claim=True)

    def test_03_every_selected_access_fault_prefix(self):
        count=0
        for gate,base,mode,phase in itertools.product(range(4),(255.75,4294967040.),range(5),(0,8)):
            memory,actor=fixture(gate,base=base);done=Oracle(self.truth,memory,actor,mode,phase).run()
            for cut in range(done.all_accesses):
                machines=[Oracle(w,memory,actor,mode,phase) for w in (self.truth,*self.images)]
                for m in machines:
                    m.access_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(state(machines[0]),state(machines[1]));self.assertEqual(state(machines[0]),state(machines[2]));count+=1
        self.receipt('faults',complete_modeled_access_prefixes=count,provider_accesses_excluded=True,
            no_portable_C_or_CP0_FCSR_fault_claim=True)

    def test_04_independent_symbol_rebases(self):
        count=0
        for group,entry in enumerate((0x15207FF0,0x15610000,0x15228000)):
            addresses=((0x80317FFC,0x15318000,0x80338004),(0x80418004,0x15427FFC,0x80438000),
                (0x80517FF0,0x15528004,0x80537FFC))[group]
            symbols=dict(zip(source.SYMBOLS,addresses));words=source.linked(self.root,self.out,self.obj,'rebase-'+str(group),entry,symbols)
            for at,old,new in source.GUARDS:
                self.assertEqual(words[at//4],old);words[at//4]=new
            for gate,base,phase in itertools.product(range(4),(255.75,4294967040.),(0,8)):
                self.compare(*fixture(gate,base=base,symbols=symbols),phase=phase,images=[words],entry=entry,symbols=symbols);count+=1
        self.receipt('rebases',independent_links=3,cases=count,HI16_carry_and_call_target=True)

    def test_05_native32_typed_objects_and_effective_controls(self):
        driver=self.out/'native-driver.c';driver.write_text('#include <ultra64.h>\n'+NATIVE)
        head='#include <ultra64.h>\n'+source.TYPE
        controls={'timer':source.SELECTED.replace('+= D_800BE9A4','-= D_800BE9A4'),
            'width':source.SELECTED.replace('actor[0x5C] =','*(u32 *)(actor + 0x5C) ='),
            'decay':source.SELECTED.replace('*(f32 *)(data + 0x18) * *(f32 *)(data + 8) * *(f32 *)(data + 8)',
                '*(f32 *)(data + 0x18) * *(f32 *)(data + 8)')}
        for opt in ('-O2','-O0'):
            for label,body in (('selected',source.SELECTED),*controls.items()):
                path=self.out/('native-'+label+'.c');path.write_text(head+body+'\n');exe=self.out/('native-'+label+opt)
                subprocess.run(native_command(opt)+['-mstackrealign','-fno-builtin',str(path.relative_to(self.root)),str(driver.relative_to(self.root)),'-o',str(exe)],cwd=self.root,capture_output=True,check=True)
                result=subprocess.run([str(exe)],capture_output=True)
                if label=='selected':self.assertEqual(result.returncode,0,(opt,result.stderr))
                else:self.assertNotEqual(result.returncode,0,(opt,label))
        self.receipt('native',cases_per_profile=1536,profiles=['O2','O0'],UBSan=True,typed_objects=True,
            effective_controls=6,invalid_FP_and_private_aliases_excluded=True)

    def test_06_callback_table_and_frozen_inputs(self):
        source.freeze(self.root,self.out)
        rom=(self.out/'before-retail_rom').read_bytes()
        self.assertEqual(struct.unpack_from('>I',rom,0x22E810)[0],source.ENTRY)
        table=(self.root/'conker/asm/data/22E730.rodata.s').read_text()
        self.assertIn('22E810 80089D50 150F3214',table)
        self.receipt('inputs',protected_entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),
            callback_slot=0x80089D50,full_dispatcher_or_transform_callee_not_qualified=True)


    def test_07_complete_first_image_and_historical_adapters(self):
        from tools.experiments import game_actor_scale_timer_installation as install
        from tools.tests import actor_scale_timer_checkpoint as checkpoint
        out=self.root/install.BUILD;expected=install.expected_inputs(self.root,out)
        self.assertEqual(json.loads((out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual((out/'prelink-prediction.elf').read_bytes(),expected['elf'])
        self.assertTrue(expected['guards'].startswith((out/'before-guards').read_bytes()))
        self.assertEqual(expected['guards'][len((out/'before-guards').read_bytes()):].count(b'\n'),2)
        if not (out/'after-elf').exists():self.receipt('installation',installed=False,first_image_qualified=True);return
        original=Path.read_bytes;count=0
        for key,data in expected.items():
            self.assertEqual((self.root/source.PATHS[key]).read_bytes(),data)
            self.assertEqual(checkpoint.previous_input(data,source.PATHS[key],self.root),(out/('before-'+key)).read_bytes())
            for stage in ('before','after'):
                path=out/(stage+'-'+key);wrong=bytearray(path.read_bytes());wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(p):return wrong if p==path else original(p)
                with patch.object(Path,'read_bytes',altered):
                    with self.assertRaisesRegex(AssertionError,'Changed scale-timer checkpoint fixture'):
                        checkpoint.previous_input(data,source.PATHS[key],self.root)
                count+=1
        for key in checkpoint.FOLLOWUP:
            data=install.followup_text((out/('before-'+key)).read_text()).encode()
            self.assertEqual(hashlib.sha256(data).hexdigest(),checkpoint.FOLLOWUP[key])
            self.assertEqual((self.root/source.PATHS[key]).read_bytes(),data)
            self.assertEqual(checkpoint.previous_input(data,source.PATHS[key],self.root),(out/('before-'+key)).read_bytes())
            for stage in ('before','after'):
                path=out/(stage+'-'+key);wrong=bytearray(path.read_bytes());wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(p):return wrong if p==path else original(p)
                with patch.object(Path,'read_bytes',altered):
                    with self.assertRaisesRegex(AssertionError,'Changed scale-timer checkpoint fixture'):
                        checkpoint.previous_input(data,source.PATHS[key],self.root)
                count+=1
        old,_,oa=load_elf_functions(str(out/'before-elf'),'mips-linux-gnu-objdump')
        new,_,na=load_elf_functions(str(out/'after-elf'),'mips-linux-gnu-objdump')
        self.assertEqual(oa,na);self.assertEqual(set(old),set(new));self.assertEqual([n for n in old if old[n]!=new[n]],[source.FUNCTION])
        old_symbols=[(n,(f[1],source.SIZE if n==source.FUNCTION else f[2],*f[3:])) for _,n,f,_ in symbol_rows((out/'before-elf').read_bytes())]
        self.assertEqual(sorted(old_symbols),sorted((n,f[1:]) for _,n,f,_ in symbol_rows(expected['elf'])))
        owned={source.PATHS[k] for k in (*expected,*checkpoint.FOLLOWUP)}
        for key,path in source.PATHS.items():
            if path not in owned:self.assertEqual((self.root/path).read_bytes(),(out/('before-'+key)).read_bytes())
        data=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        self.receipt('installation',installed=True,whole_first_image_exact=True,metadata_exclusions=0,
            compared_bodies=len(old),only_target_changed=True,all_addresses_preserved=True,game_data=data,
            checkpoint_controls=count,test_only_historical_followup=1,all_other_protected_inputs_unchanged=True)


NATIVE=r'''
typedef struct {u8 *owner;u8 epoch,pad[3];f32 time,limit,multiplier,base,decay;} Data;
typedef struct {u8 pad0[0x2C];f32 scale0,scale1,position[3];u8 pad40[0x1C];u8 value,guard[3];u8 pad60[0xB0];Data data;} Actor;
typedef struct {s32 active;u8 pad4[0x37];u8 epoch;u8 pad3C[0x198];u8 *model;} Owner;
static Actor actor;static Owner owner;static u8 model[0x400];
f32 D_800A1950[3],D_800BE9A4;
s32 func_150F3214(u8 *);
f32 sqrtf(f32 v){f32 out;__asm__("sqrtss %1,%0":"=x"(out):"x"(v));return out;}
static int calls,bad;
void func_15143134(f32 *a,f32 *out,u8 *m){
if(a!=D_800A1950||out!=actor.position||m!=model+0x3C0)bad=1;
calls++;out[0]=11.25f;out[1]=-2.5f;out[2]=3.75f;}
static int run(void){int g,t,b,d,l,s,i,n=0,expected;f32 value,time,scale;
static f32 times[]={0.f,.25f,1.f,4.f},bases[]={64.5f,255.75f,2147484672.f,4294967040.f};
if(sizeof(void*)!=4||__builtin_offsetof(Actor,data)!=0x110||__builtin_offsetof(Owner,model)!=0x1D4)return 20;
for(g=0;g<4;g++)for(t=0;t<4;t++)for(b=0;b<4;b++)for(d=0;d<4;d++)for(l=0;l<3;l++)for(s=0;s<2;s++){
actor.data.owner=(u8 *)&owner;actor.data.epoch=127;owner.active=g==1?0:1;owner.epoch=g==2?255:127;owner.model=g==3?0:model;
actor.data.time=times[t];actor.data.limit=(f32)l*2.f;actor.data.multiplier=1.5f;actor.data.base=bases[b];actor.data.decay=(f32)d*.5f;
D_800BE9A4=s?.25f:1.f;actor.scale0=17.f;actor.scale1=19.f;actor.value=0xA5;for(i=0;i<3;i++){actor.guard[i]=0xA5;actor.position[i]=23.f;}
calls=bad=0;time=times[t];scale=sqrtf(time)*1.5f;value=bases[b]-((f32)d*.5f*time)*time;
expected=g?0:!((f32)l*2.f<time+D_800BE9A4);
if(func_150F3214((u8 *)&actor)!=expected||calls!=(g==0)||bad)return 22;
if(g==0){if(actor.scale0!=scale||actor.scale1!=scale||actor.value!=(u8)(u32)value||actor.data.time!=time+D_800BE9A4||
actor.position[0]!=11.25f||actor.position[1]!=-2.5f||actor.position[2]!=3.75f)return 23;}
else if(actor.scale0!=17.f||actor.scale1!=19.f||actor.value!=0xA5||actor.data.time!=time||actor.position[0]!=23.f)return 24;
for(i=0;i<3;i++)if(actor.guard[i]!=0xA5)return 25;n++;}
return n==1536?0:26;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''

if __name__=='__main__':unittest.main()
