import sys
import time
from socket import *
from Segment import *
from Header import *
import ctypes
import struct
import hashlib

#TODO: fix the increment for the not ordered segment received
receiver_port = int(sys.argv[1])
file_r = str(sys.argv[2])

# at initiate, ack is 1
ack = 1
seq_num = 1

# ---counter, used for print out the static---
data_received = 0
seg_received = 0
Dseg_received = 0
Dseg_with_biterror = 0
Dseg_duplicated = 0
dup_acks = 0

# set the flag as the an interger
SYN = 1
ACK = 2
FIN = 4
DATA = 8

# =====================
# open socket
# =====================
# receiver host is 0.0.0.0 here
host = "0.0.0.0"
server_socket = socket(AF_INET, SOCK_DGRAM)
server_socket.bind((host, receiver_port))
print ("Receiver is open...")
addr = (host, receiver_port)

# ready to write to the receiver_log.txt
receiver_log = open ("Receiver_log.txt", "a")

def convertSegToByte(seg):
    buff = create_string_buffer(sizeof(seg))
    memmove(buff, addressof(seg), sizeof(seg))
    return buff.raw

# convert byte string to structure segment
# extract the STP packet from the arriving UDP datagrams
def convertByteToSeg(seg, byte):
    memmove(addressof(seg), byte, sizeof(seg))

# convert bytes to integer
def changeByteToInt(dataByte):
	return int.from_bytes(dataByte, byteorder='big')

# calculate the checksum of the dataByte
# from stack overflow
def rs232_checksum(the_bytes):
    return b'%02X' % (sum(the_bytes) & 0xFF)

def createSegmentByte(segment, dataByte):
    segByte = convertSegToByte(segment)
    return b''.join([segByte, dataByte])

# extract the data from the STP packet
def getSegmentAndData (segmentByte):
    seg = Segment()
    segByte = segmentByte[0:sizeof(seg) - 1]
    convertByteToSeg(seg, segByte)
    dataByte = segmentByte[sizeof(seg):]
    return (seg, dataByte)


#proper TCP header has (length, dest_port, sequence_number, ACK)
#flags, length, seqnum, ack_num, rwnd)
#sendingHeader = InitHeaderBySeg((FIN|ACK),0,1,ack_num,0)
def handShackSend(sender):
    header = initHeader(0, 0, ack, checkSum, SYN+ACK)
    #create a segment without any data
    segment = initSegment(header, header.length)
    packed = convertSegToByte(segment)
    server_socket.sendto(packed, sender)
    currTime = time.time()
    diff = currTime - baseTime
    recordSegment(diff, header, 'snd')

def handShackRcv():
    global baseTime
    raw, addr = server_socket.recvfrom(2048)
    currTime = time.time()
    if baseTime == 0:
        diff = currTime - currTime
    else:
        diff = currTime - baseTime
    (seg, dataByte) = getSegmentAndData(raw)
    # write to the log file
    recordSegment(diff, seg.header, 'rcv')
    # get the UDP port the sender is using
    return addr

def sendingACK(ACK):
    currTime = time.time()
    packed = convertSegToByte(ACK)
    server_socket.sendto(packed, sender)
    diff = currTime - baseTime
    recordSegment(diff, header, 'snd')

def sendingDupACK(ACK):
    currTime = time.time()
    packed = convertSegToByte(ACK)
    server_socket.sendto(packed, sender)
    diff = currTime - baseTime
    recordSegment(diff, header, 'snd/DA')


def terminateSend():
    # ack_num is the global number
    # seqNum is always 1
    # ACK segment do not contain any data
    headerA = initHeader(0, 1, ack, checkSum, ACK)
    segmentA = initSegment(headerA, headerA.length)
    packed = convertSegToByte(segmentA)
    server_socket.sendto(packed, sender)
    t1 = time.time()
    diff1 = t1 - baseTime
    recordSegment(diff1, headerA, 'snd')

    headerF = initHeader(0, 1, ack, checkSum, FIN)
    segmentF = initSegment(headerF, headerF.length)
    packed = convertSegToByte(segmentF)
    server_socket.sendto(packed, sender)
    t2 = time.time()
    diff2 = t2 - baseTime
    recordSegment(diff2, headerF, 'snd')

# received terminate segment
def terminateRcv():
    raw, addr = server_socket.recvfrom(2048)
    currTime = time.time()
    diff = currTime - baseTime
    (seg, dataByte) = getSegmentAndData(raw)
    recordSegment(diff, seg.header, 'rcv')
    return (seg, dataByte)

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
def printStatics():
    receiver_log.write("========================================================\n")
    receiver_log.write("Amount of data received (bytes) {}\n".format(data_received))
    receiver_log.write("Total Segments Received {}\n".format(seg_received))
    receiver_log.write("Data segments received {}\n".format(Dseg_received))
    receiver_log.write("Data segments with Bit Errors {}\n".format(Dseg_with_biterror))
    receiver_log.write("Duplicate data segments received {}\n".format(Dseg_duplicated))
    receiver_log.write("Duplicate ACKs sent {}\n".format(dup_acks))
    receiver_log.write("========================================================\n")

