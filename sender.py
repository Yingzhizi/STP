import sys
import time
import math
import ctypes
import struct
import binascii
import hashlib
from socket import *
from random import *
from Header import *
from Segment import *
from ctypes import *
from threading import *
import random

# three way handshack (SYN, SYN + ACK, ACK)
# ACK send by the sender should not contain any payload

receiver_host_ip = str(sys.argv[1])
receiver_port = int(sys.argv[2])
filename = str(sys.argv[3])
MWS = int(sys.argv[4])
MSS = int(sys.argv[5])
gamma = int(sys.argv[6])
pDrop = float(sys.argv[7])
pDuplicate = float(sys.argv[8])
pCorrupt = float(sys.argv[9])
pOrder = float(sys.argv[10])
maxOrder = int(sys.argv[11])
pDelay = float(sys.argv[12])
maxDelay = int(sys.argv[13])
seed = int(sys.argv[14])
random.seed(seed)

#set the initial sequence Number
seqNum = 1
# the ack is always 1 after 3-way handshack
ack = 1

#counter, used for print out the static
seg_trans = 0
seg_RXT = 0
seg_fast_RXT = 0
dup_acks = 0

# set the flag as the an interger
SYN = 1
ACK = 2
FIN = 4
DATA = 8

# connet socket to receiver
s = socket(AF_INET,SOCK_DGRAM)
addr = (receiver_host_ip, receiver_port)

# ready to write to the Sender_log.txt
receiver_log = open ("Sender_log.txt", "a")

# get the file size
# open tht file want to send then get read the file get the length
# which is the size in bytes
f = open (filename, 'rb')
filesize = len(f.read())
f.close()


# first step of 3-way handshack, send SYN to receiver
def handShackInitSend():
    # create a header
    header = initHeader(0, 0, 0, checkSum, SYN)
    # create a segment
    segment = initSegment(header, header.length)
    # send the segment without any data
    packed = convertSegToByte(segment)
    s.sendto(packed, addr)
    currTime = time.time()
    diff = currTime - baseTime
    recordSegment(diff, header, 'snd')

# received SYN+ACK from the receiver
def handShackRcv():
    (raw, addr) = s.recvfrom(2048)
    currTime = time.time()
    diff = currTime - baseTime
    (seg, dataByte) = getSegmentAndData(raw)
    recordSegment(diff, seg.header, "rcv")
    return seg.header

# last step of 3-way handshack, send ACK to receiver
def handShackSend (ackRcv):
    header = initHeader(0, ackRcv, 1, checkSum, ACK)
    # create a segment
    segment = Segment(header, header.length)
    packed = convertSegToByte(segment)
    s.sendto(packed, addr)
    currTime = time.time()
    diff = currTime - baseTime
    recordSegment(diff, header, 'snd')

# used for teardown the connection, listen from receiver
def recvSegment():
    raw, addr = s.recvfrom(2048)
    currTime = time.time()
    diff = currTime - baseTime
    (seg, dataByte) = getSegmentAndData(raw)
    recordSegment(diff, seg.header, 'rcv')
    return (seg, dataByte)

# first step of 4-segment terminate
# happen once the file has been successfully transmitted
def terminateFINSend():
    #seqNum is global
    header = initHeader(0, NextSeqNum, ack, checkSum, FIN)
    segment = initSegment(header, 0)
    # convert segment to bytes send to the receiver
    packed = convertSegToByte(segment)
    s.sendto(packed, addr)
    # record to the log file
    currTime = time.time()
    diff = currTime - baseTime
    recordSegment(diff, header, 'snd')

# used for send ACK to receiver
def terminateACKSend():
    header = initHeader(0, NextSeqNum + 1, ack, checkSum, ACK)
    segment = initSegment(header, 0)
    # convert segment to bytes send to the receiver
    packed = convertSegToByte(segment)
    s.sendto(packed, addr)
    # record to the log file
    currTime = time.time()
    diff = currTime - baseTime
    recordSegment(diff, header, 'snd')

