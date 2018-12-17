# -------------------------------------------------------------
# proj:    keybender-lite
# file:    midiutil.py
# authors: Mark Sabini
# desc:    General MIDI util file.
# -------------------------------------------------------------
import threading
import time
import math
import mido

NOTE_ON = 1
NOTE_OFF = 0

class MIDITrack:
    """Insert doctstring here"""
    def __init__(self, quant=None, track=None, instr=None):
        self.quant = quant if quant is not None else 16
        self.track = track if track is not None else []
        self.instr = instr if instr is not None else 0

# The beats parameter determines how long it is
def quantize_raw_track(raw_track, quant, beats, instr=0, pickup=0):
    bpm = raw_track[0]
    raw_notes = raw_track[1]
    # Don't need to worry about notes not being turned off, since MIDIThread
    # takes care of that.
    track = [[] for x in range(quant * (beats + pickup))]
    for (note, state, time) in raw_notes:
        slot = int(round((time / 60.0) * bpm * quant))
        if slot < 0 or slot >= quant * (beats + pickup): # Out of bounds
            continue
        track[slot].append((note, state))
    return MIDITrack(quant, track[-quant * beats :], instr)

class MIDITrackBuilder:
    def __init__(self, bpm, quant, beats, instr, pickup=0):
        self.bpm = bpm
        self.quant = quant
        self.beats = beats
        self.instr = instr
        self.pickup = pickup
        self.raw_track = [self.bpm, []]
        self.start_time = time.time()

    def set_start(self, start_time=None):
        self.start_time = start_time if start_time is not None else time.time()

    def add_note(self, note, state, note_time=None):
        note_time = note_time - self.start_time if note_time is not None else time.time() - self.start_time
        self.raw_track[1].append((note, state, note_time))

    def get_raw_track(self):
        return self.raw_track

    def build_midi_track(self):
        return quantize_raw_track(self.raw_track, self.quant, self.beats, self.instr, self.pickup)


class MIDITrackPlayer:
    __MAX_CHANNELS = 16
    __MAX_TRACK_LEN = 256
    CLICK_CHANNEL = 14
    CLICK_TRACK = MIDITrack(2, [[(60, NOTE_ON)], [(60, NOTE_OFF)]], 115)
    def __init__(self, outport, bpm):
        self.outport = outport
        self.bpm = bpm
        self.instrs = [-1] * self.__MAX_CHANNELS
        self.midi_tracks = [None] * self.__MAX_CHANNELS
        self.threads = [None] * self.__MAX_CHANNELS
        self.playing = [False] * self.__MAX_CHANNELS
        self.step = 0 # Steps go 1, 2, 3, 4 ... 256, 1
        self.midi_timer = MIDITimer(self.bpm)
        self.midi_timer.bind_callback(self.on_tick)
        self.bind_channel(self.CLICK_CHANNEL, self.CLICK_TRACK)
        self.outport.send(mido.Message('program_change', channel=self.CLICK_CHANNEL, program=115))

    def __del__(self):
        self.outport.close()

    def bind_channel(self, channel, midi_track):
        self.midi_tracks[channel] = midi_track

    def play_channel(self, channel):
        self.playing[channel] = True

    def stop_channel(self, channel, wait):
        if not wait and self.threads[channel] is not None:
            self.threads[channel].stop_now()
        self.playing[channel] = False

    def clear_channel(self, channel, wait):
        self.midi_tracks[channel] = None

    # Can specify the beats of pickup (i.e. 4 would give 4 clicks)
    def start(self, pickup=0):
        self.midi_timer.start()
        self.step = -abs(pickup)

    def stop(self):
        self.midi_timer.stop()
        self.step = 0
        for thread in self.threads:
            if thread is not None:
                thread.stop_now()

    # Callback that the MIDITimer will call
    def on_tick(self):
        if self.step < 0: # Pickup, so play a click
            self.step += 1
            threading.Thread(target=self.play_click).start()
            return
        self.step = ((self.step) % self.__MAX_TRACK_LEN) + 1
        for channel, midi_track in enumerate(self.midi_tracks):
            if not self.playing[channel] or midi_track is None:
                continue
            length = math.ceil(len(midi_track.track) / midi_track.quant)
            if length == 1 or self.step % length == 1: # Edge case for length 1
                thread = MIDIThread(self.outport, channel, midi_track, self.instrs[channel], self.bpm)
                self.threads[channel] = thread
                thread.start()

    def set_bpm(self, bpm):
        self.bpm = bpm # To control how fast the track plays
        self.midi_timer.set_bpm(bpm) # To control how often the track plays

    def play_click(self):
        SLEEP_INTERVAL = 60.0 / self.bpm
        # self.outport.note_on(60, 127, self.CLICK_CHANNEL)
        self.outport.send(mido.Message('note_on', channel=self.CLICK_CHANNEL, note=60, velocity=127))
        time.sleep(SLEEP_INTERVAL / 4.0)
        # self.outport.note_off(60, 127, self.CLICK_CHANNEL)
        self.outport.send(mido.Message('note_off', channel=self.CLICK_CHANNEL, note=60, velocity=127))

    def set_instr(self, channel, instr):
        self.instrs[channel] = instr

