// Modeled Unity boundary for the real compiled FinnControls assembly.
using System;
using System.Collections.Generic;
using System.Reflection;

namespace UnityEngine {
public class Object {
    public static List<Object> Objects = new List<Object>();

    public Object() {
        Objects.Add(this);
    }

    public static implicit operator bool(Object o) {
        return !object.ReferenceEquals(o, null);
    }

    public static Object[] FindObjectsOfType(Type t) {
        return Objects.FindAll(delegate(Object o) { return t.IsInstanceOfType(o); }).ToArray();
    }
}

public struct Vector3 {
    public float x, y, z;

    public Vector3(float a, float b, float c) {
        x = a;
        y = b;
        z = c;
    }
}

public class Transform : Object {
    public Vector3 position { get; set; }
}

public class GameObject : Object {
    public bool activeInHierarchy { get; set; }

    public GameObject() {
        activeInHierarchy = true;
    }
}

public enum SendMessageOptions { RequireReceiver = 0, DontRequireReceiver = 1 }

public class Component : Object {
    public GameObject gameObject { get; set; }
    public Transform transform { get; set; }
    public Dictionary<Type, Component> Components = new Dictionary<Type, Component>();

    public Component() {
        gameObject = new GameObject();
        transform = new Transform();
    }

    public Component GetComponent(Type t) {
        return Components.ContainsKey(t) ? Components[t] : null;
    }

    public void SendMessage(string n, SendMessageOptions options) {
        MethodInfo m = GetType().GetMethod(n, BindingFlags.Instance | BindingFlags.Public |
                                                  BindingFlags.NonPublic);
        if (m != null)
            m.Invoke(this, null);
    }
}

public class Behaviour : Component {
    public bool enabled { get; set; }

    public Behaviour() {
        enabled = true;
    }
}

public class MonoBehaviour : Behaviour {}

public class Camera : Behaviour {
    public static Camera main { get; set; }

    public Vector3 WorldToViewportPoint(Vector3 p) {
        return p;
    }
}

public class Time {
    public static float realtimeSinceStartup { get; set; }
    public static float timeScale { get; set; }
}
}
