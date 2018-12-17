# Keybender Lite
**Keybender Lite** takes your computer and turns it into a full-fledged MIDI controller! This is a "lite" version of [Keybender](https://github.com/ShinyCode/keybender) that only supports MIDI controller functionality, and is meant to be run from the command line. It has fewer dependencies, and should be easy to set up!

## Setup
First, clone the repo and install the requirements. You'll need to use Python 3.6.
```
>> git clone https://github.com/ShinyCode/keybender-lite.git
>> cd keybender-lite
>> pip install -r requirements.txt
```
Then, download pyHook from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyhook) (choose the one with "36" in the name, and the one corresponding to whether you're using 32-bit or 64-bit Windows). To install pyHook, inside the repo, do:
```
>> pip install [file you downloaded]
```

## Running Keybender Lite
You can run Keybender lite via:
```
python keybender-lite.py
```

## Usage
When you first start Keybender Lite, you'll need to specify the target output MIDI port. You can use [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html) to create a virtual MIDI port if needed. To quit Keybender Lite at any time, press the `right ALT` key ("Rmenu"). You can also use the `right CONTROL` key ("Rctrl") to temporarily disable/reenable Keybender Lite, since the program will swallow all keypresses. However, volume controls will still function even when Keybender Lite is active. The full list of keybinds is shown below:
```
right ALT: Quit
right CTRL: Disable/reenable Keybender Lite
Q, 2, W, 3, E, R, 5, etc.: Play [base] + [0, 1, 2, 3, 4, 5, 6, 7, ...]
Z, S, X, D, C, V, G, etc.: Play [base] - 12 + [0, 1, 2, 3, 4, 5, 6, 7, ...]
left SHIFT: Play [base] - 12 + [-1]
ESC, F1, F2, F3, F4, F5, F6, etc.: Play [base] - 24 + [0, 1, 2, 3, 4, 5, 6, 7, ...]
CAPSLOCK, TAB, `, 1: Play [base] - 24 + [-4, -3, -2, -1]
LEFT: decrement [base]
RIGHT: increment [base]
UP/DOWN: reset [base] to default value
```
The controller always plays notes relative to the value of `[base]`, which is set by default to 60 (middle C).

## License
Keybender Lite is licensed under the [MIT license](https://github.com/ShinyCode/keybender-lite/blob/master/LICENSE).
