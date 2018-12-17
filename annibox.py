#!/usr/bin/python3
# import Raspberry Pi GPIO library
import RPi.GPIO as GPIO
import time
import vlc
import sys
import os
import time
import daemon
import signal
import lockfile
import rfid as rfid
from shutdown_timer import ShutdownTimer
from enum import IntEnum

PID_FILE = '/home/pi/annibox/annibox.pid'
STDOUT_FILE = '/home/pi/annibox/annibox.log'
STDERR_FILE = '/home/pi/annibox/annibox_err.log'

VOLUME_LIMIT = 200
VOLUME_STEP = 10
VOLUME_DEFAULT = 60
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

anni_box = None
shutdown_timer = None

class AnniBox :
    def __init__ ( self ) :
        self.vlc_instance = vlc.Instance( '--aout alsa' )
        self.player = self.vlc_instance.media_list_player_new()
        self.player.get_media_player().audio_output_device_set( 'alsa', 'hw0:0' )
        self.player.get_media_player().audio_set_volume( VOLUME_DEFAULT )
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
        self.player.next()
        print( 'play ' + self.player.get_media_player().get_media().get_mrl() , flush = True )

    def pause ( self ) :
        print( 'pause', flush = True )
        self.player.pause()

    def volume_up ( self ) :
        if ( self.volume < VOLUME_LIMIT ) :
            self.volume += VOLUME_STEP
            print( 'set volume ' + str( self.volume ), flush = True )
            self.player.get_media_player().audio_set_volume( self.volume )

    def volume_down ( self ) :
        if ( self.volume > 0 ) :
            self.volume -= VOLUME_STEP
            print( 'set volume ' + str( self.volume ), flush = True )
            self.player.get_media_player().audio_set_volume( self.volume )

    def play_album ( self, name ) :
        if not os.path.isdir( 'media/' + name ) :
            print( 'album ' + name + ' not found', flush = True )
            return

        files = []
        for file in os.listdir( 'media/' + name  ) :
            files.append( 'media/' + name + '/' + file )

        if not files :
            print( 'album ' + name + ' is empty', flush = True )
            return

        files.sort()
        media_list = self.vlc_instance.media_list_new( files )
        self.player.set_media_list( media_list )
        self.player.play_item_at_index( 0 )
        print( 'play ' + self.player.get_media_player().get_media().get_mrl() , flush = True )

def play ( channel ) :
    anni_box.play()

def pause ( channel ) :
    anni_box.pause()

def volume_up ( channel ) :
    anni_box.volume_up()

def volume_down ( channel ) :
    anni_box.volume_down()

def rfid_trigger ( id ) :
    print( 'id ' + id + ' triggered', flush = True )
    anni_box.play_album( id )

def activity_check () :
    is_playing = anni_box.player.is_playing()
    # print( 'activity check: ' + str( is_playing ) ,flush = True )
    return is_playing

def shutdown( signum, frame ) :
    global anni_box
    global shutdown_timer
    shutdown_timer.stop()
    rfid.stop_rfid_loop()
    anni_box.player.stop()
    GPIO.output( Pin.LED, GPIO.LOW )
    GPIO.cleanup()
    sys.exit( 0 )

stdoutFile = open( STDOUT_FILE, 'w' )
stderrFile = open( STDERR_FILE, 'w' )

with daemon.DaemonContext(
    working_directory = '/home/pi/annibox',
    signal_map = {
        signal.SIGTERM: shutdown,
        signal.SIGTSTP: shutdown
    },
    pidfile = lockfile.FileLock( PID_FILE ),
    stdout = stdoutFile,
    stderr = stderrFile
) :
    anni_box = AnniBox()
    shutdown_timer = ShutdownTimer()
    shutdown_timer.start( activity_check )
    rfid.run_rfid_loop( rfid_trigger )