def getDataChunk(index):
    # when data size smaller than MSS
    if index + MSS >= filesize:
        dataByte = fileBytes[index:]
    else:
        dataByte = fileBytes[index:index+MSS]
    return dataByte


# final step of 4-segment terminate
# def terminateSend():
class PLD(object):
    def __init__(self, pDrop, pDuplicate, pCorrupt, pOrder, pDelay):
        self.pDrop = pDrop
        self.pDuplicate = pDuplicate
        self.pCorrupt = pCorrupt
        self.pOrder = pOrder
        self.pDelay = pDelay
        self.seg_PLD = 0
        self.seg_dropped = 0
        self.seg_corrupted = 0
        self.seg_reordered = 0
        self.seg_duplicated = 0
        self.seg_delayed = 0
        self.currReOrder = 0
        # doesn't have any segment waited for send
        self.savedSeg = None

    def make_decision(self, pConduct, seed):
        #genrate random number betwwen 0 and 1
        randomN = random.random()
        if randomN < pConduct:
            #drop the segment
            return True
        else:
            return False

    # drop the segment
    def dropSegment(self, segment):
        currTime = time.time()
        diff = currTime - baseTime
        recordSegment(diff, segment.header, "drop")
        self.seg_dropped += 1

    # send the segment to twice to UDP
    def duplicateSegment(self, segment):
        # first time
        s.sendto(segment, addr)
        currTime = time.time()
        (seg, dataByte) = getSegmentAndData(segment)
        diff = currTime - baseTime
        recordSegment(diff, seg.header, "snd")

        # second time
        s.sendto(segment, addr)
        currTime = time.time()
        diff = currTime - baseTime
        (seg, dataByte) = getSegmentAndData(segment)
        recordSegment(diff, seg.header, "snd/dup")
        self.seg_duplicated += 1

    # create bit errors within packets and forword it to UDP
    def corruptSegment(self, seg, dataByte):
        dataByte = corrupt_data(dataByte)
        segment = createSegmentByte(seg, dataByte)
        s.sendto(segment, addr)
        currTime = time.time()
        diff = currTime - baseTime
        recordSegment(diff, seg.header, "snd/corr")
        self.seg_corrupted += 1

    # saved the current segment to savedSeg and waiting for forwarding
    # until the maxOrder segment forwarding, forward the saved segment
    def reOrderSegment(self, segment):
        if self.savedSeg == None:
            self.savedSeg = segment
            print ("reorder")
        # if there already have segment wait for forwarding, send it immediately
        else:
            self.sendingSegment(segment)
            self.currReOrder += 1
            print (self.currReOrder)

    # send this segment between 0 to maxDelay milliseconds
    # TODO: what happen if it's delay, if it received 3 ACK of this one, fast RXT?
    def delaySegment(self, segment):
        global lastByteAck
        delay = randint(0, maxDelay)
        # send this after delay
        timer = Timer(delay/1000, self.delaySend, [segment])
        timer.start()

    def delaySend(self, segment):
        currTime = time.time()
        diff = currTime - baseTime
        # what happen if this socket is already closed???
        global socketCLOSE
        if socketCLOSE == False:
            s.sendto(segment, addr)
            self.seg_delayed += 1
            # get the segment header which delayed send
            (seg, dataByte) = getSegmentAndData(segment)
            recordSegment(diff, seg.header, "snd/delay")

    # not drop, duplicated, corrupted, re-ordered or delayed, forward it
    def sendingSegment(self, segment):
        s.sendto(segment, addr)
        currTime = time.time()
        diff = currTime - baseTime
        (seg, dataByte) = getSegmentAndData(segment)
        recordSegment(diff, seg.header, "snd")

    def sendingSavedSegment(self):
        s.sendto(self.savedSeg, addr)
        (seg, data) = getSegmentAndData(self.savedSeg)
        currTime = time.time()
        diff = currTime - baseTime
        recordSegment(diff, seg.header, "snd/rord")
        self.seg_reordered += 1

    def fastRXT(self, segment):
        s.sendto(segment, addr)
        (seg, data) = getSegmentAndData(segment)
        currTime = time.time()
        diff = currTime - baseTime
        recordSegment(diff, seg.header, "snd/RXT")
        self.seg_PLD += 1

    def forwardingSegment(self, segHeader, payload):
        global seed, currTime
        self.seg_PLD += 1

        #---------------------------
        # DEBUG
        print (self.currReOrder)
        if self.savedSeg != None:
            (seg, data) = getSegmentAndData(self.savedSeg)
            print ("savedSegment: " + str(seg.header.seq_num))
        else:
            print ("none reorder yet")
        #---------------------------
        # check if can resend the saved reordered segment
        if self.currReOrder == maxOrder and maxOrder != 0:
            self.sendingSavedSegment()
            self.savedSeg = None
            # clean the number of current order
            self.currReOrder = 0

        # drop the segment
        elif self.make_decision(self.pDrop, seed) == True:
            print ("drop")
            self.dropSegment(segHeader)
            if self.savedSeg != None:
                self.currReOrder += 1

        # duplicate the segment
        elif self.make_decision(self.pDuplicate, seed) == True:
            # duplicate the segment
            segment = createSegmentByte(segHeader, payload)
            self.duplicateSegment(segment)
            if self.savedSeg != None:
                self.currReOrder += 1

        # corrupt the segment
        elif self.make_decision(self.pCorrupt, seed) == True:
            # intoduce 1 bit error then send it to UDP socket
            self.corruptSegment(segHeader, payload)
            if self.savedSeg != None:
                self.currReOrder += 1

        elif self.make_decision(self.pOrder, seed) == True:
            # save this to saved segment
            segment = createSegmentByte(segHeader, dataByte)
            if self.savedSeg == None:
                self.savedSeg = segment
            # if there already have segment wait for forwarding, send it immediately
            else:
                self.sendingSegment(segment)
                self.currReOrder += 1

        elif self.make_decision(self.pDelay, seed) == True:
            segment = createSegmentByte(segHeader, dataByte)
            self.delaySegment(segment)
            if self.savedSeg != None:
                self.currReOrder += 1

        # send to the UDP socket
        else:
            # send to the UDP socket
            segment = createSegmentByte(segHeader, dataByte)
            self.sendingSegment(segment)
            if self.savedSeg != None:
                self.currReOrder += 1
        currTime = time.time()

