#!/usr/bin/python3
# import Raspberry Pi GPIO library
import RPi.GPIO as GPIO
import time
import vlc
import sys
import time
import daemon
import signal
import lockfile
import rfid as rfid
from enum import IntEnum

PID_FILE = '/home/pi/annibox/annibox.pid'
STDOUT_FILE = '/home/pi/annibox/annibox.log'
STDERR_FILE = '/home/pi/annibox/annibox_err.log'

VOLUME_LIMIT = 200
VOLUME_STEP = 10
VOLUME_DEFAULT = 100
BOUNCE_TIME = 200

class Pin ( IntEnum ) :
    GREEN = 19
    RED = 24
    BLUE = 23
    YELLOW = 21
    LED = 26

class Button ( IntEnum ) :
    PLAY = Pin.GREEN
    PAUSE = Pin.YELLOW
    VOL_UP = Pin.RED
    VOL_DOWN = Pin.BLUE

anniBox = None

class AnniBox :
    def __init__ ( self ) :
        self.vlcInstance = vlc.Instance( "--aout alsa" )
        self.player = self.vlcInstance.media_player_new()
        self.player.audio_output_device_set( "alsa", "hw0:0" )
        self.player.audio_set_volume( VOLUME_DEFAULT )
        self.volume = VOLUME_DEFAULT

        # ignore warnings for now
        GPIO.setwarnings( False )

        # Use physical pin numbering
        GPIO.setmode( GPIO.BOARD )

        # enable the LED
        GPIO.setup( Pin.LED, GPIO.OUT )
        GPIO.output( Pin.LED, GPIO.HIGH )

        # set the pins to be an input pin and set initial value to be pulled low (off)
        GPIO.setup( Button.PLAY, GPIO.IN, pull_up_down = GPIO.PUD_DOWN )
        GPIO.setup( Button.PAUSE, GPIO.IN, pull_up_down = GPIO.PUD_DOWN )
        GPIO.setup( Button.VOL_UP, GPIO.IN, pull_up_down = GPIO.PUD_DOWN )
        GPIO.setup( Button.VOL_DOWN, GPIO.IN, pull_up_down = GPIO.PUD_DOWN )

        # setup event on pin rising edge
        GPIO.add_event_detect( Button.PLAY, GPIO.RISING, callback = play, bouncetime = BOUNCE_TIME )
        GPIO.add_event_detect( Button.PAUSE, GPIO.RISING, callback = pause, bouncetime = BOUNCE_TIME )
        GPIO.add_event_detect( Button.VOL_UP, GPIO.RISING, callback = volume_up, bouncetime = BOUNCE_TIME )
        GPIO.add_event_detect( Button.VOL_DOWN, GPIO.RISING, callback = volume_down, bouncetime = BOUNCE_TIME )

    # add callback functions for each button press
    def play ( self ) :
        print( "play", flush = True )
        sys.stdout.flush()
        self.player.set_media( self.vlcInstance.media_new( "test.mp3" ) )
        self.player.play()

    def pause ( self ) :
        print( "pause", flush = True )
        self.player.pause()

    def volume_up ( self ) :
        if ( self.volume < VOLUME_LIMIT ) :
            self.volume += VOLUME_STEP
            print( "set volume " + str( self.volume ), flush = True )
            self.player.audio_set_volume( self.volume )

    def volume_down ( self ) :
        if ( self.volume > 0 ) :
            self.volume -= VOLUME_STEP
            print( "set volume " + str( self.volume ), flush = True )
            self.player.audio_set_volume( self.volume )

def play ( channel ) :
    anniBox.play()

def pause ( channel ) :
    anniBox.pause()

def volume_up ( channel ) :
    anniBox.volume_up()

def volume_down ( channel ) :
    anniBox.volume_down()

def rfid_trigger ( id ) :
    print( 'id ' + id + ' triggered', flush = True )

def shutdown( signum, frame ) :
    global anniBox
    rfid.stop_rfid_loop()
    anniBox.player.stop()
    GPIO.output( Pin.LED, GPIO.LOW )
    GPIO.cleanup()
    sys.exit( 0 )

stdoutFile = open( STDOUT_FILE, 'w' )
stderrFile = open( STDERR_FILE, 'w' )

with daemon.DaemonContext(
    working_directory = "/home/pi/annibox",
    signal_map = {
        signal.SIGTERM: shutdown,
        signal.SIGTSTP: shutdown
    },
    pidfile = lockfile.FileLock( PID_FILE ),
    stdout = stdoutFile,
    stderr = stderrFile
) :
    anniBox = AnniBox()
    rfid.run_rfid_loop( rfid_trigger )