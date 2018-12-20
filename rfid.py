import sys
import evdev
import logging
import threading

def print_callback ( id ) :
    logging.info( id )

class RfidReader :
    # set to true when the reader thread starts; if set to false, the reader will stop
    running = False

    # the thread that is reading characters from the RFID reader
    thread = None

    # the callback that is called, when an ID has been read
    callback = None

    # stop the reader and wait until it is stopped
    def stop ( self ) :
        self.running = False

        if self.thread :
            self.thread.join()

    # start the reader
    # callback will be called with ID as argument, when an ID has been read
    def start ( self, callback ) :
        self.thread = threading.Thread( target = self.__loop )
        self.running = True
        self.callback = callback
        self.thread.start()

    # wait until the reader has been stopped
    def join ( self ) :
        if self.thread :
            self.thread.join()

    def __loop ( self ) :
        try :
            device = evdev.InputDevice( '/dev/input/event0' )

            logging.info( device )

            id = ''
            logging.info( "RFID event loop started" )

            while self.running :
                event = device.read_one()

                while event != None :
                    if event.type == evdev.ecodes.EV_KEY :
                        key_event = evdev.events.KeyEvent( event )
                        if key_event.keystate == evdev.events.KeyEvent.key_up :
                            if key_event.keycode == 'KEY_ENTER' :
                                self.callback( id )
                                id = ''
                            else :
                                id = id + key_event.keycode.split( '_' )[1]

                    event = device.read_one()

            logging.info( "RFID event loop stopped" )
        except KeyboardInterrupt :
            raise
        except evdev.EvdevError as e:
            self.running = False
            logging.info( "ERROR: could not open RFID reader %s", e.msg )

if __name__ == "__main__" :
    logging.root.setLevel( logging.INFO )
    rfid_reader = RfidReader()
    rfid_reader.start( print_callback )
    rfid_reader.join()
