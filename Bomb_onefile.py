# constants
DEBUG = True        # debug mode?
RPi = True           # is this running on the RPi?
ANIMATE = False       # animate the LCD text?
SHOW_BUTTONS = True # show the Pause and Quit buttons on the main LCD GUI?
COUNTDOWN = 60      # the initial bomb countdown value (seconds)
NUM_STRIKES = 5      # the total strikes allowed before the bomb "explodes"
NUM_PHASES = 4       # the total number of initial active bomb phases
# the various image and audio files
EXPLODE = [ "./images/explode.png", "./audio/explode.mp3" ]
SUCCESS = [ "./images/success.png", "./audio/success.mp3" ]
EXPLODING = "./audio/exploding.mp3"
STRIKE = "./audio/strike.mp3"
DEFUSED = "./audio/defused.mp3"
TICK = "./audio/tick.mp3"

# imports
from random import randint, shuffle, choice
from string import ascii_uppercase
if (RPi):
    import board
    from adafruit_ht16k33.segments import Seg7x4
    from digitalio import DigitalInOut, Direction, Pull
    from adafruit_matrixkeypad import Matrix_Keypad

#################################
# setup the electronic components
#################################
# 7-segment display
# 4 pins: 5V(+), GND(-), SDA, SCL
#         ----------7SEG---------
if (RPi):
    i2c = board.I2C()
    component_7seg = Seg7x4(i2c)
    # set the 7-segment display brightness (0 -> dimmest; 1 -> brightest)
    component_7seg.brightness = 0.5

# keypad
# 8 pins: 10, 9, 11, 5, 6, 13, 19, NA
#         -----------KEYPAD----------
if (RPi):
    # the pins
    keypad_cols = [DigitalInOut(i) for i in (board.D10, board.D9, board.D11)]
    keypad_rows = [DigitalInOut(i) for i in (board.D5, board.D6, board.D13, board.D19)]
    # the keys
    keypad_keys = ((1, 2, 3), (4, 5, 6), (7, 8, 9), ("*", 0, "#"))

    component_keypad = Matrix_Keypad(keypad_rows, keypad_cols, keypad_keys)

# jumper wires
# 10 pins: 14, 15, 18, 23, 24, 3V3, 3V3, 3V3, 3V3, 3V3
#          -------JUMP1------  ---------JUMP2---------
# the jumper wire pins
if (RPi):
    # the pins
    component_wires = [DigitalInOut(i) for i in (board.D14, board.D15, board.D18, board.D23, board.D24)]
    for pin in component_wires:
        # pins are input and pulled down
        pin.direction = Direction.INPUT
        pin.pull = Pull.DOWN

# pushbutton
# 6 pins: 4, 17, 27, 22, 3V3, 3V3
#         -BUT1- -BUT2-  --BUT3--
if (RPi):
    # the state pin (state pin is input and pulled down)
    component_button_state = DigitalInOut(board.D4)
    component_button_state.direction = Direction.INPUT
    component_button_state.pull = Pull.DOWN
    # the RGB pins
    component_button_RGB = [DigitalInOut(i) for i in (board.D17, board.D27, board.D22)]
    for pin in component_button_RGB:
        # RGB pins are output
        pin.direction = Direction.OUTPUT
        pin.value = True

# toggle switches
# 3x3 pins: 12, 16, 20, 21, 3V3, 3V3, 3V3, 3V3, GND, GND, GND, GND
#           -TOG1-  -TOG2-  --TOG3--  --TOG4--  --TOG5--  --TOG6--
if (RPi):
    # the pins
    component_toggles = [DigitalInOut(i) for i in (board.D12, board.D16, board.D20, board.D21)]
    for pin in component_toggles:
        # pins are input and pulled down
        pin.direction = Direction.INPUT
        pin.pull = Pull.DOWN