class SenderTimer(object):
    def __init__(self):
        # calculate EstimatedRTT, initial = 500 milliseconds
        self.estimatedRTT = 500
        # calculate DevRTT, initial = 250 millisecond.
        self.devRTT = 250
        self.timeoutInterval = 500 + gamma * 250;
        # if haven't start the timer yet, the timer will be None
        self.timer = None

    def cal_timeoutInterval(self, sampleRTT):
        if sampleRTT > 0:
            # sampleRTT here is in s, change it to millisecond ms
            estimatedRTT = 0.875 * self.estimatedRTT + 0.125 * sampleRTT * 1000
            devRTT = 0.75 * self.devRTT + 0.25 * abs(sampleRTT * 1000 - self.estimatedRTT)
            # calculate TimeoutInterval = EstimatedRTT + 4 * DevRTT
            self.timeoutInterval = estimatedRTT + gamma * devRTT
        return self.timeoutInterval

    def startTimer(self):
        global seg_trans, seg_RXT
        print ("start timing")
        self.timer = Timer(self.timeoutInterval/1000, self.timeout)
        self.timer.start()
        return self.timer

    def timeout(self):
        global lastByteAck, seg_trans, seg_RXT, sampleRTT, sndTime
        # resend the lastByteAck packet
        dataByte = getDataChunk(lastByteAck)
        checksum = changeByteToInt(rs232_checksum(dataByte))
        header = initHeader(len(dataByte), lastByteAck + 1, ack, checksum, DATA)
        seg = initSegment(header, len(dataByte))
        segment = createSegmentByte(seg, dataByte)
        PLDmodule.fastRXT(segment)
        seg_trans += 1
        seg_RXT += 1
        self.stopTimer()
        #sampleRTT = sampleRTT - currTime
        print ("timeout!!!")
        return True

        #return resend

    # stop the current timer, becomes timer null again
    def restart(self):
        self.timer.cancel()
        # restart a new threading
        self.timer = Timer(self.timeoutInterval/1000, self.timeout)
        self.timer.start()

    # stop the current timer
    def stopTimer(self):
        if self.timer != None:
            self.timer.cancel()
            # has time to update the state of the timer.is_active()
            time.sleep(0.001)

