import sys
import evdev

running = False

def run_rfid_loop ( callback ) :
    global running
    running = True

    try :
        device = evdev.InputDevice( '/dev/input/event0' )

        print( device )

        id = ''
        print( "RFID event loop started", flush = True )

        while running :
            event = device.read_one()

            while event != None :
                if event.type == evdev.ecodes.EV_KEY :
                    key_event = evdev.events.KeyEvent( event )
                    if key_event.keystate == evdev.events.KeyEvent.key_up :
                        if key_event.keycode == 'KEY_ENTER' :
                            callback( id )
                            id = ''
                        else :
                            id = id + key_event.keycode.split( '_' )[1]

                event = device.read_one()

        print( "RFID event loop stopped", flush = True )
    except KeyboardInterrupt :
        raise
    except :
        print( "ERROR: could not open RFID reader ", sys.exc_info()[0], flush = True )

def stop_rfid_loop () :
    global running
    running = False

def print_callback ( id ) :
    print( id )

if __name__ == "__main__" :
    run_rfid_loop( print_callback )