# -------------------------------------------------------------
# proj:    keybender-lite
# file:    keybender-lite.py
# authors: Mark Sabini
# desc:    Main file for keybender-lite.
# -------------------------------------------------------------
import midiutil as mu
import mido
import pythoncom, pyHook

class KeyboardController:
    def __init__(self, outport):
        self.set_outport(outport)
        self.init_manuals()
        self.LIVE_CHANNEL = 0

    def __del__(self):
        self.outport.close()

    def set_outport(self, outport):
        self.outport = outport

    def init_manuals(self):
        ROW0_KEYS = [ord('Q'), ord('2'), ord('W'), ord('3'), ord('E'), ord('R'),
                     ord('5'), ord('T'), ord('6'), ord('Y'), ord('7'), ord('U'),
                     ord('I'), ord('9'), ord('O'), ord('0'), ord('P'), 219,
                     187, 221, 8, 220, 45,
                     46, 35, 36, 34, 33, 103, 104, 111, 105, 106, 107, 109]
        ROW1_KEYS = [160, ord('Z'), ord('S'), ord('X'), ord('D'), ord('C'), ord('V'),
                     ord('G'), ord('B'), ord('H'), ord('N'), ord('J'), ord('M'),
                     188, ord('L'), 190, 186, 191, 161]
        BASS_KEYS = [65, 20, 9, 192, 49, 27, 112, 113, 114, 115,
                     116, 117, 118, 119, 120,
                     121, 122, 123, 19, 44, 45, 46]
        self.ALL_KEYS = set(ROW0_KEYS).union(set(ROW1_KEYS)).union(set(BASS_KEYS))
        self.ROW0_START, self.ROW1_START, self.BASS_START = 60, 47, 31
        manual_row0 = mu.Manual(self.ROW0_START, ROW0_KEYS)
        manual_row1 = mu.Manual(self.ROW1_START, ROW1_KEYS)
        manual_bass = mu.Manual(self.BASS_START, BASS_KEYS)
        self.manuals = [manual_row0, manual_row1, manual_bass]
        self.sustained = False
        self.SUSTAIN_KEY = ord(' ')
        self.bias = 0

    def OnKeyDown(self, event):
        pressedKey = event.KeyID
        if pressedKey == self.SUSTAIN_KEY:
            self.sustained = True
        elif pressedKey == 39:
            self.bias += 1
        elif pressedKey == 37:
            self.bias -= 1
        elif pressedKey == 38 or pressedKey == 40:
            self.bias = 0
        elif pressedKey in self.ALL_KEYS:
            self.ProcessNoteKeyDown(pressedKey)

    def OnKeyUp(self, event):
        pressedKey = event.KeyID
        if pressedKey == self.SUSTAIN_KEY:
            self.sustained = False
            for manual in self.manuals:
                for key, keyInfo in manual.keyDict.iteritems():
                    if keyInfo[1] == mu.KeyState.SUSTAINED:
                        key = manual.start + self.bias + keyInfo[0]
                        self.outport.send(mido.Message('note_off', channel=self.LIVE_CHANNEL, note=key, velocity=127))
                        keyInfo[1] = mu.KeyState.OFF
        elif pressedKey in self.ALL_KEYS:
            self.ProcessNoteKeyUp(pressedKey)

    def ProcessNoteKeyDown(self, pressedKey):
        for manual in self.manuals:
            if pressedKey in manual.keyDict:
                keyInfo = manual.keyDict[pressedKey]
                if keyInfo[1] == mu.KeyState.HELD:
                    return
                key = manual.start + self.bias + keyInfo[0]
                self.outport.send(mido.Message('note_on', channel=self.LIVE_CHANNEL, note=key, velocity=127))
                keyInfo[1] = mu.KeyState.HELD
                return

    def ProcessNoteKeyUp(self, pressedKey):
        for manual in self.manuals:
            if pressedKey in manual.keyDict:
                keyInfo = manual.keyDict[pressedKey]
                if self.sustained:
                    if keyInfo[1] == mu.KeyState.HELD:
                        keyInfo[1] = mu.KeyState.SUSTAINED
                    return
                key = manual.start + self.bias + keyInfo[0]
                self.outport.send(mido.Message('note_off', channel=self.LIVE_CHANNEL, note=key, velocity=127))
                keyInfo[1] = mu.KeyState.OFF
                return

def get_outport():
    print("Enter the number corresponding to the desired MIDI port:")
    outputs = mido.get_output_names()
    choices = {str(index): output for index, output in enumerate(outputs)}
    for index, output in enumerate(outputs):
        print("%d: %s" % (index, output))
    while True:
        user_choice = input()
        if user_choice not in choices:
            print("The choice you entered does not correspond to a valid port. Try again.")
            continue
        name = choices[user_choice]
        try:
            outport = mido.open_output(name)
            print("Successfully opened output for \"%s\"." % name)
            return outport
        except IOError:
            print("There was an error opening the output. Try another one.")
            continue

allow = False
def listen_for_keystrokes(controller):
    whitelist = [173, 174, 175] # Still allow volume controls
    def _on_key_up(event):
        global allow
        if event.KeyID in whitelist:
            return True
        if event.Key == 'Rcontrol':
            allow = not allow
            return not allow
        elif event.Key == 'Rmenu':
            exit()
        elif not allow: controller.OnKeyUp(event)
        return allow
    def _on_key_down(event):
        global allow
        if event.KeyID in whitelist:
            return True
        if not allow: controller.OnKeyDown(event)
        return allow
    hm = pyHook.HookManager()
    hm.KeyDown = _on_key_down
    hm.KeyUp = _on_key_up
    hm.HookKeyboard()
    pythoncom.PumpMessages()

def main():
    outport = get_outport()
    if outport is None: return
    controller = KeyboardController(outport)
    listen_for_keystrokes(controller)

if __name__ == '__main__':
    main()
