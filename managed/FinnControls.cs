// Built against the APK's Unity 4.3 / .NET 2.0 assemblies.
// Calls the original handlers; no game state or cooldown is overwritten.
using System;
using System.Reflection;
using UnityEngine;

public static class FinnControls {
    const int Kick = 1, Recovery = 2, B = 4, Left = 8, Right = 16, Restart = 32;
    static float nextTap;
    static readonly FieldInfo birdTapped =
        typeof(FlyingBird).GetField("tapped", BindingFlags.NonPublic | BindingFlags.Instance);
    static readonly MethodInfo restartRun =
        typeof(PausePopup)
            .GetMethod("_onResetButtonClick", BindingFlags.NonPublic | BindingFlags.Instance);

    static UnityEngine.Object[] Find(Type type) {
        return UnityEngine.Object.FindObjectsOfType(type);
    }

    static bool Active(Behaviour b) {
        return b && b.enabled && b.gameObject.activeInHierarchy;
    }

    static void Click(Component b) {
        b.SendMessage("OnMouseDown", SendMessageOptions.DontRequireReceiver);
    }

    // Pick one visible target using the real camera, independently of resolution.
    static Component Target(Type type, int side) {
        Camera cam = Camera.main;
        if (!cam)
            return null;
        Component best = null;
        float score = 1000000;
        foreach (UnityEngine.Object o in Find(type)) {
            Behaviour b = o as Behaviour;
            if (!Active(b))
                continue;
            if (b is FlyingBird && birdTapped != null && (bool)birdTapped.GetValue(b))
                continue;
            Vector3 p = cam.WorldToViewportPoint(b.transform.position);
            if (p.z <= 0 || p.x < 0 || p.x > 1 || p.y < 0 || p.y > 1)
                continue;
            if ((side < 0 && p.x >= .5f) || (side > 0 && p.x < .5f))
                continue;
            float d = (p.x - .5f) * (p.x - .5f) + (p.y - .5f) * (p.y - .5f);
            if (d < score) {
                best = b;
                score = d;
            }
        }
        return best;
    }

    public static int Tick(int down, int held) {
        if ((down & Restart) != 0) {
            nextTap = 0;
            // Use the pause menu's exact handler: restore time, stop recording,
            // reload this scene. It does not clear saves or start a new game.
            foreach (UnityEngine.Object o in Find(typeof(InGameGUI))) {
                InGameGUI gui = (InGameGUI)o;
                if (!Active(gui) || !gui.pausePopup || restartRun == null)
                    continue;
                restartRun.Invoke(gui.pausePopup, new object[] { gui.pausePopup.resetButton });
                break;
            }
            return 0;
        }
        if ((held & Restart) != 0)
            return 0;
        bool tap = (down & B) != 0;
        float now = Time.realtimeSinceStartup;
        if ((held & B) != 0 && now >= nextTap)
            tap = true;
        if (tap)
            nextTap = now + .10f;
        if ((held & B) == 0)
            nextTap = 0;
        // A normal Fire1 tap can dismiss tutorials which pause time.
        if (Time.timeScale == 0)
            return tap ? 1 : 0;
        if ((down & (Kick | Recovery)) != 0) {
            foreach (UnityEngine.Object o in Find(typeof(InGameGUI))) {
                InGameGUI gui = (InGameGUI)o;
                if (!Active(gui))
                    continue;
                ActionIcon icon = (down & Kick) != 0 ? gui.kickIcon : gui.bounceIcon;
                CommonButton button =
                    icon ? icon.GetComponent(typeof(CommonButton)) as CommonButton : null;
                if (Active(button))
                    Click(button);
                if ((down & (Kick | Recovery)) == (Kick | Recovery) && gui.bounceIcon) {
                    button = gui.bounceIcon.GetComponent(typeof(CommonButton)) as CommonButton;
                    if (Active(button))
                        Click(button);
                }
            }
        }
        if ((down & Left) != 0) {
            Component p = Target(typeof(EnemyLifeChecker), -1);
            if (p)
                Click(p);
        }
        if ((down & Right) != 0) {
            Component p = Target(typeof(EnemyLifeChecker), 1);
            if (p)
                Click(p);
        }
        if (!tap)
            return 0;
        foreach (UnityEngine.Object o in Find(typeof(PowerCharger))) {
            PowerCharger p = (PowerCharger)o;
            if (Active(p)) {
                // Launch timing takes two distinct presses, as on touch.
                if ((down & B) != 0)
                    Click(p);
                return 0;
            }
        }
        foreach (UnityEngine.Object o in Find(typeof(IceRider))) {
            IceRider ice = (IceRider)o;
            if (Active(ice)) {
                Click(ice);
                return 0;
            }
        }
        foreach (UnityEngine.Object o in Find(typeof(BirdsRider))) {
            if (Active((BirdsRider)o)) {
                Component bird = Target(typeof(FlyingBird), 0);
                if (bird)
                    Click(bird);
                return 0;
            }
        }
        // CometRider and RainicornRider use Input.GetButtonDown("Fire1").
        // The native host supplies a down/up over separate game frames.
        return 1;
    }
}
