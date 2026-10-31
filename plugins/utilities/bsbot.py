# ba_meta require api 9
# BsBot - fixed for BombSquad 1.7.62 only
from __future__ import annotations

import random

import babase
import bauiv1 as bui
import bascenev1 as bs

REQUIRED_VERSION = '1.7.62'

plugman = {
    'filename': 'BsBot.py',
    'version': '1.4.0',
    'authors': ['EXTRAX8'],
    'description': (
        'Spawner for AI bots using any character already registered in the '
        'game, with light and spark effects. Offline use only. '
        'Works on BombSquad 1.7.62 only.'
    ),
}

FALLBACK_CHARACTERS = [
    'Spaz', 'Zoe', 'Jack Morgan', 'Mel', 'Snake Shadow', 'Kronk',
    'Frosty', 'Bones', 'Bernard', 'Pixel', 'Santa Claus', 'Agent Johnson',
    'B-9000', 'Taobao Mascot', 'Grumbledorf', 'Easter Bunny',
]


def _detected_version() -> str:
    """Best-effort read of the game version string."""
    candidates = []
    try:
        env = babase.app.env
        for name in ('engine_version', 'version'):
            candidates.append(getattr(env, name, None))
    except Exception:
        pass
    try:
        candidates.append(getattr(babase.app, 'version', None))
    except Exception:
        pass
    for c in candidates:
        if c:
            return str(c).strip()
    return ''


def _version_ok() -> bool:
    """True only when running on BombSquad 1.7.62."""
    return _detected_version() == REQUIRED_VERSION


def _version_msg() -> str:
    found = _detected_version() or 'unknown'
    return (f'BsBot works on BombSquad {REQUIRED_VERSION} only '
            f'(detected: {found}).')


def _get_characters() -> list[str]:
    """All characters actually registered in the game."""
    try:
        names = sorted(bs.app.classic.spaz_appearances.keys())
        if names:
            return names
    except Exception:
        pass
    return list(FALLBACK_CHARACTERS)


def _is_offline() -> bool:
    """Spawning is allowed only in a purely local (offline) game."""
    try:
        if bs.get_foreground_host_activity() is None:
            return False
        # Connected to someone else's party.
        if hasattr(bs, 'get_connection_to_host_info_2'):
            if bs.get_connection_to_host_info_2() is not None:
                return False
        # Hosting a public party.
        if bs.get_public_party_enabled():
            return False
        # Remote clients connected to our party.
        for entry in bs.get_game_roster():
            if entry.get('client_id', -1) != -1:
                return False
        return True
    except Exception:
        babase.print_exception()
        return False


