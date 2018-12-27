import sys
import time
import math
from socket import *
from random import *
from ctypes import *

# header include the length of the sending data
# the sequence number of the segment
# the ack number of the segment
# the checksum store the checksum of the payload which is an integer
# the types of the segment, include SYN, ACK, FIN, DATA
class Header(Structure):
    _fields_ = [("length", c_int),
               # ("seq_num", c_int),
               ("seq_num", c_long),
               ("ack_num", c_long),
               ("checksum", c_int),
               ("type", c_int)]

def initHeader(length, seq_num, ack_num, checkSum, types):
    header = Header()
    header.length = length
    header.seq_num = seq_num
    header.ack_num = ack_num
    header.checksum = checkSum
    header.type = types
    return header

# check the type of a packet
# exist cases:
#   1) SYN = 1
#   2) ACK = 2
#   3) FIN = 4
#   4) DATA = 8
#   5) SYN/ACK = 3
#   6) FIN/ACK = 6
def checkTypesOfPacket(header):
    types = header.type
    if types == 1:
        return 'S'
    elif types == 2:
        return 'A'
    elif types == 4:
        return 'F'
    elif types == 8:
        return 'D'
    elif types == 3:
        return 'SA'
    elif types == 6:
        return 'FA'