###########
# functions
###########
# generates the bomb's serial number
#  it should be made up of alphaneumeric characters, and include at least 3 digits and 3 letters
#  the sum of the digits should be in the range 1..15 to set the toggles target
#  the first three letters should be distinct and in the range 0..4 such that A=0, B=1, etc, to match the jumper wires
#  the last letter should be outside of the range
def genSerial():
    # set the digits (used in the toggle switches phase)
    serial_digits = []
    toggle_value = randint(1, 15)
    # the sum of the digits is the toggle value
    while (len(serial_digits) < 3 or toggle_value - sum(serial_digits) > 0):
        d = randint(0, min(9, toggle_value - sum(serial_digits)))
        serial_digits.append(d)

    # set the letters (used in the jumper wires phase)
    jumper_indexes = [ 0 ] * 5
    while (sum(jumper_indexes) < 3):
        jumper_indexes[randint(0, len(jumper_indexes) - 1)] = 1
    jumper_value = int("".join([ str(n) for n in jumper_indexes ]), 2)
    # the letters indicate which jumper wires must be "cut"
    jumper_letters = [ chr(i + 65) for i, n in enumerate(jumper_indexes) if n == 1 ]

    # form the serial number
    serial = [ str(d) for d in serial_digits ] + jumper_letters
    # and shuffle it
    shuffle(serial)
    # finally, add a final letter (F..Z)
    serial += [ choice([ chr(n) for n in range(70, 91) ]) ]
    # and make the serial number a string
    serial = "".join(serial)

    return serial, toggle_value, jumper_value

# generates the keypad combination from a keyword and rotation key
def genKeypadCombination():
    # encrypts a keyword using a rotation cipher
    def encrypt(keyword, rot):
        cipher = ""

        # encrypt each letter of the keyword using rot
        for c in keyword:
            cipher += chr((ord(c) - 65 + rot) % 26 + 65)

        return cipher

    # returns the keypad digits that correspond to the passphrase
    def digits(passphrase):
        combination = ""
        keys = [ None, None, "ABC", "DEF", "GHI", "JKL", "MNO", "PRS", "TUV", "WXY" ]

        # process each character of the keyword
        for c in passphrase:
            for i, k in enumerate(keys):
                if (k and c in k):
                    # map each character to its digit equivalent
                    combination += str(i)

        return combination

    # the list of keywords and matching passphrases
    keywords = { "BADGER": "RIVER",\
                 "BANDIT": "FADED",\
                 "CABLES": "SPINY",\
                 "CANOPY": "THROW",\
                 "FIELDS": "CYCLE",\
                 "FIERCE": "ALOOF",\
                 "IMMUNE": "STOLE",\
                 "IMPACT": "TOADY",\
                 "MIDWAY": "FEIGN",\
                 "MIGHTY": "CARVE",\
                 "REBORN": "TRICK",\
                 "RECALL": "CLIMB",\
                 "SYMBOL": "LEAVE",\
                 "SYSTEM": "FOXES",\
                 "WIDELY": "BOUND",\
                 "WINGED": "YACHT" }
    # the rotation cipher key
    rot = randint(1, 25)

    # pick a keyword and matching passphrase
    keyword, passphrase = choice(list(keywords.items()))
    # encrypt the passphrase and get its combination
    cipher_keyword = encrypt(keyword, rot)
    combination = digits(passphrase)
    # the two random hexadecimal values
    hex_value_1 = hex(randint(16, 100))[2:].upper().zfill(0)
    hex_value_2 = hex(randint(16, 100))[2:].upper().zfill(0)
    hex_value_3 = hex(randint(16, 100))[2:].upper().zfill(0)
    
    # calculate the decimal equivalents
    decimal_value_1 = int(hex_value_1, 16)
    decimal_value_2 = int(hex_value_2, 16)
    decimal_value_3 = int(hex_value_3, 16)
    
    # multiply the decimal values to form the keypad combination
    combination = str(decimal_value_1 * decimal_value_2 * decimal_value_3)
    print (combination, type((combination)))
    combination = "45678"
    return keyword, cipher_keyword, rot, combination, passphrase

###############################
# generate the bomb's specifics
###############################
# generate the bomb's serial number (which also gets us the toggle and jumper target values)
#  serial: the bomb's serial number
#  toggles_target: the toggles phase defuse value
#  wires_target: the wires phase defuse value
serial, toggles_target, wires_target = genSerial()

# generate the combination for the keypad phase
#  keyword: the plaintext keyword for the lookup table
#  cipher_keyword: the encrypted keyword for the lookup table
#  rot: the key to decrypt the keyword
#  keypad_target: the keypad phase defuse value (combination)
#  passphrase: the target plaintext passphrase
keyword, cipher_keyword, rot, keypad_target, passphrase = genKeypadCombination()

# generate the color of the pushbutton (which determines how to defuse the phase)
button_color = choice(["R", "G", "B"])
# appropriately set the target (R is None)
button_target = None



