/* dcr_input.h -- Switch input -> Unity's Android event payloads.
 *
 * Unity receives input through UnityPlayer.nativeInjectEvent(InputEvent)
 * and then reads the event back through JNI (MotionEvent.getX(i), ...). So an
 * event is a Java object of class android/view/MotionEvent or KeyEvent whose
 * payload is one of these structs; jni_android.c serves the getters from it. */
#ifndef DCR_INPUT_H
#define DCR_INPUT_H
#include <stdint.h>

#define DCR_MAX_POINTERS 10

/* Shared JNI gamepad identity inherited from the Android runtime. Finn's
 * game actions use touch events and the managed bridge in finn_controls.c. */
#define DCR_PAD_DEVICE_ID 7
#define DCR_PAD_NAME "NVIDIA Corporation NVIDIA Controller v01.04"
#define DCR_PAD_SOURCES 0x01000511 /* JOYSTICK | GAMEPAD | DPAD | KEYBOARD */
#define DCR_SRC_JOYSTICK 0x01000010
#define DCR_SRC_GAMEPAD_KEYS 0x00000501 /* GAMEPAD | KEYBOARD, as a pad's KeyEvent */
#define DCR_AXES 24                     /* MotionEvent.AXIS_X (0) .. AXIS_BRAKE (23) */

typedef struct {
    int32_t action; /* MotionEvent action incl. pointer index bits */
    int32_t count;
    int32_t id[DCR_MAX_POINTERS];
    float x[DCR_MAX_POINTERS], y[DCR_MAX_POINTERS];
    int64_t down_time_ms, event_time_ms;
    int32_t source; /* 0x1002 touchscreen, or DCR_SRC_JOYSTICK */
    int32_t device_id;
    float axis[DCR_AXES]; /* joystick events: getAxisValue(AXIS_*) */
} DcrMotion;

typedef struct {
    int32_t action; /* ACTION_DOWN 0 / ACTION_UP 1 */
    int32_t key_code;
    int32_t meta_state;
    int32_t repeat;
    int32_t unicode;
    int32_t source; /* 0x501 gamepad | 0x101 keyboard */
    int32_t device_id;
    int64_t down_time_ms, event_time_ms;
} DcrKey;

/* The gamepad's axes, as InputDevice.getMotionRanges() lists them. */
extern const int dcr_pad_axes[];
extern const int dcr_pad_naxes;

void dcr_input_init(void);
void dcr_input_frame(void); /* poll the pads/touch and inject events (main loop) */
void finn_input_cancel(void);

#endif
