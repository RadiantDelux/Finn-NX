using System;
using UnityEngine;

class ControlsChecks {
    static int count;

    static void Check(bool ok, string message) {
        if (!ok)
            throw new Exception(message);
        count++;
    }

    static void Reset() {
        UnityEngine.Object.Objects.Clear();
        Time.timeScale = 1;
        Time.realtimeSinceStartup += 10;
        Camera.main = new Camera();
        FinnControls.Tick(0, 0);
    }
    static T At<T>(float x, float y, float z)
        where T : Component, new() {
        T o = new T();
        o.transform.position = new Vector3(x, y, z);
        return o;
    }

    static void Main() {
        Reset();
        InGameGUI gui = new InGameGUI();
        gui.kickIcon = new ActionIcon();
        gui.bounceIcon = new ActionIcon();
        CommonButton kick = new CommonButton(), bounce = new CommonButton();
        gui.kickIcon.Components[typeof(CommonButton)] = kick;
        gui.bounceIcon.Components[typeof(CommonButton)] = bounce;
        FinnControls.Tick(3, 3);
        Check(kick.Clicks == 1 && bounce.Clicks == 1, "simultaneous X/Y lost");
        bounce.enabled = false;
        FinnControls.Tick(2, 2);
        Check(bounce.Clicks == 1, "disabled recovery button bypassed");
        Time.timeScale = 0;
        FinnControls.Tick(3, 3);
        Check(kick.Clicks == 1, "pause ignored");
        Reset();
        EnemyLifeChecker l = At<EnemyLifeChecker>(.2f, .5f, 1),
                         r = At<EnemyLifeChecker>(.8f, .5f, 1);
        EnemyLifeChecker off = At<EnemyLifeChecker>(-.1f, .5f, 1),
                         behind = At<EnemyLifeChecker>(.3f, .5f, -1);
        FinnControls.Tick(8, 8);
        Check(l.Clicks == 1 && r.Clicks == 0, "left target wrong");
        FinnControls.Tick(16, 16);
        Check(r.Clicks == 1, "right target wrong");
        FinnControls.Tick(24, 24);
        Check(off.Clicks == 0 && behind.Clicks == 0, "invisible target clicked");
        Reset();
        PowerCharger p = new PowerCharger();
        Check(FinnControls.Tick(4, 4) == 0 && p.State == 1, "initial launch did not start gauge");
        Time.realtimeSinceStartup += 1;
        FinnControls.Tick(0, 4);
        Check(p.State == 1, "holding B stopped launch gauge");
        FinnControls.Tick(0, 0);
        FinnControls.Tick(4, 4);
        Check(p.State == 2, "second B did not stop gauge");
        Reset();
        Check(FinnControls.Tick(4, 4) == 1, "Fire1 pulse missing");
        Time.realtimeSinceStartup += .02f;
        Check(FinnControls.Tick(0, 4) == 0, "repeat too fast");
        Time.realtimeSinceStartup += .11f;
        Check(FinnControls.Tick(0, 4) == 1, "held B did not repeat");
        Check(FinnControls.Tick(0, 0) == 0, "released B repeated");
        Reset();
        BirdsRider rider = new BirdsRider();
        FlyingBird b1 = At<FlyingBird>(.4f, .5f, 1), b2 = At<FlyingBird>(.8f, .5f, 1);
        FlyingBird hidden = At<FlyingBird>(1.1f, .5f, 1);
        Check(FinnControls.Tick(4, 4) == 0 && b1.Clicks == 1 && b2.Clicks == 0,
              "bird tap did not select one");
        Time.realtimeSinceStartup += .11f;
        FinnControls.Tick(0, 4);
        Check(b1.Clicks == 1 && b2.Clicks == 1 && hidden.Clicks == 0,
              "bird repeat did not skip tapped/invisible");
        Reset();
        IceRider ice = new IceRider();
        Check(FinnControls.Tick(4, 4) == 0 && ice.Clicks == 1, "ice tap missing");
        Reset();
        gui = new InGameGUI();
        PausePopup pause = new PausePopup();
        gui.pausePopup = pause;
        Check(FinnControls.Tick(32, 32) == 0 && pause.Restarts == 1,
              "minus did not call the original reset handler");
        FinnControls.Tick(0, 32);
        Check(pause.Restarts == 1, "holding minus repeated restart");
        Time.timeScale = 0;
        FinnControls.Tick(32, 32);
        Check(pause.Restarts == 2 && Time.timeScale == 1, "restart did not work while paused");
        pause.IsAnimating = true;
        FinnControls.Tick(32, 32);
        Check(pause.Restarts == 2, "reset animation guard bypassed");
        pause.IsAnimating = false;
        gui.enabled = false;
        FinnControls.Tick(32, 32);
        Check(pause.Restarts == 2, "disabled gameplay restarted");
        gui.enabled = true;
        gui.pausePopup = null;
        Check(FinnControls.Tick(32, 32) == 0, "missing reset popup failed");
        Reset();
        Check(FinnControls.Tick(32, 32) == 0, "minus outside a run injected a tap");
        gui = new InGameGUI();
        gui.pausePopup = pause = new PausePopup();
        p = new PowerCharger();
        Check(FinnControls.Tick(32 | 4, 32 | 4) == 0 && pause.Restarts == 1 && p.State == 0,
              "restart also launched Finn");
        Reset();
        gui = new InGameGUI();
        gui.kickIcon = new ActionIcon();
        gui.bounceIcon = new ActionIcon();
        kick = new CommonButton();
        bounce = new CommonButton();
        gui.kickIcon.Components[typeof(CommonButton)] = kick;
        gui.bounceIcon.Components[typeof(CommonButton)] = bounce;
        FinnControls.Tick(1, 1);
        Check(kick.Clicks == 1 && bounce.Clicks == 0, "kick action also triggered recovery");
        FinnControls.Tick(2, 2);
        Check(kick.Clicks == 1 && bounce.Clicks == 1, "recovery action also triggered kick");
        Console.WriteLine("PASS: " + count + " controls checks; Unity and game handlers modeled");
    }
}