if (DEBUG):
    print(f"Serial number: {serial}")
    print(f"Toggles target: {bin(toggles_target)[2:].zfill(4)}/{toggles_target}")
    print(f"Wires target: {bin(wires_target)[2:].zfill(5)}/{wires_target}")
    print(f"Keypad target: {keypad_target}/{passphrase}/{keyword}/{cipher_keyword}(rot={rot})")
    print(f"Button target: {button_target}")

# set the bomb's LCD bootup text
boot_text = f"Booting...\n\x00\x00"\
            f"*Kernel v3.1.4-159 loaded.\n"\
            f"Initializing subsystems...\n\x00"\
            f"*System model: 102BOMBv4.2\n"\
            f"*Serial number: {serial}\n"\
            f"Encrypting keypad...\n\x00"\
            f"*Keyword: {cipher_keyword}; key: {rot}\n"\
            f"*{' '.join(ascii_uppercase)}\n"\
            f"*{' '.join([str(n % 10) for n in range(26)])}\n"\
            f"Rendering phases...\x00"


from tkinter import *
import tkinter
from threading import Thread
import pygame
from time import sleep
import os
import sys

#########
# classes
#########
# the LCD display GUI
class Lcd(Frame):
    def __init__(self, window):
        super().__init__(window, bg="black")
        # make the GUI fullscreen
        #window.attributes("-fullscreen", True)
        # we need to know about the timer (7-segment display) to be able to pause/unpause it
        self._timer = None
        # we need to know about the pushbutton to turn off its LED when the program exits
        self._button = None
        # setup the initial "boot" GUI
        self.setupBoot()

    # sets up the LCD "boot" GUI
    def setupBoot(self):
        # set column weights
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.columnconfigure(2, weight=1)
        # the scrolling informative "boot" text
        self._lscroll = Label(self, bg="black", fg="white", font=("Courier New", 14), text="", justify=LEFT)
        self._lscroll.grid(row=0, column=0, columnspan=3, sticky=W)
        self.pack(fill=BOTH, expand=True)

    # sets up the LCD GUI
    def setup(self):
        # the timer
        self._ltimer = Label(self, bg="black", fg="#00ff00", font=("Courier New", 18), text="Time left: ")
        self._ltimer.grid(row=1, column=0, columnspan=3, sticky=W)
        # the keypad passphrase
        self._lkeypad = Label(self, bg="black", fg="#ff0000", font=("Courier New", 18), text="Keypad phase: ")
        self._lkeypad.grid(row=2, column=0, columnspan=3, sticky=W)
        # the jumper wires status
        self._lwires = Label(self, bg="black", fg="#ff0000", font=("Courier New", 18), text="Wires phase: ")
        self._lwires.grid(row=3, column=0, columnspan=3, sticky=W)
        # the pushbutton status
        self._lbutton = Label(self, bg="black", fg="#ff0000", font=("Courier New", 18), text="Button phase: ")
        self._lbutton.grid(row=4, column=0, columnspan=3, sticky=W)
        # the toggle switches status
        self._ltoggles = Label(self, bg="black", fg="#ff0000", font=("Courier New", 18), text="Toggles phase: ")
        self._ltoggles.grid(row=5, column=0, columnspan=2, sticky=W)
        # the strikes left
        self._lstrikes = Label(self, bg="black", fg="#00ff00", font=("Courier New", 18), text="Strikes left: ")
        self._lstrikes.grid(row=5, column=2, sticky=W)
        if (SHOW_BUTTONS):
            # the pause button (pauses the timer)
            self._bpause = tkinter.Button(self, bg="red", fg="white", font=("Courier New", 18), text="Pause", anchor=CENTER, command=self.pause)
            self._bpause.grid(row=6, column=0, pady=40)
            # the quit button
            self._bquit = tkinter.Button(self, bg="red", fg="white", font=("Courier New", 18), text="Quit", anchor=CENTER, command=self.quit)
            self._bquit.grid(row=6, column=2, pady=40)

    # lets us pause/unpause the timer (7-segment display)
    def setTimer(self, timer):
        self._timer = timer

    # lets us turn off the pushbutton's RGB LED
    def setButton(self, button):
        self._button = button

    # pauses the timer
    def pause(self):
        if (RPi):
            self._timer.pause()

    # setup the conclusion GUI (explosion/defusion)
    def conclusion(self, exploding=False, success=False):
        while (not exploding and pygame.mixer.music.get_busy()):
            sleep(0.1)
        # destroy/clear widgets that are no longer needed
        self._lscroll["text"] = ""
        self._ltimer.destroy()
        self._lkeypad.destroy()
        self._lwires.destroy()
        self._lbutton.destroy()
        self._ltoggles.destroy()
        self._lstrikes.destroy()
        if (SHOW_BUTTONS):
            self._bpause.destroy()
            self._bquit.destroy()

        # reconfigure the GUI
        # the appropriate (success/explode) image
        if (success):
            image = PhotoImage(file=SUCCESS[0])
        else:
            image = PhotoImage(file=EXPLODE[0])
        self._lscroll["image"] = image
        self._lscroll.image = image
        self._lscroll.grid(row=0, column=0, columnspan=3, sticky=EW)
        # the retry button
        self._bretry = tkinter.Button(self, bg="red", fg="white", font=("Courier New", 18), text="Retry", anchor=CENTER, command=self.retry)
        self._bretry.grid(row=1, column=0, pady=40)
        # the quit button
        self._bquit = tkinter.Button(self, bg="red", fg="white", font=("Courier New", 18), text="Quit", anchor=CENTER, command=self.quit)
        self._bquit.grid(row=1, column=2, pady=40)
        # play the appropriate (success/explode) audio
        if (success):
            pygame.mixer.music.load(SUCCESS[1])
        else:
            pygame.mixer.music.load(EXPLODE[1])
        pygame.mixer.music.play(1)

    # re-attempts the bomb (after an explosion or a successful defusion)
    def retry(self):
        # re-launch the program (and exit this one)
        os.execv(sys.executable, ["python3"] + [sys.argv[0]])
        exit(0)

    # quits the GUI, resetting some components
    def quit(self):
        if (RPi):
            # turn off the 7-segment display
            self._timer._running = False
            self._timer._component.blink_rate = 0
            self._timer._component.fill(0)
            # turn off the pushbutton's LED
            for pin in self._button._rgb:
                pin.value = True
        # exit the application
        exit(0)

