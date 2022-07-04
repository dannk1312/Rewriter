import json
import platform
from threading import Thread
from tkinter import N
import PySimpleGUI as sg
from psgtray import SystemTray
from random import random
from pynput.keyboard import Controller, Listener, Key, HotKey
import time
import pyperclip
import codecs


# Theme
sg.theme_background_color('White')
sg.theme_text_color('Black')
sg.theme_button_color('Black')
sg.theme_text_element_background_color('White')
sg.theme_input_background_color('White')
sg.theme_element_background_color('White')
alive = [True]


class Rewriter:
    def __init__(self, hotkey: str = '<ctrl>+<alt>+v',  rule: dict[str, str] = {}, delay: int = 50) -> None:
        self.controller = Controller()
        self.rule: dict[str, str] = rule
        self.delay: int = delay
        self.hotkey: list = HotKey.parse(hotkey)
        self.hotkey_str: str = hotkey
        self.writing: bool = False

    def rewrite(self, text: str):
        self.writing = True
        delay_sec = self.delay / 1000
        delay_div_2 = delay_sec / 2
        new_text = text
        for k, v in self.rule.items():
            new_text = new_text.replace(k, v)
        for c in new_text:
            if not self.writing:
                break
            self.controller.tap(c)
            time.sleep(delay_sec + delay_div_2 * (random() - 0.5))

    def set_hotkey(self, hotkey: str):
        self.hotkey = HotKey.parse(hotkey)
        self.hotkey_str = hotkey

    def __rewrite_copy(self):
        for key in self.hotkey:
            self.controller.touch(key, is_press=False)
        try:
            text = pyperclip.paste()
            self.__rewrite_thread = Thread(
                target=self.rewrite, args=(text, ), daemon=True)
            self.__rewrite_thread.start()
        except:
            pass

    def stop_rewrite(self):
        self.writing = False

    def run(self):
        try:
            self.listener.stop()
        except:
            pass

        def on_press(k):
            hotkey.press(self.listener.canonical(k))
            if k == Key.esc:
                self.stop_rewrite()

        def on_release(k):
            hotkey.release(self.listener.canonical(k))

        hotkey = HotKey(self.hotkey, self.__rewrite_copy)
        self.listener = Listener(
            on_press=on_press, on_release=on_release, daemon=True)
        self.listener.start()


