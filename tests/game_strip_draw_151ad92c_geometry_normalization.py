"""Checked second-basis allocation/schedule derivation; no full-function adoption."""
from pathlib import Path
import hashlib
import json,struct
from tools.tests import game_strip_draw_151ad92c_basis_normalization as first
from tools.experiments import game_strip_draw_151ad92c_geometry as source
p=source.OUT
BASE=0x1ADC
index=lambda a:(a-BASE)//4

def fp(word,*,ft=None,fs=None,fd=None):
    assert word>>26==17 and word>>21&31==16
    for value,shift in ((ft,16),(fs,11),(fd,6)):
        if value is not None:word=word&~(31<<shift)|value<<shift
    return word

def derive(raw):
    region=struct.pack('>'+str(index(0x1F20)-index(0x1DAC))+'I',*raw[index(0x1DAC):index(0x1F20)])
    digest=hashlib.sha256(region).hexdigest();assert digest==source.PIN['second_region_sha256']
    words,previous=first.derive(raw)
    before=words[:]
    mapping={12:18,14:16,16:12,18:14}
    for i in range(index(0x1DAC),index(0x1F20)):
        w=words[i];op=w>>26;fmt=w>>21&31
        if op==17:
            shifts=(16,11,6)if fmt==16 else (11,)
        elif op in (49,57):shifts=(16,)
        else:shifts=()
        for shift in shifts:
            reg=w>>shift&31;w=w&~(31<<shift)|mapping.get(reg,reg)<<shift
        words[i]=w
    edits={}
    def change(at,value,why):
        old=words[index(at)];assert old!=value
        edits[at]=dict(index=index(at),expected_word=old,replacement_word=value,reason=why)
        words[index(at)]=value
    at=lambda a:words[index(a)]
    change(0x1E24,at(0x1E24)&~(31<<16)|16<<16,'retain current Y in dead reciprocal register')
    change(0x1E58,at(0x1E58)&~(31<<16),'retain current Z in dead norm register')
    for address,fields,reason in (
        (0x1E30,dict(fs=16,fd=6),'Y plus'),
        (0x1E34,dict(fs=6,fd=8),'truncate Y plus'),
        (0x1E64,dict(fs=0,fd=10),'Z plus'),
        (0x1E68,dict(fd=6),'X minus'),
        (0x1E6C,dict(fs=10,fd=4),'truncate Z plus'),
        (0x1E90,dict(fs=6,fd=8),'truncate X minus'),
        (0x1EC8,dict(fs=16,fd=10),'Y minus'),
        (0x1ECC,dict(fs=10,fd=4),'truncate Y minus'),
        (0x1EFC,dict(fs=0),'Z minus')):
        change(address,fp(at(address),**fields),reason)
    for address,register in ((0x1E38,8),(0x1E78,4),(0x1E9C,8),(0x1ED0,4)):
        w=at(address);assert w>>26==17 and w>>21&31==0
        change(address,w&~(31<<11)|register<<11,'consume relocated truncated coordinate')
    order=(0x1DDC,0x1DE0,0x1DE4,0x1E58,0x1DF8,0x1E24,0x1DE8,0x1DFC,
        0x1DF0,0x1E08,0x1E00,0x1E0C,0x1E10,0x1E14,0x1E04,0x1E18,0x1E30,0x1E1C,
        0x1E20,0x1E28,0x1E34,0x1E2C,0x1E64,0x1E38,0x1E68,0x1E6C,0x1E3C,
        0x1E40,0x1E44,0x1E48,0x1E4C,0x1E50,0x1E54,0x1E5C,0x1E78,0x1E60,
        0x1E90,0x1EC8,0x1EFC,0x1E70,0x1E74,0x1E7C,0x1E80,0x1E84,0x1E88,
        0x1E8C,0x1E94,0x1E9C,0x1E98,0x1ECC,0x1F00,0x1EA0,0x1EA4,0x1EA8,
        0x1EAC,0x1EB0,0x1EB4,0x1EB8,0x1EC0,0x1ED0,0x1EC4,0x1ED4,0x1ED8,
        0x1EDC,0x1EE0,0x1EE4,0x1EE8,0x1EEC,0x1EF4,0x1F04,0x1EF8,0x1F08,
        0x1F0C,0x1F10,0x1F14,0x1F18,0x1F1C)
    start,end=index(0x1DDC),index(0x1F20)
    removed={0x1DEC,0x1DF4,0x1EBC,0x1EF0}
    assert len(order)==77 and len(set(order))==77
    assert set(order)|removed==set(range(0x1DDC,0x1F20,4))
    assert at(0x1DEC)==at(0x1DF4)==0
    assert at(0x1EBC)==0xC7A60104 and at(0x1EF0)==0xC7A40100
    words[start:end]=[at(a)for a in order]+[0]*4
    assert len(words)==len(raw)==469
    branch=lambda w:w>>26 in(1,2,3,4,5,6,7,20,21,22,23)or w>>26==17 and w>>21&31==8
    assert all(not branch(w)or words[i]==w for i,w in enumerate(before))
    record=dict(previous=previous,FP_allocation={str(k):v for k,v in mapping.items()},operand_edits=list(edits.values()),
        source_instruction_order=list(order),redundant_private_loads=[index(0x1EBC),index(0x1EF0)],
        trailing_vacant_slots=4,words=len(words),all_branch_words_and_positions_unchanged=True,checked_source_region_sha256=digest)
    return words,record

CHECKED_INDICES=sorted({first.index(a)for a in first.PINS}|set(range(index(0x1DAC),index(0x1F20))))