# template (superclass) for various bomb components/phases
class PhaseThread(Thread):
    def __init__(self, name, component=None, target=None):
        super().__init__(name=name, daemon=True)
        # phases have an electronic component (which usually represents the GPIO pins)
        self._component = component
        # phases have a target value (e.g., a specific combination on the keypad, the proper jumper wires to "cut", etc)
        self._target = target
        # phases can be successfully defused
        self._defused = False
        # phases can be failed (which result in a strike)
        self._failed = False
        # phases have a value (e.g., a pushbutton can be True/Pressed or False/Released, several jumper wires can be "cut"/False, etc)
        self._value = None
        # phase threads are either running or not
        self._running = False

# template (superclass) for various numeric bomb components/phases
# these types of phases can be represented as the binary representation of an integer
# e.g., jumper wires phase, toggle switches phase
class NumericPhase(PhaseThread):
    def __init__(self, name, component=None, target=None, display_length=0):
        super().__init__(name, component, target)
        # the default value is the current state of the component
        self._value = self._get_int_state()
        # we need to know the previous state to detect state change
        self._prev_value = self._value
        # we need to know the display length (character width) of the pin states (for the GUI)
        self._display_length = display_length

    # runs the thread
    def run(self):
        self._running = True
        while (self._running):
            # get the component value
            self._value = self._get_int_state()
            # the component value is correct -> phase defused
            if (self._value == self._target):
                self._defused = True
            # the component state has changed
            elif (self._value != self._prev_value):
                # one or more component states are incorrect -> phase failed (strike)
                if (not self._check_state()):
                    self._failed = True
                # note the updated state
                self._prev_value = self._value
            sleep(0.1)

    # checks the component for an incorrect state (only internally called)
    def _check_state(self):
        # get a list (True/False) of the current, previous, and valid (target) component states
        states = self._get_bool_state()
        prev_states = [ bool(int(c)) for c in bin(self._prev_value)[2:].zfill(self._display_length) ]
        valid_states = [ bool(int(c)) for c in bin(self._target)[2:].zfill(self._display_length) ]
        # go through each component state
        for i in range(len(states)):
            # a component state has changed *and* it is in an invalid state -> phase failed (strike)
            if (states[i] != prev_states[i] and states[i] != valid_states[i]):
                return False
        return True

    # returns the state of the component as a list (True/False)
    def _get_bool_state(self):
        return [ pin.value for pin in self._component ]

    # returns the state of the component as an integer
    def _get_int_state(self):
        return int("".join([ str(int(n)) for n in self._get_bool_state() ]), 2)

    # returns the state of the component as a string
    def __str__(self):
        if (self._defused):
            return "DEFUSED"
        else:
            return f"{bin(self._value)[2:].zfill(self._display_length)}/{self._value}"

