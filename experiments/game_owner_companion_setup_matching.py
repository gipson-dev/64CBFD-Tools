"""Certified private incoming-home forwarding and setup-prefix scheduling."""
import argparse
import csv
import io
import json
import struct
from pathlib import Path

from tools.experiments import game_owner_companion_setup_candidates as recovery
from tools.pad_generated_object import parse_object

ENTRY,ROM,WORDS=recovery.ENTRY,recovery.ROM,recovery.WORDS
FUNCTION,SOURCE,ORIGINAL=recovery.FUNCTION,recovery.SOURCE,recovery.ORIGINAL
TYPES,EXTRA_TYPES=recovery.TYPES,recovery.EXTRA_TYPES
DECLARATIONS,EXTRA_DECLARATIONS=recovery.DECLARATIONS,recovery.EXTRA_DECLARATIONS
SYMBOLS=recovery.SYMBOLS
SELECTED=recovery.SELECTED.replace('u8 *actor)', 'u8 *volatile actor)').replace(
    '    u8 *endpoint = *(u8 **)(actor + 0x28);\n    u8 *pair;',
    '    u8 *pair = actor;\n    u8 *endpoint = *(u8 **)(pair + 0x28);').replace(
    'work.packet.actor = actor;', 'work.packet.actor = pair;')
PREFIX_MAP=(0,2,5,1,3,8,6,10,9,11,12,7,*range(13,71),4)
FIRST_CALL=0x13C
HEADER=(0x27BDFF28,0xAFBF0034,0xAFB10030,0xAFB0002C,0xAFA400D8,0x8FB100D8,
    0x240E0001,0x24180005,0x8E300028,0xA3AE0094,0xAFB10090,0xAFB00068,0x920F003B)


def normalize(words):
    if len(words)!=176 or tuple(words[:13])!=HEADER:
        raise ValueError('complete 176-word/frame0xD8 private-home shape required')
    result=[words[i] for i in PREFIX_MAP]+list(words[71:])
    # Forward the private home load from A0; store that same captured S1 late.
    result[2]=(4<<21) | (17<<11) | 0x25
    result[70]=(words[4]&~(31<<16)) | (17<<16)
    return result


def constant(value):
    return ('constant',value&0xFFFFFFFF)


def add(value,offset):
    if not offset:return value
    if value[0]=='constant':return constant(value[1]+offset)
    if value[0]=='address':return ('address',value[1],value[2]+offset)
    if value[0]=='add':return add(value[1],value[2]+offset)
    return ('add',value,offset)


def byte(value,index):
    if value[0]=='constant':return constant((value[1]>>(24-index*8))&255)
    return ('byte',value,index)


class PrefixState:
    """Symbolic 32-bit setup state; public objects are disjoint from private SP."""
    def __init__(self):
        self.r=[('register',i) for i in range(32)]
        self.r[0]=constant(0)
        self.r[4]=('address','actor',0)
        self.r[29]=('address','stack',0)
        self.f=[('float-register',i) for i in range(32)]
        self.memory={}
        self.public_reads=[]
        self.home_reads=0

    def get(self,address,size):
        private=address[0]=='address' and address[1]=='stack'
        if not private:
            self.public_reads.append((address,size))
            return ('read',address,size)
        if address[2]==0 and size==4:self.home_reads+=1
        values=[self.memory.get(add(address,i),('initial-byte',add(address,i))) for i in range(size)]
        if all(v[0]=='constant' for v in values):
            return constant(sum(v[1]<<(8*(size-1-i)) for i,v in enumerate(values)))
        if size==4 and values[0][0]=='byte':
            origin=values[0][1]
            if values==[byte(origin,i) for i in range(4)]:
                return origin
        raise ValueError('unwritten or partial private read')

    def put(self,address,value,size):
        if address[0]!='address' or address[1]!='stack':
            raise ValueError('public write in setup prefix')
        if not (-216<=address[2] and address[2]+size<=4):
            raise ValueError('private write leaves owned frame/home')
        for i in range(size):
            self.memory[add(address,i)]=byte(value,4-size+i)

    def execute(self,word):
        op,rs,rt,rd=word>>26,word>>21&31,word>>16&31,word>>11&31
        imm=word&65535; signed=imm if imm<32768 else imm-65536
        if op==9:
            self.r[rt]=add(self.r[rs],signed)
        elif op==15:
            self.r[rt]=constant(imm<<16)
        elif op==13:
            if self.r[rs][0]!='constant':raise ValueError('nonconstant ORI')
            self.r[rt]=constant(self.r[rs][1]|imm)
        elif op==0 and word&63==37:
            if self.r[rs]==constant(0):self.r[rd]=self.r[rt]
            elif self.r[rt]==constant(0):self.r[rd]=self.r[rs]
            else:raise ValueError('unsupported OR')
        elif op in (35,36):
            self.r[rt]=self.get(add(self.r[rs],signed),4 if op==35 else 1)
        elif op in (40,41,43):
            self.put(add(self.r[rs],signed),self.r[rt],{40:1,41:2,43:4}[op])
        elif op==49:
            self.f[rt]=self.get(add(self.r[rs],signed),4)
        elif op==57:
            self.put(add(self.r[rs],signed),self.f[rt],4)
        elif op==17 and rs==4:
            self.f[rd]=self.r[rt]
        else:
            raise ValueError('unsupported/control prefix word 0x%08X'%word)
        self.r[0]=constant(0)


