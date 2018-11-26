#!/usr/bin/python3
# import Raspberry Pi GPIO library
import RPi.GPIO as GPIO
import time
import vlc
from enum import IntEnum

VOLUME_LIMIT = 200
VOLUME_STEP = 10
VOLUME_DEFAULT = 100
BOUNCE_TIME = 200

class ButtonPin ( IntEnum ) :
    GREEN = 19
    RED = 24
    BLUE = 23
    YELLOW = 21

class Button ( IntEnum ) :
    PLAY = ButtonPin.GREEN
    PAUSE = ButtonPin.YELLOW
    VOL_UP = ButtonPin.RED
    VOL_DOWN = ButtonPin.BLUE

vlcInstance = vlc.Instance( "--aout alsa" )
player = vlcInstance.media_player_new()
player.audio_output_device_set( "alsa", "hw0:0" )
player.audio_set_volume( VOLUME_DEFAULT )
volume = VOLUME_DEFAULT

# ignore warnings for now
GPIO.setwarnings( False )

# Use physical pin numbering
GPIO.setmode( GPIO.BOARD )

# set the pins to be an input pin and set initial value to be pulled low (off)
GPIO.setup( Button.PLAY.value, GPIO.IN, pull_up_down = GPIO.PUD_DOWN )
GPIO.setup( Button.PAUSE.value, GPIO.IN, pull_up_down = GPIO.PUD_DOWN )
GPIO.setup( Button.VOL_UP.value, GPIO.IN, pull_up_down = GPIO.PUD_DOWN )
GPIO.setup( Button.VOL_DOWN.value, GPIO.IN, pull_up_down = GPIO.PUD_DOWN )

# add callback functions for each button press
def play ( channel ) :
    global player
    print( "play" )
    player.set_media( vlcInstance.media_new( "test.mp3" ) )
    player.play()

def pause ( channel ) :
    global player
    print( "pause" )
    player.pause()

def volume_up ( channel ) :
    global volume
    global player

    if ( volume < VOLUME_LIMIT ) :
        volume += VOLUME_STEP
        print( "set volume " + str( volume ) )
        player.audio_set_volume( volume )

def volume_down ( channel ) :
    global volume
    global player

    if ( volume > 0 ) :
        volume -= VOLUME_STEP
        print( "set volume " + str( volume ) )
        player.audio_set_volume( volume )

# setup event on pin 10 rising edge
GPIO.add_event_detect( Button.PLAY.value, GPIO.RISING, callback = play, bouncetime = BOUNCE_TIME )
GPIO.add_event_detect( Button.PAUSE.value, GPIO.RISING, callback = pause, bouncetime = BOUNCE_TIME )
GPIO.add_event_detect( Button.VOL_UP.value, GPIO.RISING, callback = volume_up, bouncetime = BOUNCE_TIME )
GPIO.add_event_detect( Button.VOL_DOWN.value, GPIO.RISING, callback = volume_down, bouncetime = BOUNCE_TIME )

message = input( "Press [Enter] to quit\n" )
GPIO.cleanup()