# the timer phase
class Timer(PhaseThread):
    def __init__(self, component, initial_value, name="Timer"):
        super().__init__(name, component)
        # the default value is the specified initial value
        self._value = initial_value
        # is the timer paused?
        self._paused = False
        # initialize the timer's minutes/seconds representation
        self._min = ""
        self._sec = ""
        # by default, each tick is 1 second
        self._interval = 1

    # runs the thread
    def run(self):
        self._running = True
        while (self._running):
            if (not self._paused):
                # update the timer and display its value on the 7-segment display
                self._update()
                self._component.print(str(self))
                # wait 1s (default) and continue
                sleep(self._interval)
                # the timer has expired -> phase failed (explode)
                if (self._value == 0):
                    self._running = False
                self._value -= 1
            else:
                sleep(0.1)

    # updates the timer (only internally called)
    def _update(self):
        self._min = f"{self._value // 60}".zfill(2)
        self._sec = f"{self._value % 60}".zfill(2)

    # pauses and unpauses the timer
    def pause(self):
        # toggle the paused state
        self._paused = not self._paused
        # blink the 7-segment display when paused
        self._component.blink_rate = (2 if self._paused else 0)

    # returns the timer as a string (mm:ss)
    def __str__(self):
        return f"{self._min}:{self._sec}"

# the keypad phase
class Keypad(PhaseThread):
    def __init__(self, component, target, name="Keypad"):
        super().__init__(name, component, target)
        # the default value is an empty string
        self._value = ""

    # runs the thread
    def run(self):
        self._running = True
        while (self._running):
            # process keys when keypad key(s) are pressed
            if (self._component.pressed_keys):
                # debounce
                while (self._component.pressed_keys):
                    try:
                        # just grab the first key pressed if more than one were pressed
                        key = self._component.pressed_keys[0]
                    except:
                        key = ""
                    sleep(0.1)
                if key == "#":
                    pygame.mixer.music.load("ding.mp3")
                    pygame.mixer.music.play(loops=(toggles_target-1))
                else:
                    # log the key
                    self._value += str(key)
                    # the combination is correct -> phase defused
                    if (self._value == self._target):
                        self._defused = True
                    # the combination is incorrect -> phase failed (strike)
                    elif (self._value != self._target[0:len(self._value)]):
                        self._failed = True
                sleep(0.1)

    # returns the keypad combination as a string
    def __str__(self):
        if (self._defused):
            return "DEFUSED"
        else:
            return self._value

# the jumper wires phase
class Wires(NumericPhase):
    def __init__(self, component, target, display_length, name="Wires"):
        super().__init__(name, component, target, display_length)

    # returns the jumper wires state as a string
    def __str__(self):
        if (self._defused):
            return "DEFUSED"
        else:
            return "".join([ chr(int(i)+65) if pin.value else "." for i, pin in enumerate(self._component) ])

# the pushbutton phase
# the pushbutton phase
class Button(PhaseThread):
    def __init__(self, component_state, component_rgb, target, color, name="Button"):
        super().__init__(name, component_state, target)
        # the default value is False/Released
        self._value = False
        # has the pushbutton been pressed?
        self._pressed = False
        # we need the pushbutton's RGB pins to set its color
        self._rgb = component_rgb
        # the pushbutton's randomly selected LED color
        self._color = color
        # define the number of clicks required to defuse based on color
        self._clicks_required = 1  # Default for Red
        if color == "G":
            self._clicks_required = 2
        elif color == "B":
            self._clicks_required = 3
        # count the number of clicks
        self._click_count = 0

    # runs the thread
    def run(self):
        self._running = True
        # set the RGB LED color
        self._rgb[0].value = False if self._color == "R" else True
        self._rgb[1].value = False if self._color == "G" else True
        self._rgb[2].value = False if self._color == "B" else True
        while (self._running):
            # get the pushbutton's state
            self._value = self._component.value
            # it is pressed
            if (self._value):
                # note it
                self._pressed = True
            # it is released
            else:
                # was it previously pressed?
                if (self._pressed):
                    self._click_count += 1
                    # check if the required number of clicks is reached
                    if self._click_count == self._clicks_required:
                        self._defused = True
                    self._pressed = False
            sleep(0.1)

    # returns the pushbutton's state as a string
    def __str__(self):
        if (self._defused):
            return "DEFUSED"
        else:
            return f"{self._click_count} clicks"