def certify(words):
    normalized=normalize(words)
    if words[FIRST_CALL//4]>>26!=3:
        raise ValueError('first helper boundary moved')
    states=[]
    for body in (words,normalized):
        state=PrefixState()
        for word in body[:FIRST_CALL//4]:
            state.execute(word)
        state.execute(body[FIRST_CALL//4+1])
        states.append(state)
    raw,fitted=states
    if (raw.r,raw.f,raw.memory,raw.public_reads)!=(fitted.r,fitted.f,fitted.memory,fitted.public_reads):
        raise ValueError('prefix state/public-read congruence failed')
    if (raw.home_reads,fitted.home_reads)!=(1,0):
        raise ValueError('exactly one closed private-home read must be forwarded')
    if words[71:]!=normalized[71:]:
        raise ValueError('normalization leaves prefix')
    changed=[i*4 for i,(a,b) in enumerate(zip(words,normalized)) if a!=b]
    if len(changed)!=69:
        raise ValueError('expected exactly69 prefix scheduling/home words')
    return dict(offsets=changed,first_call=FIRST_CALL,private_home=0,
        gpr_and_fp_and_private_memory_equal=True,public_read_order_equal=True,
        one_private_store_load_forwarded=True,actor_endpoint_global_objects_disjoint_from_private_frame=True,
        suffix_words_unchanged=105,retail_lookup=False)


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    return recovery.compile_candidate(root,out,name,body,profile)


def guard_rows(obj):
    text,functions,relocations=parse_object(obj)
    fn=functions[FUNCTION];base=fn['value']
    raw=list(struct.unpack_from('>176I',text,base))
    proof=certify(raw);fitted=normalize(raw)
    old={i:relocations.get(base+i*4,[]) for i in range(176)}
    moved={i:old[source] for i,source in enumerate(PREFIX_MAP)}
    moved.update({i:old[i] for i in range(71,176)})
    rows=[]
    spec=lambda uses:';'.join(kind+':'+name for kind,name in uses) or '-'
    for offset in proof['offsets']:
        i=offset//4
        rows.append(dict(filename='generated_1DF510',function=FUNCTION,offset='0x%X'%offset,
            expected='0x%08X'%raw[i],replacement='0x%08X'%fitted[i],
            expected_relocations=spec(old[i]),replacement_relocations=spec(moved[i]),
            note='Normalize certified companion private argument-home forwarding and prefix schedule',
            insert_after='',insert_after_relocations='',omit='false'))
    for i in range(176):
        if old[i]!=moved[i] and i*4 not in proof['offsets']:
            raise ValueError('unguarded relocation movement')
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-owner-companion-setup-matching'
    records=[]
    for profile in recovery.setup.compiler.PROFILES if args.profiles else ('o2g3',):
        meta,words=compile_candidate(root,out,'selected-'+profile,profile=profile)
        if profile=='o2g3':
            meta['certificate']=certify(words)
            meta['normalized_words']=normalize(words)
            guards=guard_rows(out/('selected-'+profile+'.o'))
            stream=io.StringIO()
            writer=csv.DictWriter(stream,fieldnames=list(guards[0]),lineterminator='\n')
            writer.writerows(guards)
            (out/'guards.csv').write_text(stream.getvalue())
        records.append(meta)
        print(profile,meta['body_words'],meta['frame'],meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
