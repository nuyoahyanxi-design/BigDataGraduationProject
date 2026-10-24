"""Bounded, single-process CAPTCHA and throttling for the local deployment."""
import base64
import hashlib
import hmac
import secrets
import struct
import threading
import time
import zlib
from collections import OrderedDict
from fastapi import HTTPException

# Raster glyphs: the answer never appears as SVG text or JSON metadata.
GLYPHS = {
 '2':['11110','00001','00001','01110','10000','10000','11111'],
 '3':['11110','00001','00001','01110','00001','00001','11110'],
 '4':['10010','10010','10010','11111','00010','00010','00010'],
 '5':['11111','10000','10000','11110','00001','00001','11110'],
 '6':['01110','10000','10000','11110','10001','10001','01110'],
 '7':['11111','00001','00010','00100','01000','01000','01000'],
 '8':['01110','10001','10001','01110','10001','10001','01110'],
 '9':['01110','10001','10001','01111','00001','00001','01110'],
 'A':['01110','10001','10001','11111','10001','10001','10001'],
 'B':['11110','10001','10001','11110','10001','10001','11110'],
 'D':['11110','10001','10001','10001','10001','10001','11110'],
 'E':['11111','10000','10000','11110','10000','10000','11111'],
 'F':['11111','10000','10000','11110','10000','10000','10000'],
 'H':['10001','10001','10001','11111','10001','10001','10001'],
}

def raster(answer):
    width,height=180,60
    pixels=bytearray([250,247,241]*(width*height))
    def dot(x,y,color):
        if 0<=x<width and 0<=y<height:
            pos=(y*width+x)*3;pixels[pos:pos+3]=bytes(color)
    for _ in range(420):dot(secrets.randbelow(width),secrets.randbelow(height),(210,195,182))
    for i,letter in enumerate(answer):
        offset=11+secrets.randbelow(9)
        for y,row in enumerate(GLYPHS[letter]):
            for x,bit in enumerate(row):
                if bit=='1':
                    for dy in range(4):
                        for dx in range(4):dot(14+i*32+x*4+dx,y*4+offset+dy,(112,67,51))
    raw=b''.join(b'\x00'+pixels[y*width*3:(y+1)*width*3] for y in range(height))
    def chunk(name,data):return struct.pack('!I',len(data))+name+data+struct.pack('!I',zlib.crc32(name+data)&0xffffffff)
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
    return 'data:image/png;base64,'+base64.b64encode(png).decode('ascii')

class AuthChallenges:
    def __init__(self):
        self.lock=threading.Lock();self.key=secrets.token_bytes(32)
        self.challenges=OrderedDict();self.attempts=OrderedDict()
    def digest(self,value):return hmac.new(self.key,value.encode(),hashlib.sha256).hexdigest()
    def throttle(self,key,limit=20,window=300):
        now=time.monotonic();key=self.digest(key)
        with self.lock:
            for expired in [k for k,v in self.attempts.items() if v[1]<=now]:self.attempts.pop(expired,None)
            count,end=self.attempts.get(key,(0,now+window))
            if count>=limit or (key not in self.attempts and len(self.attempts)>=10000):
                raise HTTPException(429,'Too many attempts; try later',headers={'Retry-After':str(max(1,int(end-now)))})
            self.attempts[key]=(count+1,end)
    def create(self):
        now=time.monotonic();answer=''.join(secrets.choice(tuple(GLYPHS)) for _ in range(5));identifier=secrets.token_urlsafe(24)
        with self.lock:
            for expired in [k for k,v in self.challenges.items() if v[1]<=now]:self.challenges.pop(expired,None)
            if len(self.challenges)>=10000:raise HTTPException(429,'Too many challenges')
            self.challenges[identifier]=(self.digest(answer),now+120)
        return {'captcha_id':identifier,'image':raster(answer),'expires_in':120}
    def verify(self,identifier,answer):
        with self.lock:entry=self.challenges.pop(identifier or '',None)
        value=answer.get_secret_value() if answer else ''
        if not entry or entry[1]<=time.monotonic() or not hmac.compare_digest(entry[0],self.digest(value.strip().upper())):
            raise HTTPException(400,'CAPTCHA invalid or expired')

guard=AuthChallenges()