def main():
    # Load config
    try:
        with open('config.json', 'r', encoding='utf-8') as file:
            config = json.load(file)
        config['delay'] = config.get('delay', 50)
        config['start_visible'] = config.get('start_visible', True)
        config['hotkey'] = config.get('hotkey', '<ctrl>+<alt>+v')
        config['rules'] = config.get('rules', [{}])
    except:
        config = {
            'delay': 50,
            'hotkey': '<ctrl>+<alt>+v',
            'rules': [{}],
            'start_visible': True
        }

    def rule_str(rule):
        if not rule:
            return ''
        return '\n'.join((f"{repr(k)[1:-1]}:{repr(v)[1:-1]}" for k, v in rule.items()))

    def str_rule(txt):
        if not txt:
            return {}
        return {codecs.decode(data[0], 'unicode_escape'): codecs.decode(data[1], 'unicode_escape') for data in (pair.split(':') for pair in txt.splitlines())}

    def ico_path():
        if platform.system() == 'Windows':
            return 'icon.ico'
        return 'icon.png'

    rewriter = Rewriter(
        delay=config['delay'],
        hotkey=config['hotkey'],
        rule=config['rules'][0])
    rewriter.run()

    input_factory = lambda key, tooltip='': sg.Input(config[key], key=key, size=(26, 1), tooltip=tooltip,
                                                     border_width=3,  justification=sg.TEXT_LOCATION_CENTER)

    def button_factory(key): return sg.Button(
        key, expand_x=True, border_width=0)

    # Application
    layout = [[sg.Text('Stop rewrite : ESC')],
              [sg.Text('Start rewrite:')],
              [input_factory(
                  'hotkey', '<Special key>: <ctrl>, <tab>, <alt>, ....\nNormal key: a, b, q, ...\n Use "+" to combine')],
              [sg.Text('Delay(ms):')],
              [input_factory('delay')],
              [sg.T(f'Rules({len(config["rules"])}):')],
              [button_factory(c) for c in '<>+-'],
              [sg.Multiline(rule_str(config['rules'][0]),
                            key='rule', autoscroll=True, size=(25, 3))],
              [button_factory('save'), button_factory('undo')],
              [sg.HorizontalSeparator(pad=(5, 10))],
              [sg.Checkbox('visible when startup', default=config['start_visible'],
                           enable_events=True, key='start_visible')],
              [sg.HorizontalSeparator(pad=(5, 10))],
              [sg.Text('made by dannk - ver 1.05 😁', justification=sg.TEXT_LOCATION_CENTER, expand_x=True)]]

    window = sg.Window('Rewriter',
                       layout,
                       finalize=True,
                       enable_close_attempted_event=True,
                       font=("Consolas", 14),
                       icon=ico_path())

    if not config['start_visible']:
        window.hide()
    tray = SystemTray(['', ['Show Window', '---', 'Exit']],
                      single_click_events=False, window=window, icon=ico_path())
    while True:
        event, values = window.read()

        if event == tray.key:
            event = values[event]
        if event in (sg.WIN_CLOSED, 'Exit'):
            break
        if event in ('Show Window', sg.EVENT_SYSTEM_TRAY_ICON_DOUBLE_CLICKED):
            window.un_hide()
            window.bring_to_front()
        elif event == sg.WIN_CLOSE_ATTEMPTED_EVENT:
            window.hide()
            tray.show_icon()
        elif event in "+-><":
            if event == '+':
                if not config['rules'][0]:
                    config['rules'].insert(0, {})
            if event == "-":
                config['rules'].pop(0)
                if not config['rules']:
                    config['rules'].append({})
            if event == ">":
                config['rules'].append(config['rules'].pop(0))
            if event == "<":
                config['rules'].insert(0, config['rules'].pop(-1))
            layout[5][0].update(value=f'Rules({len(config["rules"])}):')
            window['rule'].update(value=rule_str(config['rules'][0]))
            rewriter.rule = config['rules'][0]
        elif event in ['start_visible']:
            config[event] = values[event]
            with open('config.json', 'w', encoding='utf-8') as file:
                json.dump(config, file)
        elif event == "save":
            try:
                rewriter.set_hotkey(values['hotkey'])
                rewriter.run()
                config['hotkey'] = values['hotkey']
                rewriter.delay = config['delay'] = int(values['delay'])
                rewriter.rule = config['rules'][0] = str_rule(values['rule'])
                with open('config.json', 'w', encoding='utf-8') as file:
                    json.dump(config, file)
            except:
                window['hotkey'].update(value=config['hotkey'])
                window['delay'].update(value=config['delay'])
                window['rule'].update(value=rule_str(config['rules'][0]))
        elif event == "undo":
            window['hotkey'].update(value=config['hotkey'])
            window['delay'].update(value=config['delay'])
            window['rule'].update(value=rule_str(config['rules'][0]))

    tray.close()
    window.close()


def dialog_exist():
    def ico_path(): return 'icon.ico' if platform.system() == 'Windows' else 'icon.png'
    window = sg.Window('Rewriter Notification',
                       [
                           [sg.Text('Warnings:')],
                           [sg.Text(
                            'A previous instance of Rewritter is already running!\nLook for Rewritter icon at the tray icons.')],
                           [sg.HorizontalSeparator(pad=((5, 5), (10, 20)))],
                           [sg.Button('exit', expand_x=True, border_width=0)]
                       ],
                       finalize=True,
                       enable_close_attempted_event=True,
                       font=("Consolas", 16),
                       icon=ico_path())
    while True:
        event, values = window.read()
        if event in ('exit', sg.WIN_CLOSE_ATTEMPTED_EVENT):
            break
    window.close()


if __name__ == '__main__':
    import psutil
    apps = [p.name() for p in psutil.process_iter()]
    if apps.count('rewriter.exe') > 2:
        dialog_exist()
    else:
        main()