# seems work
# it records the information about each segment that is send and receives
def recordSegment(time, header, events):
    types = checkTypesOfPacket(header)
    length = header.length
    sequenceNumber = header.seq_num
    ack = header.ack_num
    receiver_log.write("%-20s %-10.2f %-10s %-10d %-10d %-10d\n"\
            % (events,time,types,sequenceNumber,length,ack))

# print static at the end of the log file
# works
def printStatics(PLD):
    receiver_log.write("========================================================\n")
    receiver_log.write("Size of the file (in Bytes) {}\n".format(filesize))
    receiver_log.write("Segments transmitted (including drop & RXT) {}\n".format(seg_trans))
    receiver_log.write("Number of Segments handled by PLD {}\n".format(PLD.seg_PLD))
    receiver_log.write("Number of Segments dropped {}\n".format(PLD.seg_dropped))
    receiver_log.write("Number of Segments Corrupted {}\n".format(PLD.seg_corrupted))
    receiver_log.write("Number of Segments Re-ordered {}\n".format(PLD.seg_reordered))
    receiver_log.write("Number of Segments Duplicated {}\n".format(PLD.seg_duplicated))
    receiver_log.write("Number of Segments Delayed {}\n".format(PLD.seg_delayed))
    receiver_log.write("Number of Retransmissions due to TIMEOUT {}\n".format(seg_RXT))
    receiver_log.write("Number of FAST RETRANSMISSION {}\n".format(seg_fast_RXT))
    receiver_log.write("Number of DUP ACKS received {}\n".format(dup_acks))
    receiver_log.write("========================================================\n")

def convertSegToByte(seg):
    buff = create_string_buffer(sizeof(seg))
    memmove(buff, addressof(seg), sizeof(seg))
    return buff.raw

def convertByteToSeg(seg, byte):
    memmove(addressof(seg), byte, sizeof(seg))

def changeByteToInt(dataByte):
	return int.from_bytes(dataByte, byteorder='big')

# from stack overflow
def rs232_checksum(the_bytes):
    return b'%02X' % (sum(the_bytes) & 0xFF)

def createSegmentByte(segment, dataByte):
    segByte = convertSegToByte(segment)
    return b''.join([segByte, dataByte])

def getSegmentAndData (segmentByte):
    seg = Segment()
    segByte = segmentByte[0:sizeof(seg) - 1]
    convertByteToSeg(seg, segByte)
    dataByte = segmentByte[sizeof(seg):]
    return (seg, dataByte)

def corrupt_data(dataByte):
	value = changeByteToInt(dataByte)
	value = (value & 0x1fffff) >> 1
	corr_data = value.to_bytes(len(dataByte), byteorder='big')
	return corr_data

rcvACK = {}

# when segment doesn't contain any payload
checkSum = b'00'
checkSum = changeByteToInt(checkSum)
# ========================================================
# start timer, three way handshack (SYN, SYN + ACK, ACK)
# ACK send by the sender should not contain any payload
# ========================================================
baseTime = time.time()
handShackInitSend()
seg_trans += 1
rcvSeg = handShackRcv()
handShackSend (rcvSeg.ack_num)
seg_trans += 1

# set the initial sequence Number
seqNum = 1
ack = 1

# ========================================================
# start file transferring
# ========================================================
f=open(filename, "rb")
# read the file in one go, dataByte = fileBytes[index: index + MSS]
fileBytes = f.read()

# load the PLD moudle, determine if the package should drop or not
PLDmodule = PLD(pDrop, pDuplicate, pCorrupt, pOrder, pDelay)

NextSeqNum = seqNum
sendBase = seqNum

