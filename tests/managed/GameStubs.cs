using UnityEngine;

public class ActionIcon : MonoBehaviour {}

public class CommonButton : MonoBehaviour {
    public int Clicks;

    void OnMouseDown() {
        if (enabled)
            Clicks++;
    }
}

public class InGameGUI : MonoBehaviour {
    public ActionIcon kickIcon, bounceIcon;
    public PausePopup pausePopup;
}

public class PausePopup : MonoBehaviour {
    public CommonButton resetButton = new CommonButton();
    public bool IsAnimating;
    public int Restarts;

    void _onResetButtonClick(CommonButton button) {
        if (IsAnimating)
            return;
        Time.timeScale = 1;
        Restarts++;
    }
}

public class EnemyLifeChecker : MonoBehaviour {
    public int Clicks;

    void OnMouseDown() {
        if (enabled) {
            Clicks++;
            enabled = false;
        }
    }
}

public class FlyingBird : MonoBehaviour {
    bool tapped;
    public int Clicks;

    void OnMouseDown() {
        if (!tapped) {
            Clicks++;
            tapped = true;
        }
    }
}

public class PowerCharger : MonoBehaviour {
    public int State;

    void OnMouseDown() {
        if (State < 2)
            State++;
    }
}

public class IceRider : MonoBehaviour {
    public int Clicks;

    void OnMouseDown() {
        Clicks++;
    }
}

public class BirdsRider : MonoBehaviour {}
