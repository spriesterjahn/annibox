#!/usr/bin/python3
import RPi.GPIO as GPIO
import time
import vlc
import sys
import os
import time
import daemon
import signal
import logging
import logging.handlers
from rfid import RfidReader
from shutdown_timer import ShutdownTimer
from enum import IntEnum
from multiprocessing import Lock

LOG_FILE = '/home/pi/annibox/annibox.log'
STDOUT_FILE = '/home/pi/annibox/stdout.log'
STDERR_FILE = '/home/pi/annibox/stderr.log'

VOLUME_LIMIT = 120
VOLUME_STEP = 10
VOLUME_DEFAULT = 50
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
rfid_reader = None
mutex = Lock()

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
        logging.info( 'play ' + self.player.get_media_player().get_media().get_mrl() )

    def pause ( self ) :
        logging.info( 'pause' )
        self.player.pause()

    def volume_up ( self ) :
        if ( self.volume < VOLUME_LIMIT ) :
            self.volume += VOLUME_STEP
            logging.info( 'set volume ' + str( self.volume ) )
            self.player.get_media_player().audio_set_volume( self.volume )

    def volume_down ( self ) :
        if ( self.volume > 0 ) :
            self.volume -= VOLUME_STEP
            logging.info( 'set volume ' + str( self.volume ) )
            self.player.get_media_player().audio_set_volume( self.volume )

    def play_album ( self, name ) :
        if not os.path.isdir( 'media/' + name ) :
            logging.info( 'album ' + name + ' not found' )
            return

        files = []
        for file in os.listdir( 'media/' + name  ) :
            files.append( 'media/' + name + '/' + file )

        if not files :
            logging.info( 'album ' + name + ' is empty' )
            return

        files.sort()
        logging.info( 'set play list %s', files )
        media_list = self.vlc_instance.media_list_new( files )
        self.player.set_media_list( media_list )
        self.player.play_item_at_index( 0 )
        logging.info( 'play ' + self.player.get_media_player().get_media().get_mrl()  )

def play ( channel ) :
    with mutex :
        anni_box.play()

def pause ( channel ) :
    with mutex :
        anni_box.pause()

def volume_up ( channel ) :
    with mutex :
        anni_box.volume_up()

def volume_down ( channel ) :
    with mutex :
        anni_box.volume_down()

def rfid_trigger ( id ) :
    with mutex :
        logging.info( 'id ' + id + ' triggered' )
        anni_box.play_album( id )

def activity_check () :
    with mutex :
        is_playing = anni_box.player.is_playing()
        logging.debug( 'activity check: ' + str( is_playing ) )
        return is_playing

def shutdown( signum, frame ) :
    shutdown_timer.stop()
    rfid_reader.stop()
    anni_box.player.stop()

stdoutFile = open( STDOUT_FILE, 'w' )
stderrFile = open( STDERR_FILE, 'w' )

with daemon.DaemonContext(
    working_directory = '/home/pi/annibox',
    signal_map = {
        signal.SIGTERM: shutdown,
        signal.SIGTSTP: shutdown
    },
    stdout = stdoutFile,
    stderr = stderrFile
) :
    logFileHandler = logging.handlers.RotatingFileHandler(
        filename = LOG_FILE,
        maxBytes = 128 * 1024,
        backupCount = 1 )
    logFileHandler.setFormatter( logging.Formatter( '%(asctime)s [%(levelname)s] %(message)s' ) )
    logging.root.addHandler( logFileHandler )
    logging.root.setLevel( logging.INFO )

    logging.info( '========================' )

    anni_box = AnniBox()
    shutdown_timer = ShutdownTimer()
    shutdown_timer.start( activity_check )
    rfid_reader = RfidReader()
    rfid_reader.start( rfid_trigger )
    shutdown_timer.join()
    rfid_reader.join()

    GPIO.output( Pin.LED, GPIO.LOW )
    GPIO.cleanup()
