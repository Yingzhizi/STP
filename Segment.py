from Header import Header
from ctypes import *

class Segment(Structure):
    _fields_ = [("header", Header),
                ("size", c_int)]

def initSegment(header, size):
    seg = Segment()
    seg.header = header
    seg.size = size
    return seg
