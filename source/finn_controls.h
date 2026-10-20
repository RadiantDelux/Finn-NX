#ifndef FINN_CONTROLS_H
#define FINN_CONTROLS_H

enum FinnAction {
    FINN_ACTION_KICK = 1 << 0,
    FINN_ACTION_RECOVERY = 1 << 1,
    FINN_ACTION_TAP = 1 << 2,
    FINN_ACTION_LEFT = 1 << 3,
    FINN_ACTION_RIGHT = 1 << 4,
    FINN_ACTION_RESTART = 1 << 5,
};

/* Mirrors the managed helper's action bits; called only on UnityMain. */
int finn_controls_tick(int down, int held);

#endif