# the toggle switches phase
class Toggles(NumericPhase):
    def __init__(self, component, target, display_length, name="Toggles"):
        super().__init__(name, component, target, display_length)

    # Add the new defusal logic here
    def defuse_wires(self):
        current_time = datetime.now().strftime("%H:%M:%S")
        # Calculate the sum of digits in the current time
        sum_of_digits = sum(int(digit) for digit in current_time if digit.isdigit())
        
        # Update the wire_target based on the sum of digits
        wire_target = sum_of_digits
        self._target = wire_target
        
        # Diffuse wires based on the binary representation of wire_target
        binary_representation = bin(wire_target)[2:]  # Convert to binary and remove the '0b' prefix
        self.diffuse_wires(binary_representation)

    def diffuse_wires(self, binary_representation):
        # Your logic to diffuse wires based on binary_representation
        # For example, if binary_representation is '101', diffuse wires A and C
        # For demonstration purposes, print the wires to be diffused
        print(f"Diffusing wires: {binary_representation}")

    # Override the defuse method to trigger the defusal of wires
    def defuse(self):
        super().defuse()
        self.defuse_wires()

    # Override the _check_state method to customize the state check
    def _check_state(self):
        # Your custom state check logic, if needed
        return super()._check_state()

###########
# functions
###########
# generates the bootup sequence on the LCD
def bootup(n=0):
    # if we're not animating (or we're at the end of the bootup text)
    if (not ANIMATE or n == len(boot_text)):
        # if we're not animating, render the entire text at once (and don't process \x00)
        if (not ANIMATE):
            gui._lscroll["text"] = boot_text.replace("\x00", "")
        # configure the remaining GUI widgets
        gui.setup()
        # setup the phase threads, execute them, and check their statuses
        if (RPi):
            gui.after(1000, setup_phases)
    # if we're animating
    else:
        # add the next character (but don't render \x00 since it specifies a longer pause)
        if (boot_text[n] != "\x00"):
            gui._lscroll["text"] += boot_text[n]

        # scroll the next character after a slight delay (\x00 is a longer delay)
        gui.after(25 if boot_text[n] != "\x00" else 750, bootup, n + 1)

# sets up the phase threads
def setup_phases():
    global timer, keypad, wires, button, toggles
    
    # setup the timer thread
    timer = Timer(component_7seg, COUNTDOWN)
    # bind the 7-segment display to the LCD GUI so that it can be paused/unpaused from the GUI
    gui.setTimer(timer)
    # setup the keypad thread
    keypad = Keypad(component_keypad, keypad_target)
    # setup the jumper wires thread
    wires = Wires(component_wires, wires_target, display_length=5)
    # setup the pushbutton thread
    button = Button(component_button_state, component_button_RGB, button_target, button_color, timer)
    # bind the pushbutton to the LCD GUI so that its LED can be turned off when we quit
    gui.setButton(button)
    # setup the toggle switches thread
    toggles = Toggles(component_toggles, toggles_target, display_length=4)

    # start the phase threads
    timer.start()
    keypad.start()
    wires.start()
    button.start()
    toggles.start()
    
    # play the tick audio
    pygame.mixer.music.load(TICK)
    pygame.mixer.music.play(-1)

    # check the phases
    gui.after(100, check_phases)

