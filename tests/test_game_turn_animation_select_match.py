"""Turn thresholds, wrapped headings, live table aliases and two authentic callers."""
from dataclasses import dataclass
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_turn_animation_select_candidates as candidate
from tools.experiments import game_turn_animation_select_match as match
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle,STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_envelope_gates_match as windows
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT,TABLE,ACTOR=candidate.ROOT,match.TABLE,0x30000
ACTOR_GLOBAL,NOTICE=0x800D154C,0x800D1891
CALLERS=((0x15057D98,0x15057DEC,0x85248),(0x15077FF0,0x15078068,0xA54A0))
THRESHOLDS=((0,0),(63,127),(200,100),(255,255))
OUTPUTS=(0x44,0x76,0x78,0x7A,0xF4,0x138,0x218,0x21C,0x223,0x244)

@dataclass(frozen=True)
class Case:
    magnitude:int=128
    row:int=0
    delta:int=0x8000
    pattern:int=1
    sentinel:bool=False
    seed:int=0
    layout:int=-10000
    magnitude_upper:int=0xA51234
    row_upper:int=0x5A9876

def owner_at(c,phase=0,table=TABLE):
    if c.layout==-10000:return ACTOR
    if c.layout<-10000:
        return STACK+phase+{-10001:-0x100,-10002:4-0x44,-10003:4-0xF4,
                            -10004:8-0x218,-10005:4-0x78}[c.layout]
    return table+c.layout

def arguments(c,phase=0,table=TABLE):
    return(owner_at(c,phase,table),((c.magnitude_upper&0xFFFFFF)<<8)|(c.magnitude&255),
           ((c.row_upper&0xFFFFFF)<<8)|(c.row&255))

def choose(memory,owner,magnitude,row,table=TABLE):
    address=table+(row&255)*10;value=magnitude&255
    index=5 if memory[address+7]<value else 2 if memory[address+2]<value else 0
    heading=read(memory,owner+0x76,2)
    index+=3 if (read(memory,owner+0x78,2)-heading)&0x8000 else 4
    return address+index,heading

def fixture(c,phase=0,table=TABLE,real_table=None):
    owner=owner_at(c,phase,table)
    memory={STACK+phase+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
    memory.update({table+i:(i*29+c.seed+0x37)&255 for i in range(2560)})
    memory.update({owner+i:(i*13+c.seed+0x59)&255 for i in range(0x254)})
    heading=(c.seed*257+0xFFF0)&0xFFFF
    put(memory,owner+0x76,heading,2);put(memory,owner+0x78,heading+c.delta,2)
    put(memory,owner+0x218,(0,1,4,0x02000004,0x80000003,0xFFFFFFFF)[c.seed%6])
    put(memory,owner+0xF4,(c.seed*0x1234567+0xABCDEF0F)&0xFFFFFFFF)
    if real_table is None:
        address=table+(c.row&255)*10
        memory[address+2],memory[address+7]=THRESHOLDS[c.pattern]
        for i in (3,4,5,6,8,9):memory[address+i]=0xFF if c.sentinel else (c.seed+i*19)&0xFE
    else:memory.update({table+i:v for i,v in enumerate(real_table)})
    return memory

def reference(initial,c,phase=0,table=TABLE,raw_arguments=None,sp=None):
    memory=dict(initial);owner,mag,row=raw_arguments or arguments(c,phase,table)
    stack=STACK+phase if sp is None else sp
    # The retail byte arguments retain their full incoming words in their homes.
    put(memory,stack+4,mag);put(memory,stack+8,row)
    entry,heading=choose(memory,owner,mag,row,table)
    if memory[entry]!=255:
        cursor,flags=read(memory,owner+0x218),read(memory,owner+0xF4)
        put(memory,owner+0x218,cursor-5);put(memory,owner+0x21C,20000,2)
        memory[owner+0x223]=13;put(memory,owner+0x44,0)
        animation=memory[entry]
        put(memory,owner+0xF4,flags&~14);put(memory,owner+0xF4,(flags&~14)|4)
        put(memory,owner+0x78,heading,2);put(memory,owner+0x7A,heading,2)
        memory[owner+0x138]=0;put(memory,owner+0x244,animation,2)
    return memory

class Oracle(RayOracle):
    def __init__(self,words,memory,c=Case(),phase=0,table=TABLE,entry=match.ENTRY,connected=None):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,arguments=arguments(c,phase,table),connected=connected)
        self.hi,self.lo,self.condition=0x89ABCDEF,0x76543210,True
    def record_call(self,target):
        if target!=match.ENTRY:raise AssertionError(('unbounded turn helper',hex(target)))
        args=self.arguments(3);self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):raise AssertionError(('unexpected turn helper',hex(target)))

