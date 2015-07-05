Frame-by-frame serial communication
###################################

:date: 2014-02-26
:tags: Arduino, Serial, Hackerspace
:status: published

With the `hackerspace open day <http://frack.nl/wiki/Hackerspace_Open_Dag_2014>`_ coming up in a bit over a month, this is a perfect time to prepare some small projects. Something that can be completed in a few evenings, and is reasonably accessible to curious newcomers. A fellow hacker ordered a few `nRF24 wireless transceivers <http://www.nordicsemi.com/eng/Products/2.4GHz-RF/nRF24L01>`_ a while ago, and now is as good a time as any to *do* something with them.


A little about the nRF24
========================

The nRF24 is a 2.4GHz wireless transceiver that is available from a large amount of resellers, from about 2 USD. While they operate in the same ISM band as WiFi, they are **not** Ethernet devices. There's at least one `well documented library <http://maniacbug.github.io/RF24/>`_ around that provides an interface to them for Arduino, which will provide a starting point for our boondoggle.

The `30 meter range <https://hallard.me/nrf24l01-real-life-range-test/>`_ on these I think is pretty reasonable, though it's nowhere near the 100m that most vendors claim. For those cases where you need the distance coverage, there are models around that will allow for an antenna to be connected. With a simple antenna, distances over 100m in the open field have been reported (see the references article).

.. PELICAN_END_SUMMARY


The project idea
================

There's not much of a *plan* yet on what the project should be, but I'm amused by something that came to me last night: using the nRF in an *Arduino-based serial-to-internet contraption*. That might be a bit too terse, so allow me to explain the way to connect to the internet with this setup:

#. Starting on the client machine, a simple Python application listens on a socket...
#. ...which provides an HTTP proxy relaying incoming data to the serial port;
#. An Arduino receives the serial data and retransmits it over the nRF;
#. A second Arduino receives the data from the nRF and retransmits to its serial...
#. ...where a second computer listens and sends the data to an actual HTTP proxy;
#. The remote server eventually replies and data goes back the way it came.

Is this a practical way of browsing the web? Probably not, and it will certainly provide you with a very slow connection. Does it make for a fun and interesting project? Probably, hopefully not in a (too) frustrating way.


I mentioned frames
==================

One of the things that should be immediately obvious is that HTTP requests can be quite large, not for modern computers, but definitely so for microcontrollers. An Arduino powered by an `ATmega328p <http://www.atmel.com/devices/atmega328.aspx>`_ has two kilobytes of SRAM. An HTTP request with a few cookies and perhaps an included form (let's not talk about file uploads) is easily larger than that. This means that trying to buffer a full request is not going to work. With my fellow hacker having left earlier, taking the wireless chips with him, I set out to solve the buffering problem.

The solution is fairly easy actually, mostly because our Arduino doesn't actually have to *process* the information, we're only using it as a conduit. This is still untested for the intended purpose, but it works for now to frame a large incoming stream into chunks of definite sizes, using only a marginal amount of memory on the Arduino:

.. code-block:: c++

    const byte frameSize = 16;
    byte frame[frameSize];

    byte readMessage(byte messageBuffer[]) {
      // Read up to one frame of data from serial
      byte serialInput, messageLength = 0;
      while (messageLength < frameSize
             && readByte(serialInput)
             && serialInput != '\n') {
        *messageBuffer++ = serialInput;
        messageLength++;
      }
      return messageLength;
    }

    bool readByte(byte &receivedByte) {
      // Read a single byte from serial or time out
      // Write data in referenced byte; return success state
      const int readTimeout = 20;
      long startTime = millis();
      while (!Serial.available())
        if ((millis() - startTime) > readTimeout)
          return false;
      receivedByte = Serial.read();
      return true;
    }

The third condition for the :code:`while` loop will be taken out for the work in the proxy. For now the sketch (GitHub: `FramedCommunicator <https://github.com/edelooff/FramedCommunicator>`_) prints the frame and its length back over the serial connection, printing line-breaks as they are received would mess up the text display.