# Makes a metronome. Can pass it a MIDITrackPlayer and it will call the callback on every tick
class MIDITimer:
    def __init__(self, bpm):
        self.bpm = bpm
        self.callback = None
        self.timer_thread = None

    def start(self):
        if self.timer_thread:
            self.timer_thread.stop_now()
            self.timer_thread.join()
        self.timer_thread = MIDITimerThread(self.bpm, self.callback)
        self.timer_thread.bind_on_finish(self.clear_timer_thread)
        self.timer_thread.start()

    def stop(self):
        if self.timer_thread:
            self.timer_thread.stop_now()
        self.clear_timer_thread()

    def bind_callback(self, callback):
        self.callback = callback

    def clear_timer_thread(self):
        self.timer_thread = None

    def is_running(self):
        return self.timer_thread is not None

    def set_bpm(self, bpm):
        self.bpm = bpm

class MIDITimerThread(threading.Thread):
    def __init__(self, bpm, callback):
        threading.Thread.__init__(self)
        self.bpm = bpm
        self.callback = callback
        self.on_finish = None
        self.stop = False

    def stop_now(self):
        self.stop = True

    def run(self):
        while(True):
            if self.stop:
                if self.on_finish is not None:
                    self.on_finish()
                return
            thread = threading.Thread(target=self.callback)
            thread.start()
            time.sleep(60.0 / self.bpm)

    def bind_on_finish(self, on_finish):
        self.on_finish = on_finish

class MIDIThread(threading.Thread):
    def __init__(self, outport, channel, midi_track, instr, bpm):
        threading.Thread.__init__(self)
        self.stop = False
        self.outport = outport
        self.channel = channel
        self.midi_track = midi_track
        self.bpm = bpm
        self.vol = 127
        self.SLEEP_INTERVAL = 60.0 / bpm / self.midi_track.quant
        self.notesOn = set()
        if instr == -1:
            # self.outport.set_instrument(self.midi_track.instr, channel=self.channel)
            self.outport.send(mido.Message('program_change', channel=self.channel, program=midi_track.instr))
        else:
            # self.outport.set_instrument(instr, channel=self.channel)
            self.outport.send(mido.Message('program_change', channel=self.channel, program=instr))

    def stop_now(self):
        self.stop = True

    def __turn_off_all(self):
        for note in self.notesOn:
            # self.outport.note_off(note, self.vol, self.channel)
            self.outport.send(mido.Message('note_off', channel=self.channel, note=note, velocity=self.vol))

    def run(self):
        for beat_index, notes in enumerate(self.midi_track.track):
            if self.stop:
                self.__turn_off_all()
                return
            if notes is not None:
                for (note, state) in notes:
                    if state == NOTE_ON:
                        # self.outport.note_on(note, self.vol, self.channel)
                        self.outport.send(mido.Message('note_on', channel=self.channel, note=note, velocity=self.vol))
                        self.notesOn.add(note)
                    else:
                        # self.outport.note_off(note, self.vol, self.channel)
                        self.outport.send(mido.Message('note_off', channel=self.channel, note=note, velocity=self.vol))
                        if note in notes:
                            self.notesOn.remove(note)
            time.sleep(self.SLEEP_INTERVAL)
        self.__turn_off_all()

class Manual:
    def __init__(self, start, keyList):
        self.start = start
        self.keyList = set(keyList)
        self.keyDict = dict()
        for index, key in enumerate(keyList):
            self.keyDict[key] = [index, KeyState.OFF]

class KeyState:
    HELD = 0
    SUSTAINED = 1
    OFF = 2