def controls():
    b=candidate.SELECTED
    result={
      'large-inclusive':b.replace('bytes[7] < magnitude','bytes[7] <= magnitude'),
      'medium-inclusive':b.replace('bytes[2] < magnitude','bytes[2] <= magnitude'),
      'wrong-large-base':b.replace('index = 5;','index = 4;'),
      'wrong-medium-base':b.replace('index = 2;','index = 1;'),
      'wrong-direction-bit':b.replace('& 0x8000','& 0x4000'),
      'wrong-negative-slot':b.replace('index += 3;','index += 4;'),
      'wrong-sentinel':b.replace('*entry != 0xFF','*entry != 0xFE'),
      'wrong-command-step':b.replace('- 5u','- 4u'),
      'wrong-duration':b.replace('unk21C = 20000','unk21C = 19999'),
      'wrong-state':b.replace('unk223 = 13','unk223 = 12'),
      'missing-velocity-clear':b.replace('        actor->unk44 = 0.0f;\n',''),
      'wrong-flag-mask':b.replace('~0xE','~0xF'),
      'wrong-flag-bit':b.replace('~0xE) | 4','~0xE) | 2'),
      'wrong-heading':b.replace('actor->unk7A = heading;','actor->unk7A = 0;'),
      'missing-byte-reset':b.replace('        actor->unk138 = 0;\n',''),
    }
    if any(value==b for value in result.values()):raise ValueError('Ineffective turn control')
    return result

def early_entry_control():
    return candidate.SELECTED.replace('    if (*entry != 0xFF) {',
        '    { u8 cached = *entry;\n    if (cached != 0xFF) {',1).replace('animation = *entry;','animation = cached;',1)+'\n}'

