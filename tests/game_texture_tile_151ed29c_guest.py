"""Private texture tile comparison against an independent command model."""
from pathlib import Path
import itertools,json,os,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-texture-tile-151ed29c-durable'
rom=(root/'conker/conker.us.bin').read_bytes();elf=(root/'conker/build/conker.us.elf').read_bytes()
symbols={r[1]:r[2][1] for r in symbol_rows(elf)};entry=0x151ed29c
commands,image,sizeout=0x300000,0x310000,0x320000;table=0x8009deb0
programs=[list(struct.unpack_from('>101I',rom,0x21a74c)),bound_blob(*payload(out/os.environ.get('TILE_OBJECT','coords-02.o'),'func_151ED29C'),symbols)]
class Machine(FactoryOracle):
    def execute(self,word):
        if word>>26==0 and word&63==7:
            rs,rt,rd=word>>21&31,word>>16&31,word>>11&31
            value=(self.r[rt]^0x80000000)-0x80000000
            self.r[rd]=(value>>(self.r[rs]&31))&0xffffffff;self.r[0]=0
        else:super().execute(word)
def masks(dim):
    count=1;power=2
    if dim>=3:
        while True:
            power*=2;count+=1
            if power>=dim:break
    return count
def fixture(w,h,fmt,size):
    m={STACK+i:0xa5 for i in range(-128,128)}
    for base,n in ((commands-16,64),(image-16,64),(sizeout-8,16)):
        m.update({base+i:(i*29+0x35)&255 for i in range(n)})
    for i in range(272):m[table+i]=rom[0x242970+i]
    put(m,image+6,w,2);put(m,image+8,h,2);m[image+10]=fmt;m[image+11]=size
    return m
def reference(initial,commands=commands,image=image,sizeout=sizeout):
    m=initial.copy();w=read(m,image+6,2);h=read(m,image+8,2);fmt=m[image+10];size=m[image+11]
    raw=(w*h+m[table+size])&0xffffffff;raw=(raw^0x80000000)-0x80000000
    put(m,sizeout,raw>>(m[table+4+size]&31))
    wm,hm=masks(w),masks(h);line=(m[table+8+size]*w+7)>>3
    values=(0xe7000000,0,0xf5000000|((fmt&7)<<21)|((m[table+12+size]&3)<<19),0x07000000,
            0xf5000000|((fmt&7)<<21)|((size&3)<<19)|((line&511)<<9),
            0x00080200|((hm&15)<<14)|((wm&15)<<4),0xf2000000,
            ((((w-1)*4)&0xfff)<<12)|(((h-1)*4)&0xfff))
    for i,v in enumerate(values):put(m,commands+i*4,v)
    return m
dimensions=(0,1,2,3,4,5,7,8,15,16,17,255,256,257,65535)
def main():
    cases=0
    for w,h,fmt,size in itertools.product(dimensions,dimensions,range(8),range(4)):
        initial=fixture(w,h,fmt,size);expected=reference(initial)
        for n,p in enumerate(programs):
            m=Machine(p,initial.copy(),Case(),entry=entry,s={},arguments=(commands,image,sizeout)).run()
            if m.memory!=expected or m.r[2]!=commands+32:
                different=[(hex(a),initial.get(a),expected.get(a),m.memory.get(a)) for a in sorted(set(expected)|set(m.memory)) if expected.get(a)!=m.memory.get(a)]
                print(json.dumps({'case':[w,h,fmt,size],'stream':n,'return':hex(m.r[2]),'different':different[:20]}),flush=True);raise SystemExit(1)
        cases+=1
    report={'cases':cases,'streams':2,'valid_size_indices':True,'uncredited':True}
    (out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
if __name__=='__main__':main()
