import threading
import time
import os
import logging

class ShutdownTimer :
    # the default timeout in minutes
    DEFAULT_TIMEOUT = 10.0

    # used internally to store the next timeout value
    timeout = time.monotonic() + DEFAULT_TIMEOUT * 60.0

    # the thread that is checking if the timeout is reached
    thread = None

    # set to true when the timer runs; if set to false, the timer will stop
    running = False

    # callback function that determines if the system is active or not
    # if this indicates activity, the shutdown timeout is pushed back automatically
    activity_check = None

    # push the imminent shutdown back to given number of minutes from now
    def push_timeout ( self, minutes = DEFAULT_TIMEOUT ) :
        self.timeout = time.monotonic() + minutes * 60.0

    # internal thread that checks if the timeout is reached once each second
    def __check_shutdown ( self ) :
        logging.info( 'shutdown timer started' )
        CHECK_INTERVAL = 5.0 # seconds
        next_check = time.monotonic() + CHECK_INTERVAL

        while self.running :
            now = time.monotonic()

            if now < next_check :
                time.sleep( 0.1 ) # seconds
                continue

            logging.debug( 'shutdown in %f minutes', ( self.timeout - now ) / 60.0 )
            next_check = now + CHECK_INTERVAL

            if self.activity_check() == True :
                self.push_timeout()
            else:
                if now > self.timeout :
                    logging.info( 'shutdown timeout reached' )
                    os.system( 'sudo shutdown -h now' )
                    self.running = False

        logging.info( 'shutdown timer stopped' )

    # start the timer
    def start ( self, activity_check ) :
        self.thread = threading.Thread( target = self.__check_shutdown )
        self.running = True
        self.activity_check = activity_check
        self.push_timeout()
        self.thread.start()

    # stop the timer and wait until it is stopped
    def stop ( self ) :
        self.running = False
        self.thread.join()

    # wait until the timer is stopped
    def join ( self ) :
        self.thread.join()

def __dummy_activity_check () :
    logging.info( 'dummy activity check' )
    return False

if __name__ == '__main__' :
    logging.root.setLevel( logging.INFO )
    st = ShutdownTimer()
    st.start( __dummy_activity_check )
    st.join()