def native_source(body):
    return '''#include <ultra64.h>
#include "structs.h"
typedef void(*Handler)(void*,u8,u8);
static u8 *tableMemory;
#define D_80099A3C tableMemory
static struct127 actual,expected;
''' + body + r'''
static u32 wanted(struct127*p,u8 magnitude,u8 row){
 u8 *r=tableMemory+(u32)row*10;u32 index=0;u16 h=p->unk76;
 if(magnitude>r[7])index=5;else if(magnitude>r[2])index=2;
 index+=((p->unk78-h)&0x8000)?3:4;
 if(r[index]!=255){
  s32 f=p->unkF4;p->unk218=(struct216*)((u32)p->unk218-5u);
  p->unk21C=20000;p->unk223=13;p->unk44=0.0f;
  p->unkF4=(f&~14)|4;p->unk78=h;p->unk7A=h;p->unk138=0;p->unk244=r[index];
 }
 return index;
}
__attribute__((noinline))static void invoke(Handler fn,void*p,u8 a,u8 b){fn(p,a,b);}
static int one(u32 seed,u32 indirect){
 u32 i,index;u8 row=(u8)(seed>>8),magnitude=(u8)seed;u8 *r=tableMemory+(u32)row*10;
 for(i=0;i<sizeof(actual);i++)((u8*)(void*)&actual)[i]=(u8)(i*13u+seed*7u+0x59);
 actual.unk76=(u16)(seed*257u+0xFFF0);actual.unk78=(u16)(actual.unk76+(u16)seed);
 actual.unk218=(struct216*)((u32[]){0,1,4,0x02000004u,0x80000003u,0xFFFFFFFFu}[seed%6]);
 actual.unkF4=(s32)(seed*0x1234567u+0xABCDEF0Fu);
 for(i=0;i<10;i++)r[i]=(u8)(i*19u+seed);
 r[2]=(u8)((seed>>4)*13u);r[7]=(u8)((seed>>6)*29u);
 index=(r[7]<magnitude?5:r[2]<magnitude?2:0)+((seed&0x8000)?3:4);
 r[index]=(seed&3)?(u8)(seed&254):255;
 for(i=0;i<sizeof(actual);i++)((u8*)(void*)&expected)[i]=((u8*)(void*)&actual)[i];
 wanted(&expected,magnitude,row);
 if(indirect)invoke(func_15056A00,&actual,magnitude,row);else func_15056A00(&actual,magnitude,row);
 for(i=0;i<sizeof(actual);i++)if(((u8*)(void*)&actual)[i]!=((u8*)(void*)&expected)[i])return 1;
 return 0;
}
static int run(void){u32 args[6]={0,4096,3,0x22,0xFFFFFFFFu,0};u32 i,j,result;
 if(sizeof(void*)!=4||sizeof(f32)!=4||sizeof(struct216)!=5||
 __builtin_offsetof(struct127,unk44)!=0x44||__builtin_offsetof(struct127,unk76)!=0x76||
 __builtin_offsetof(struct127,unkF4)!=0xF4||__builtin_offsetof(struct127,unk218)!=0x218||
 __builtin_offsetof(struct127,unk244)!=0x244)return 9;
 __asm__ volatile("int $0x80":"=a"(result):"a"(90),"b"(args):"memory");
 if(result>=0xFFFFF000u)return 10;tableMemory=(u8*)result;
 for(i=0;i<65536;i++)for(j=0;j<2;j++)if(one(i,j))return 1;
 return 0;
}
void _start(void){s32 result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''

class GameTurnAnimationSelectMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT)
        cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>66I',cls.rom,match.ROM))
        text,functions,_=parse_object(cls.prepared['qualified_compact']);info=functions[match.FUNCTION]
        cls.raw_blob=text[info['value']:info['value']+match.SIZE]
        cls.fitted_blob,cls.proof=match.normalized(cls.raw_blob,match.BINDINGS,cls.rom[match.ROM:match.ROM+match.SIZE])
        linked,_=link_owner(ROOT,cls.out,cls.prepared['qualified_compact'],match.FILENAME)
        cls.raw=list(struct.unpack_from('>66I',linked,info['value']))
        linked,functions=link_owner(ROOT,cls.out,cls.prepared['qualified_owner'],match.FILENAME)
        cls.fitted=list(struct.unpack_from('>66I',linked,functions[match.FUNCTION]['value']))
        elf=cls.prepared['predecessor_elf'].read_bytes();at=match.elf_slot_offset(elf,TABLE,2560)
        cls.real_table=elf[at:at+2560]

    def receipt(self,name,value):
        (self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    def compare(self,c,phase=0,images=None,entry=match.ENTRY,table=TABLE,initial=None):
        memory=fixture(c,phase,table)if initial is None else initial;expected=reference(memory,c,phase,table)
        models=[Oracle(words,memory,c,phase,table,entry).run()for words in images or(self.retail,self.raw,self.fitted)]
        for model in models:self.assertEqual(model.memory,expected,c);self.assertFalse(model.calls)
        self.assertEqual(complete(models[0]),complete(models[2]));return models

    def test_01_derived_roles_regular_padder_owner_and_literal_image(self):
        r=self.prepared['report'];self.assertEqual((r['words'],r['guards'],r['neighbors'],r['relocations']),(66,10,88,2))
        self.assertEqual((self.proof['GPR_lifetimes'],self.proof['schedule_changes']),(5,0))
        self.assertTrue(r['regular_owner_padder']);self.assertEqual(r['changed_bodies'],[match.FUNCTION]);self.assertEqual(r['strict_exclusions'],0)
        truth=self.rom[match.ROM:match.ROM+match.SIZE]
        for at in range(match.SIZE):
            bad=bytearray(self.raw_blob);bad[at]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),match.BINDINGS,truth)
        for bindings in ({},{0x10:match.BINDINGS[0x10]},{**match.BINDINGS,0x14:[('R_MIPS_LO16','D_80099A3E')]}):
            with self.assertRaises(ValueError):match.normalized(self.raw_blob,bindings,truth)
        for index in (0,4,9):
            rows=[dict(r)for r in self.prepared['predecessor_rows']]+[match.complete_row(r)for r in match.PATCH_ROWS]
            rows[len(self.prepared['predecessor_rows'])+index]['expected']='0x%08X'%(match.GUARD_WORDS[index][1]^1)
            path=self.out/('bad-guard-%d.csv'%index);harness.write_patches(path,self.prepared['fields'],rows)
            with self.assertRaises(ValueError):match.emit_padded_assembly(self.prepared['qualified_compact'],ROOT/match.ASM,word_patches_path=path,filename=match.FILENAME)
        before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes()
        for at in (0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,match.SIZE)):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)

    def test_02_all_byte_arguments_thresholds_sentinels_and_real_data(self):
        count=0;visits=set()
        for mag,pattern,direction,sentinel,phase in itertools.product(range(256),range(4),(0x7FFF,0x8000),(False,True),(0,8)):
            c=Case(mag,(mag*17+pattern*47)&255,direction,pattern,sentinel,mag^pattern)
            models=self.compare(c,phase);visits.update(models[0].visits);count+=1
        for row,mag,delta in itertools.product(range(256),(0,1,127,128,254,255),(0,0x8000)):
            c=Case(mag,row,delta,seed=row);self.compare(c,initial=fixture(c,real_table=self.real_table));count+=1
        for delta,mag in itertools.product((0,1,0x7FFF,0x8000,0xFFFF),(0,63,64,127,128,255)):
            self.compare(Case(mag,255,delta,seed=delta&255));count+=1
        self.assertEqual(visits,set(range(match.ENTRY,match.ENTRY+match.SIZE,4)))
        self.receipt('guest-contract',{'cases_per_body':count,'retail_words_visited':66,'all_unsigned_byte_arguments':True,
            'upper_input_words_retained_in_homes':True,'protected_real_data_bytes':2560,
            'real_data_SHA256':hashlib.sha256(self.real_table).hexdigest(),'actual_table_extent_not_inferred':True})

    def test_03_table_actor_aliases_and_incoming_home_aliases(self):
        count=0
        for layout,mag,delta,pattern,phase in itertools.product(range(-0x254,0x44,4),(0,128,255),(0x7FFF,0x8000),(0,2),(0,8)):
            self.compare(Case(mag,0,delta,pattern,seed=layout&255,layout=layout),phase);count+=1
        for layout,mag,row,delta,phase in itertools.product(range(-10005,-10000),(0,128,255),(0,1,127,255),(0x7FFF,0x8000),(0,8)):
            self.compare(Case(mag,row,delta,layout=layout),phase);count+=1
        self.receipt('aliases',{'cases_per_body':count,'aligned_actor_offsets':len(range(-0x254,0x44,4)),
            'table_can_overlap_actor_and_argument_homes':True,'no_bounds_or_saturation_added':True})

    def test_04_native32_all_byte_pairs_and_heading_deltas(self):
        out=self.out/'native';out.mkdir(exist_ok=True)
        rows=[('positive-'+opt[1:],candidate.SELECTED,opt,0)for opt in('-O0','-O2','-O3')]
        rows.extend((name,body,'-O2',1)for name,body in controls().items())
        for label,body,opt,expected in rows:
            path=out/(label+'.c');binary=path.with_suffix('.elf');path.write_text(native_source(body))
            built=subprocess.run([*native_command(opt),'-fno-strict-aliasing','-mstackrealign',str(path),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            self.assertEqual(subprocess.run([str(binary)],capture_output=True,timeout=60).returncode,expected,label)
        self.receipt('native-contract',{'profiles':['O0','O2','O3'],'direct_cases_per_profile':65536,
            'typed_call_cases_per_profile':65536,'controls':sorted(controls()),'trap_UBSan':True,
            'actor_uses_actual_SDK_struct127':True,'table_uses_fresh_typeless_allocation':True,'synthetic_rows':256})

    def test_05_original_call_windows_gates_homes_and_preserved_outputs(self):
        visits=[set(),set()];counts=[0,0]
        for which,mag,row,delta,phase,allowed in itertools.product(range(2),(0,64,128,255),(0,1,3,255),(0,0x7FFF,0x8000,0xFFFF),(0,8),(False,True)):
            entry,end,rom=CALLERS[which];c=Case(mag,row,delta,seed=mag^row)
            initial=fixture(c,phase);owner=owner_at(c,phase);expected=dict(initial)
            sp=STACK+phase-(0x178 if which==0 else 0x28)
            if which==0:
                initial[TABLE+row*10]=0 if allowed else 255
                put(initial,sp+0x78,0x1234,2);initial[sp+0x153]=mag
                expected=dict(initial);call=allowed
                if call:
                    put(expected,owner+0x76,0x1234,2);put(expected,sp+0x144,0x3FC00000);put(expected,sp+0x4C,13)
                    expected=reference(expected,c,phase,raw_arguments=(owner,mag,row),sp=sp)
            else:
                initial[TABLE+row*10]=0 if allowed else 255
                put(initial,ACTOR_GLOBAL,owner);initial[NOTICE]=0xA7
                expected=dict(initial);put(expected,owner+0x78,read(initial,owner+0x78,2),2)
                difference=(read(expected,owner+0x78,2)-read(expected,owner+0x76,2))&0xFFFF
                high=(difference>>8)&255;distance=(-high)&255 if high&128 else high
                call=initial[TABLE+row*10]<distance
                if call:
                    expected[owner+0x250]=0xA7
                    expected=reference(expected,c,phase,raw_arguments=(owner,distance,row),sp=sp)
            original=list(struct.unpack_from('>%dI'%((end-entry)//4),self.rom,rom));models=[]
            for child in(self.retail,self.raw,self.fitted):
                connected={match.ENTRY+i*4:w for i,w in enumerate(child)}
                model=Oracle(original,initial,c,phase,entry=entry,connected=connected)
                model.r[29]=sp
                if which==0:
                    model.r[3]=row+1;model.r[2]=0xA50000FF if allowed else 0x5A000000
                    model.r[16]=owner;model.r[8]=13;model.f[2]=0x3FC00000
                else:
                    model.r[7]=row;model.r[24]=owner;model.r[8]=ACTOR_GLOBAL;model.r[2]=read(initial,owner+0x78,2)
                model.code=windows.WindowCode(model.code,model,end)
                with self.assertRaises(windows.WindowBoundary):model.run()
                self.assertEqual(model.memory,expected,(which,c,allowed))
                args=(owner,mag,row)if which==0 else(owner,distance,row)
                self.assertEqual(model.calls,[(match.ENTRY,args)]if call else[])
                if which==0 and call:self.assertEqual((model.r[8],model.f[2]),(13,0x3FC00000))
                visits[which].update(model.visits);models.append(model)
            self.assertEqual(complete(models[0]),complete(models[2]));counts[which]+=1
        for which,(entry,end,_)in enumerate(CALLERS):self.assertTrue(set(range(entry,end,4))<=visits[which])
        self.receipt('callers',{'cases_per_body':counts,'window_words':[21,30],
            'first_window_starts_after_floating_eligibility_gate':True,'second_window_wraps_high_angle_byte':True,
            'full_parent_C_or_gameplay_claimed':False})

    def test_06_literal_fault_prefixes_and_sentinel_inactive_fields(self):
        count=0
        for mag,delta,sentinel,phase in itertools.product((0,64,128,255),(0x7FFF,0x8000),(False,True),(0,8)):
            c=Case(mag,0,delta,1,sentinel);initial=fixture(c,phase);done=Oracle(self.retail,initial,c,phase).run()
            for cut in range(done.root_accesses):
                models=[Oracle(words,initial,c,phase)for words in(self.retail,self.fitted)]
                for model in models:
                    model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        c=Case(sentinel=True);initial=fixture(c)
        for offset,size in ((0x44,4),(0xF4,4),(0x138,1),(0x218,4),(0x21C,2),(0x223,1),(0x244,2)):
            for b in range(size):initial.pop(ACTOR+offset+b)
        self.compare(c,initial=initial)
        self.receipt('fault-prefixes',{'fired_prefixes':count,'complete_fitted_private_state_equal':True,
            'raw_fault_registers_not_equated':True,'sentinel_requires_no_state_field_mapping':True})

    def test_07_independent_GNU_table_rebases_and_stack_overlap(self):
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context=type('TurnOriginal',(),dict(root=ROOT,out=self.out))
        original=ViewListSetupTests.original.__func__(context,'original-turn',(ROOT/match.ASM).read_text(),match.FUNCTION)
        objects=(original,self.prepared['qualified_compact'],self.prepared['qualified_owner']);links=count=0
        for index,(entry,table)in enumerate(((match.ENTRY,TABLE),(0x18017FFC,0x800A7FFC),(0x1A028000,0x800A8000),(0x18002000,STACK+4))):
            images=[]
            for ordinal,obj in enumerate(objects):
                data,functions,relocations=parse_object(obj)
                assembly,unknown=emit_function(data,functions[match.FUNCTION],relocations,match.FUNCTION,{'D_80099A3C':table})
                self.assertFalse(unknown);path=self.out/('rebase-%d-%d'%(index,ordinal))
                path.with_suffix('.s').write_text(assembly);path.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(path.with_suffix('.o')),str(path.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(path.with_suffix('.ld')),'-e',match.FUNCTION,
                    '--defsym=D_80099A3C=0x%X'%table,'-o',str(path.with_suffix('.elf')),str(path.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>66I',sections(path.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[2])
            for mag,row,delta in itertools.product((0,128,255),(0,1,255),(0x7FFF,0x8000)):
                self.compare(Case(mag,row,delta),images=images,entry=entry,table=table);count+=1
        self.receipt('rebases',{'GNU_links':links,'cases_per_body':count,'HI_LO_carry_edges':True,'table_can_overlap_incoming_homes':True})

    def test_08_actual_compiled_controls_and_late_table_reload(self):
        results={}
        for label in ('wrong-duration','wrong-flag-mask','wrong-direction-bit'):
            obj,_=compile_owner(ROOT,self.out,candidate.source_with(controls()[label]),'control-'+label)
            text,functions=link_owner(ROOT,self.out,obj,candidate.OWNER);info=functions[match.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(info['size']//4),text,info['value']))
            found=False
            for c in (Case(seed=1),Case(delta=0x4000,seed=2),Case(magnitude=255,seed=3)):
                model=Oracle(words,fixture(c),c).run()
                if model.memory!=reference(fixture(c),c):found=True;break
            self.assertTrue(found,label);results[label]={'guest_counterexample':True,'words':len(words)}
        obj,_=compile_owner(ROOT,self.out,candidate.source_with(early_entry_control()),'control-cached-entry')
        text,functions=link_owner(ROOT,self.out,obj,candidate.OWNER);info=functions[match.FUNCTION]
        words=list(struct.unpack_from('>%dI'%(info['size']//4),text,info['value']))
        c=Case(200,0,0,seed=3,layout=8-0x218);initial=fixture(c)
        initial[TABLE+7]=100;initial[TABLE+2]=50;put(initial,owner_at(c)+0x218,0x02000004)
        actual=Oracle(words,initial,c).run();self.assertNotEqual(actual.memory,reference(initial,c))
        results['cached-entry']={'command_pointer_alias_changes_selected_byte':True,'words':len(words)}
        self.receipt('compiled-controls',results)

if __name__=='__main__':unittest.main()