lastByteSent = 0
lastByteAck = 0
STPtimer = SenderTimer()

global sampleRTT, sndTime
sampleRTT = 0

receivedACK = {}
currTime = 0

socketCLOSE = False
sndTime = time.time()

while True:
    if lastByteAck == filesize:
        # file transmit finished, stop the timer
        STPtimer.stopTimer()
        break
    if (lastByteSent - lastByteAck < MWS and lastByteSent - lastByteAck >= 0 and lastByteSent != filesize):
        # or (PLDmodule.savedSeg != None and PLDmodule.currReOrder <= maxOrder)
        # --- genetate the segment ready to send to UDP ---
        dataByte = getDataChunk(lastByteSent)
        checksum = changeByteToInt(rs232_checksum(dataByte))
        header = initHeader(len(dataByte), lastByteSent + 1, ack, checksum, DATA)
        seg = initSegment(header, len(dataByte))

        # check if the timer start yet
        # if the timer haven't start yet
        if STPtimer.timer == None:
            STPtimer.cal_timeoutInterval(sampleRTT)
            currTimer = STPtimer.startTimer()

        # ------ go to the PLD modole------
        lastByteSent += len(dataByte)
        NextSeqNum += len(dataByte)
        #currTime = time.time()
        seg_trans += 1
        # the time send the segment
        PLDmodule.forwardingSegment(seg, dataByte)
        # print ("Im here")
    elif STPtimer.timer != None and STPtimer.timer.is_alive() == False:
        print ("means timeout")
        # STPtimer.cal_timeoutInterval(sampleRTT)
        currTimer = STPtimer.startTimer()
        continue
    else:
        (raw, addr) = s.recvfrom(2048)
        rcv_time = time.time()
        (seg, ACK_dataByte) = getSegmentAndData(raw)
        rcv_ack = seg.header.ack_num
        length = seg.header.length
        types = seg.header.type
        diff = rcv_time - baseTime

        # add received to the dictionary
        if rcv_ack > lastByteAck:
            NextSeqNum  = rcv_ack
            lastByteAck = rcv_ack - 1
            # update the new sampleRTT
            sampleRTT = rcv_time - sndTime
            print ("sndTime: " + str(currTime))
            print ("timeout" + str(STPtimer.timeoutInterval/1000))
            print ("SampleRTT " + str(sampleRTT))
            # stop the current timer
            sndTime = time.time()
            STPtimer.stopTimer()

        # there has any not yet acked segment
        if lastByteSent > lastByteAck:
            # recalculate the time interval
            STPtimer.stopTimer()
            STPtimer.cal_timeoutInterval(sampleRTT)
            # start the timer again
            sndTime = time.time()
            currTimer = STPtimer.startTimer()

        if rcv_ack in receivedACK:
            receivedACK[rcv_ack] += 1
            dup_acks += 1
            recordSegment(diff, seg.header, 'rcv/DA')

            # include one is already received
            if receivedACK[rcv_ack] == 4:
                dataByte = getDataChunk(rcv_ack - 1)
                checksum = changeByteToInt(rs232_checksum(dataByte))
                header = initHeader(len(dataByte), rcv_ack, ack, checksum, DATA)
                seg = initSegment(header, len(dataByte))
                segment = createSegmentByte(seg, dataByte)
                PLDmodule.fastRXT(segment)
                seg_trans += 1
                seg_fast_RXT += 1
        else:
            receivedACK[rcv_ack] = 1
            recordSegment(diff, seg.header, 'rcv')
            print ("got here")



# ====================================================================
# four-segement (FIN, ACK, FIN, ACK) conncection terminate
# sender will initiate the connection close once the entire file
# been successfully transmitted
# ====================================================================
terminateFINSend()
seg_trans += 1
# waiting for the ACK and FIN from the receiver
recvSegment()
recvSegment()
seqNum += 1
ack += 1
terminateACKSend()
seg_trans += 1

# ============================
# FINISH
# close the file and socket
# ============================
printStatics(PLDmodule)
f.close()
s.close()
socketCLOSE = True
print ("Finish sending file")