# use for sort the buff
def sortByFirst(elem):
    return elem[0].header.seq_num

# create a list sotre packet out of order
buff = []

# create a list to store the ACKed packet
received = []
# create a dic to store the number of seqnum of each segment received
dupAck = {}

# when segment doesn't contain any payload
checkSum = b'00'
checkSum = changeByteToInt(checkSum)

# ========================================================
# start timer, three way handshack (SYN, SYN + ACK, ACK)
# ACK send by the sender should not contain any payload
# ========================================================
baseTime = 0
sender = handShackRcv()
baseTime = time.time()
seg_received += 1
handShackSend(sender)
handShackRcv()
seg_received += 1

# after 3-way handshack, create a new file file_r.pdf
f = open(file_r, 'wb')

# ========================================================
# start downloading file
# ========================================================
while True:
    print ("Start receiving file...")
    (raw, addr) = server_socket.recvfrom(2048)
    # get the diff of the time
    currTime = time.time()
    diff = currTime - baseTime

    # extract the segment and data carried from the receievd bytes
    (seg, dataByte) = getSegmentAndData(raw)
    seg_received += 1

    # get the sequence number, the data length
    # and the types of the received segment
    rcv_seq = seg.header.seq_num
    length = seg.header.length
    types = seg.header.type
    checksum = seg.header.checksum

    # increment the amount of data received
    data_received += len(dataByte)
    # received the FIN flag segment, start teardown
    # this part works
    if types == FIN:
        ack = rcv_seq + 1
        recordSegment(diff, seg.header, 'rcv')
        # sed the ACk and FIN flags segment to the sender
        terminateSend()
        break
    # data segment received increse 1
    Dseg_received += 1

    # received a segment with bit error rcv/corr
    if checksum != changeByteToInt(rs232_checksum(dataByte)):
        Dseg_with_biterror += 1
        recordSegment(diff, seg.header, 'rcv/corr')
    else:
        # received segment is in order
        if rcv_seq == ack:
            print (ack)
            print (rcv_seq)
            recordSegment(diff, seg.header, 'rcv')
            # need to go to check the buffer to determine the ack need to send
            # if the buffer is empty
            if len(buff) == 0:
                # write the data to the file
                #print (len(buff))
                f.write(dataByte)
                print ("seq:" + str(seg.header.seq_num) + ", length:" + str(seg.header.length))
                received.append(seg.header.seq_num)
                # get the new ack number
                ack = rcv_seq + length
            else:
                # write the segment in the buffer to the file if they are in order
                ack = rcv_seq + length
                f.write(dataByte)
                print ("seq:" + str(seg.header.seq_num) + ", length:" + str(seg.header.length))

                while (len(buff) !=  0 and buff[0][0].header.seq_num == ack):
                    seg = buff[0][0]
                    dataByte = buff[0][1]
                    f.write(dataByte)
                    print ("seq:" + str(seg.header.seq_num) + ", length:" + str(seg.header.length))
                    # add the sequence number to the received list
                    received.append(seg.header.seq_num)
                    # pop this segment from the buffer
                    buff.pop(0)
                    print (len(buff))
                    # get the new ack number
                    ack = ack + seg.header.length
            # send ACK to sender which new ack number
            header = initHeader(0, seq_num, ack, checkSum, ACK)
            ACKseg = initSegment(header, header.length)
            sendingACK(ACKseg)

        # check if the segment is out of order
        # if the segment received out of order, add it to buff
        # send the ACK as event of snd/DA, ack_num keeps the same
        elif rcv_seq > ack:
            print ("out of order")
            recordSegment(diff, seg.header, 'rcv')
            # check if there has any duplicated segement been received
            # if this segment has been write to the file, discard it, do thing
            if rcv_seq in received:
                Dseg_duplicated += 1
            else:
                # add it to the buffer
                buff.append((seg, dataByte))
                # sort the buffer
                buff.sort(key=sortByFirst)

            # send the ACK to the sender
            # check how many times each ack been send
            if ack in dupAck:
                dupAck[ack] += 1
            else:
                dupAck[ack] = 1

            # sending the same ack up to 3 times
            if dupAck[ack] <= 3:
                header = initHeader(0, seq_num, ack, checkSum, ACK)
                ACKseg = initSegment(header, header.length)
                sendingDupACK(ACKseg)
                dup_acks += 1
        else:
            if rcv_seq in received:
                Dseg_duplicated += 1
                print ("here")
                recordSegment(diff, seg.header, 'rcv')


# waiting the last segment been received
# the last step of the 4-segment teardown
while True:
    (seg, dataByte) = terminateRcv()
    seg_received += 1
    if seg.header.type == ACK:
        break;

# print the static result to the log file
printStatics()

# ============================
# FINISH
# close the file and socket
# ============================
f.close()
server_socket.close()
print ("Finish")
