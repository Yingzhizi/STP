# STP
Simple Transfer Protocol
a reliable transport protocol implemented over the UDP protocol which has a basic functions of TCP protocol which can encapsulate PDF file and transfer it reliable. It includes three-way handshake for connection establishment, four-segment connection termination, timer, MSS (Maximum Segment Size), MWS (Maximum Window Size). Handle the packet drop, duplicate packets, packet error handling, timeout and delay packet handling, receiver side can also detect duplicated and corrupted packet. 

# Require Skills
* Detailed understanding of how reliable transport protocols such as TCP function.
* Socket programming for UDP transport protocol.
* Protocol and message design.

# List of features provided by the Sender and Receiver
* A three-way handshake (SYN, SYN+ACK, ACK) for the connection establishment. The ACK sent by the sender to conclude the three-way handshake won't contain any payload.
* A four-segment (FIN, ACK, FIN, ACK) connection termination. The Sender will initiate the connection close once the entire file has been successfully transmitted.
* Sender will maintain a single-timer for timeout operation. 
* The STP protocol includes the simplified TCP sender and fast retransmit.
* STP is a byte-stream oriented protocol. Sequence number and acknowledgement number fields are included in the STP header for each segment. The meaning of sequence number and acknowledgment number are the same as in TCP.
* MSS (Maximum segment size) is the maximum number of bytes of data that your STP segment can
contain. In other words, MSS counts data ONLY and does NOT include header. Sender will be able to deal with different values of MSS. The value of MSS will be supplied to Sender as an input argument.
* Maximum Window Size (MWS). MWS is the maximum number of un-acknowledged bytes that the Sender can have at any time. MWS counts ONLY data. Header length should NOT be counted as part of MWS.

# Sender.py
The <b>Sender</b> accepts the following fourteen (14) arguments:
1. <b>receiver_host_ip</b>: The IP address of the host machine on which the Receiver is running.
2. <b>receiver_port</b>: The port number on which Receiver is expecting to receive packets from the
sender.
3. <b>file.pdf</b>: The name of the pdf file that has to be transferred from sender to receiver using your STP .
4. <b>MWS</b>: The maximum window size used by your STP protocol in bytes. 
5. <b>MSS</b>: Maximum Segment Size which is the maximum amount of data (in bytes) carried in each STP segment. 
6. <b>gamma</b>: This value is used for calculation of timeout value. See Section 7 of the specification for details.
The following 8 arguments are used exclusively by the PLD module:
7. <b>pDrop</b>: The probability that a STP data segment which is ready to be transmitted will be dropped. This value must be between 0 and 1. For example if pDrop = 0.5, it means that 50% of the transmitted segments are dropped by the PLD.
8. <b>pDuplicate</b>: The probability that a data segment which is not dropped will be duplicated. This value must also be between 0 and 1.
9. <b>pCorrupt</b>: The probability that a data segment which is not dropped/duplicated will be corrupted. This value must also be between 0 and 1.
10. <b>pOrder</b>: The probability that a data segment which is not dropped, duplicated and corrupted will be re-ordered. This value must also be between 0 and 1.
11. <b>maxOrder</b>: The maximum number of packets a particular packet is held back for re-ordering purpose. This value must be between 1 and 6.
12. <b>pDelay</b>: The probability that a data segment which is not dropped, duplicated, corrupted or re-ordered will be delayed. This value must also be between 0 and 1.
13. <b>maxDelay</b>: The maximum delay (in milliseconds) experienced by those data segments that are delayed.
14. <b>seed</b>: The seed for your random number generator. The use of seed will be explained in Section 4.5.2 of the specification.

The Sender should be initiated as follows:
```
python sender.py receiver_host_ip receiver_port file.pdf MWS MSS gamma pDrop pDuplicate pCorrupt pOrder maxOrder pDelay maxDelay seed
```
Note that, you should first start the Receiver before initiating the Sender.

# Recevier.py
The <b>Receiver</b> should accept the following two arguments:
1. <b>receiver_port</b>: the port number on which the Receiver will open a UDP socket for receiving datagrams from the Sender.
2. </b>file_r.pdf</b>: the name of the pdf file into which the data sent by the sender should be stored (this is a copy of the file that is being transferred from sender to receiver).

The Receiver should be initiated as follows:
```
python receiver.py receiver_port file_r.pdf
```
# The PLD Module
The PLD module was implemented as part of your Sender program. The function of the PLD is to emulate some of the events that can occur in the Internet such as loss of packets, packet corruption, packet re-ordering and delays. Even though theoretically UDP packets will get lost and delayed on their own, in the test environment these events will occur very rarely. Further to test the reliability of your STP protocol we would like to be able to control the percentage of packets being lost, corrupted, re-ordered and delayed. The PLD module should take care of the following events;
* Drop packets
* Duplicate packets
* Create bit errors within packets (a single bit error)
* Transmits out of order packets
* Delays packets

# logfile
* The sender will maintain a log file titled <b>Sender_log.txt</b> where it records the information about each segment that it sends and receives. Information about dropped, delayed, corrupted segments should also be included
* The Receiver will also maintain a log file titled <b>Receiver_log.txt</b> where it records the information about each segment that it sends and receives.
 

