"""Convert local FCTX records and custom artwork to matching DXT1 mip chains."""
from io import BytesIO
import struct
from PIL import Image


def mip_size(width, height):
    return max(1, (width+3)//4)*max(1, (height+3)//4)*8


def decode_fctx(payload, ident):
    if len(payload)<40 or struct.unpack_from('<III',payload)!=(3030004,ident,2) or payload[16:20]!=b'FCTX':
        raise ValueError('Unsupported texture identity or header')
    if payload[36:40]!=b'DXT1':
        raise ValueError('Only verified DXT1 texture records are supported')
    width,height,levels,duplicate=struct.unpack_from('<HHBB',payload,28)
    if not width or not height or width>4096 or height>4096 or levels!=duplicate or not 1<=levels<=13:
        raise ValueError('Invalid texture dimensions/mip count')
    dims=[(max(1,width>>i),max(1,height>>i)) for i in range(levels)]
    blocks={};offset=40
    for i in reversed(range(levels)):
        size=mip_size(*dims[i]);blocks[i]=payload[offset:offset+size];offset+=size
        if len(blocks[i])!=size:raise ValueError('Truncated FCTX mip')
    if offset!=len(payload):raise ValueError('Unexpected FCTX tail')
    return Image.open(BytesIO(dds(width,height,levels,blocks))).convert('RGB')


def dds(width,height,levels,blocks):
    header=bytearray(128)
    struct.pack_into('<IIIIIII',header,0,0x20534444,124,0xa1007,height,width,mip_size(width,height),0)
    struct.pack_into('<I',header,28,levels)
    struct.pack_into('<II4s',header,76,32,4,b'DXT1')
    struct.pack_into('<I',header,108,0x401008)
    return bytes(header)+b''.join(blocks[i] for i in range(levels))


def encode(image,spec,original_header):
    width,height,levels=(spec[k] for k in ('width','height','levels'))
    if image.width*height!=image.height*width:
        raise ValueError('Texture artwork aspect ratio differs from its UV layout')
    blocks={}
    for i in range(levels):
        resized=image.resize((max(1,width>>i),max(1,height>>i)),Image.Resampling.BICUBIC).convert('RGB')
        stream=BytesIO();resized.save(stream,format='DDS',pixel_format='DXT1')
        blocks[i]=stream.getvalue()[128:]
        if len(blocks[i])!=mip_size(resized.width,resized.height):
            raise ValueError('Unexpected DXT1 encoder output')
    header=bytearray(original_header)
    struct.pack_into('<HHBB',header,28,width,height,levels,levels)
    fctx=header+b''.join(blocks[i] for i in reversed(range(levels)))
    struct.pack_into('<I',fctx,12,len(fctx)-16)
    return bytes(fctx),dds(width,height,levels,blocks)
