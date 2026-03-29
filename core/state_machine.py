"""
state_machine.py — Finite State Machine for the analysis workflow.

States match the HMI sequence diagram:

    IDLE → CONNECTING → CALIBRATING → THERMAL_WAIT → SLIDE_LOADING
         → CAPTURING → ANALYSING → RESULTS → REPORT_GENERATED → IDLE

Transitions are driven by events from hardware & UI.
"""

from __future__ import annotations

import logging
from enum import Enum, auto
from typing import Any, Callable

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class State(Enum):
    """All possible HMI states."""
    IDLE = auto()
    CONNECTING = auto()
    CALIBRATING = auto()
    THERMAL_WAIT = auto()
    SLIDE_LOADING = auto()
    CAPTURING = auto()
    ANALYSING = auto()
    RESULTS = auto()
    REPORT_GENERATED = auto()
    ERROR = auto()


class Event(Enum):
    """Events that trigger state transitions."""
    START = auto()
    CONNECTED = auto()
    CONNECTION_FAILED = auto()
    CALIBRATED = auto()
    TEMP_STABLE = auto()
    SLIDE_LOADED = auto()
    CAPTURE_DONE = auto()
    ANALYSIS_DONE = auto()
    REPORT_DONE = auto()
    NEW_SAMPLE = auto()
    ERROR = auto()
    RESET = auto()


# Transition table: (current_state, event) → next_state
_TRANSITIONS: dict[tuple[State, Event], State] = {
    (State.IDLE, Event.START):                  State.CONNECTING,
    (State.CONNECTING, Event.CONNECTED):        State.CALIBRATING,
    (State.CONNECTING, Event.CONNECTION_FAILED): State.ERROR,
    (State.CALIBRATING, Event.CALIBRATED):      State.THERMAL_WAIT,
    (State.THERMAL_WAIT, Event.TEMP_STABLE):    State.SLIDE_LOADING,
    (State.SLIDE_LOADING, Event.SLIDE_LOADED):  State.CAPTURING,
    (State.CAPTURING, Event.CAPTURE_DONE):      State.ANALYSING,
    (State.ANALYSING, Event.ANALYSIS_DONE):     State.RESULTS,
    (State.RESULTS, Event.REPORT_DONE):         State.REPORT_GENERATED,
    (State.REPORT_GENERATED, Event.NEW_SAMPLE): State.SLIDE_LOADING,
    # Global transitions
    (State.ERROR, Event.RESET):                 State.IDLE,
}

# Any state can transition to ERROR on Event.ERROR
for s in State:
    if s != State.ERROR:
        _TRANSITIONS[(s, Event.ERROR)] = State.ERROR


class StateMachine(QObject):
    """
    Observable finite state machine.

    Signals
    -------
    state_changed(State, State)
        (old_state, new_state) emitted on every transition.
    """

    state_changed = pyqtSignal(object, object)  # (State, State)

    def __init__(self, parent: Any | None = None) -> None:
        super().__init__(parent)
        self._state = State.IDLE
        self._callbacks: dict[State, list[Callable[[State, State], None]]] = {}

    @property
    def state(self) -> State:
        return self._state

    def handle_event(self, event: Event) -> bool:
        """
        Process an event. Returns True if a transition occurred.
        """
        key = (self._state, event)
        new_state = _TRANSITIONS.get(key)

        if new_state is None:
            logger.warning(
                "No transition for (%s, %s) — ignored",
                self._state.name, event.name,
            )
            return False

        old = self._state
        self._state = new_state
        logger.info("FSM: %s --%s--> %s", old.name, event.name, new_state.name)
        self.state_changed.emit(old, new_state)

        # Fire registered callbacks
        for cb in self._callbacks.get(new_state, []):
            try:
                cb(old, new_state)
            except Exception:
                logger.exception("Callback error on %s", new_state.name)

        return True

    def on_enter(self, state: State, callback: Callable[[State, State], None]) -> None:
        """Register a callback to fire when entering *state*."""
        self._callbacks.setdefault(state, []).append(callback)

    def reset(self) -> None:
        """Force-reset to IDLE."""
        old = self._state
        self._state = State.IDLE
        self.state_changed.emit(old, State.IDLE)
        logger.info("FSM force-reset to IDLE")