class BotSettingsWindow(bui.Window):
    def __init__(self) -> None:
        self.is_offline = _is_offline()
        self.characters = _get_characters()

        cfg = bui.app.config
        selected = cfg.get('BsBot Character', 'Kronk')
        if selected not in self.characters:
            selected = self.characters[0]
        self.selected = selected

        width, height = 550, 480
        uiscale = bui.app.ui_v1.uiscale
        scale = (2.0 if uiscale is bui.UIScale.SMALL else
                 1.4 if uiscale is bui.UIScale.MEDIUM else 1.0)

        super().__init__(root_widget=bui.containerwidget(
            size=(width, height),
            transition='in_scale',
            scale=scale,
        ))
        self._width = width

        bui.textwidget(
            parent=self._root_widget,
            position=(width * 0.5, height - 40),
            size=(0, 0),
            text='BsBot Character Matrix - EXTRAX8',
            scale=1.3,
            color=(0.4, 1.0, 0.6),
            h_align='center',
            v_align='center',
        )

        status = ('Local game: spawner enabled' if self.is_offline else
                  'Spawner locked (start an offline game first)')
        bui.textwidget(
            parent=self._root_widget,
            position=(width * 0.5, height - 75),
            size=(0, 0),
            text=status,
            scale=0.8,
            color=(0.2, 1.0, 0.4) if self.is_offline else (1.0, 0.3, 0.3),
            h_align='center',
            v_align='center',
        )

        bui.textwidget(
            parent=self._root_widget,
            position=(40, height - 120),
            size=(0, 0),
            text='Character:',
            scale=0.8,
            color=(0.8, 0.8, 0.8),
            v_align='center',
        )
        self.char_button = bui.buttonwidget(
            parent=self._root_widget,
            position=(40, height - 175),
            size=(260, 45),
            label=f'Bot: {self.selected}',
            color=(0.2, 0.5, 0.9),
            on_activate_call=self._cycle_character,
        )

        bui.textwidget(
            parent=self._root_widget,
            position=(40, height - 220),
            size=(0, 0),
            text='Effects:',
            scale=0.8,
            color=(0.8, 0.8, 0.8),
            v_align='center',
        )
        bui.buttonwidget(
            parent=self._root_widget,
            position=(40, height - 275),
            size=(150, 45),
            label='Royal Gold Light',
            color=(1.0, 0.84, 0.0),
            on_activate_call=self._fx_royal_gold,
        )
        bui.buttonwidget(
            parent=self._root_widget,
            position=(200, height - 275),
            size=(150, 45),
            label='Spark Stream',
            color=(1.0, 0.2, 0.2),
            on_activate_call=self._fx_sparks,
        )

        bui.buttonwidget(
            parent=self._root_widget,
            position=(40, height - 360),
            size=(470, 50),
            label='SPAWN SELECTED BOT',
            color=(0.1, 0.7, 0.3) if self.is_offline else (0.2, 0.2, 0.2),
            on_activate_call=self._spawn_configured_bot,
        )

        close = bui.buttonwidget(
            parent=self._root_widget,
            position=(width * 0.5 - 60, 20),
            size=(120, 40),
            label='Close',
            on_activate_call=self._close,
        )
        bui.containerwidget(edit=self._root_widget, cancel_button=close)

    # ------------------------------------------------------------------
    def _cycle_character(self) -> None:
        try:
            idx = (self.characters.index(self.selected) + 1) % len(
                self.characters)
        except ValueError:
            idx = 0
        self.selected = self.characters[idx]
        bui.app.config['BsBot Character'] = self.selected
        bui.app.config.commit()
        bui.buttonwidget(edit=self.char_button, label=f'Bot: {self.selected}')

    def _fx_royal_gold(self) -> None:
        if not _is_offline():
            self._deny()
            return
        activity = bs.get_foreground_host_activity()
        if activity is None:
            return
        try:
            with activity.context:
                light = bs.newnode('light', attrs={
                    'position': (0, 3, 0),
                    'color': (1.0, 0.84, 0.0),
                    'radius': 0.6,
                    'volume_intensity_scale': 10.0,
                })
                bs.animate(light, 'intensity',
                           {0.0: 0.0, 0.4: 2.0, 2.0: 0.0})
                bs.timer(2.1, light.delete)
        except Exception:
            babase.print_exception()

    def _fx_sparks(self) -> None:
        if not _is_offline():
            self._deny()
            return
        activity = bs.get_foreground_host_activity()
        if activity is None:
            return
        try:
            with activity.context:
                for _ in range(25):
                    pos = (random.uniform(-2, 2), random.uniform(1.5, 4),
                           random.uniform(-2, 2))
                    bs.emitfx(
                        position=pos,
                        velocity=(0, 3, 0),
                        count=15,
                        scale=1.0,
                        spread=1.0,
                        chunk_type='spark',
                        emit_type='chunks',
                    )
        except Exception:
            babase.print_exception()

    def _deny(self) -> None:
        bui.getsound('error').play()
        bui.screenmessage('Offline games only!', color=(1, 0, 0))

    def _spawn_configured_bot(self) -> None:
        if not _is_offline():
            self._deny()
            return
        activity = bs.get_foreground_host_activity()
        if activity is None:
            return

        try:
            from bascenev1lib.actor.spazbot import SpazBotSet, BrawlerBot

            chosen = self.selected

            # A bot class using the chosen character: the game then loads the
            # real meshes, textures and sounds of that character itself.
            bot_cls = type(
                'BsBot_' + chosen.replace(' ', '_'),
                (BrawlerBot,),
                {'character': chosen},
            )

            def on_spawn(bot) -> None:
                try:
                    if bot is not None and bot.node:
                        bot.node.name = 'SDG'
                        bot.node.name_color = (0.4, 1.0, 0.6)
                except Exception:
                    babase.print_exception()

            with activity.context:
                if not hasattr(activity, 'custom_bot_set'):
                    activity.custom_bot_set = SpazBotSet()
                activity.custom_bot_set.spawn_bot(
                    bot_cls,
                    pos=(random.uniform(-1, 1), 4, random.uniform(-1, 1)),
                    spawn_time=0.4,
                    on_spawn_call=on_spawn,
                )
            bui.screenmessage(f'SDG ({chosen}) spawned!',
                              color=(0.2, 1.0, 0.5))
        except Exception:
            babase.print_exception()
            bui.screenmessage('Launch an offline game first!',
                              color=(1, 1, 0))

    def _close(self) -> None:
        bui.containerwidget(edit=self._root_widget, transition='out_scale')


# ba_meta export babase.Plugin
class BsBotPlugin(babase.Plugin):
    def on_app_running(self) -> None:
        if not _version_ok():
            bui.screenmessage(_version_msg(), color=(1, 0.3, 0.3))
            return
        bui.screenmessage('BsBot loaded. Open it from the plugin settings.',
                          color=(0.4, 1.0, 0.6))

    def has_settings_ui(self) -> bool:
        return True

    def show_settings_ui(self, source_widget) -> None:
        if not _version_ok():
            bui.screenmessage(_version_msg(), color=(1, 0.3, 0.3))
            return
        BotSettingsWindow()