# checks the phase threads
def check_phases():
    global active_phases, exploding

    # restart the tick audio if needed
    if (not exploding and not pygame.mixer.music.get_busy()):
        pygame.mixer.music.load(TICK)
        pygame.mixer.music.play(-1)
        
    # check the timer
    if (timer._running):
        # update the GUI
        gui._ltimer["text"] = f"Time left: {timer}"
        # play the exploding audio at t-10s
        if (not exploding and timer._interval * timer._value <= 11.25):
            exploding = True
            component_7seg.blink_rate = 1
            pygame.mixer.music.load(EXPLODING)
            pygame.mixer.music.play(1)
        if (timer._value == 60):
            gui._ltimer["fg"] = "#ff0000"
    else:
        # the countdown has expired -> explode!
        # turn off the bomb and render the conclusion GUI
        turn_off()
        gui.after(100, gui.conclusion, exploding, False)
        # don't check any more phases
        return
    # check the keypad
    if (keypad._running):
        # update the GUI
        gui._lkeypad["text"] = f"Combination: {keypad}"
        # the phase is defused -> stop the thread
        if (keypad._defused):
            keypad._running = False
            gui._lkeypad["fg"] = "#00ff00"
            defused()
        # the phase has failed -> strike
        elif (keypad._failed):
            strike()
            # reset the keypad
            keypad._failed = False
            keypad._value = ""
    # check the wires
    if (wires._running):
        # update the GUI
        gui._lwires["text"] = f"Wires: {wires}"
        # the phase is defused -> stop the thread
        if (wires._defused):
            wires._running = False
            gui._lwires["fg"] = "#00ff00"
            defused()
        # the phase has failed -> strike
        elif (wires._failed):
            strike()
            # reset the wires
            wires._failed = False
    # check the button
    if (button._running):
        # update the GUI
        gui._lbutton["text"] = f"Button: {button}"
        # the phase is defused -> stop the thread
        if (button._defused):
            button._running = False
            gui._lbutton["fg"] = "#00ff00"
            defused()
        # the phase has failed -> strike
        elif (button._failed):
            strike()
            # reset the button
            button._failed = False
    # check the toggles
    if (toggles._running):
        # update the GUI
        gui._ltoggles["text"] = f"Toggles: {toggles}"
        # the phase is defused -> stop the thread
        if (toggles._defused):
            toggles._running = False
            gui._ltoggles["fg"] = "#00ff00"
            defused()
        # the phase has failed -> strike
        elif (toggles._failed):
            strike()
            # reset the toggles
            toggles._failed = False

    # note the strikes on the GUI
    gui._lstrikes["text"] = f"Strikes left: {strikes_left}"
    # too many strikes -> explode!
    if (strikes_left == 0):
        # turn off the bomb and render the conclusion GUI
        turn_off()
        gui.after(1000, gui.conclusion, exploding, False)
        # stop checking phases
        return
    # a few strikes left -> timer goes twice as fast!
    elif (strikes_left == 2 and not exploding):
        timer._interval = 0.5
        gui._lstrikes["fg"] = "#ff0000"
    # one strike left -> timer goes even faster!
    elif (strikes_left == 1 and not exploding):
        timer._interval = 0.25

    # the bomb has been successfully defused!
    if (active_phases == 0):
        # turn off the bomb and render the conclusion GUI
        turn_off()
        gui.after(100, gui.conclusion, exploding, True)
        # stop checking phases
        return

    # check the phases again after a slight delay
    gui.after(100, check_phases)

# handles a strike
def strike():
    global strikes_left
    
    # note the strike
    strikes_left -= 1
    # play the strike audio
    if (not exploding):
        pygame.mixer.music.load(STRIKE)
        pygame.mixer.music.play(1)

# handles when a phase is defused
def defused():
    global active_phases

    # note that the phase is defused
    active_phases -= 1
    # play the defused audio
    if (not exploding):
        pygame.mixer.music.load(DEFUSED)
        pygame.mixer.music.play(1)

# turns off the bomb
def turn_off():
    # stop all threads
    timer._running = False
    keypad._running = False
    wires._running = False
    button._running = False
    toggles._running = False

    # turn off the 7-segment display
    component_7seg.blink_rate = 0
    component_7seg.fill(0)
    # turn off the pushbutton's LED
    for pin in button._rgb:
        pin.value = True

######
# MAIN
######

# initialize pygame
pygame.init()

# initialize the LCD GUI
window = Tk()
gui = Lcd(window)

# initialize the bomb strikes, active phases (i.e., not yet defused), and if the bomb is exploding
strikes_left = NUM_STRIKES
active_phases = NUM_PHASES
exploding = False

# "boot" the bomb
gui.after(1000, bootup)

# display the LCD GUI
window.mainloop()

