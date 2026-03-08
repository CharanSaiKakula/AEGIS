# flight_ops — Tello Person-Following Autonomy

Autonomy stack for a DJI Tello person-following project.

## Package layout

```
flight_ops/
├── core/                # Core system orchestration
│   ├── mission_manager.py
│   └── behavior_manager.py
├── decision/            # MDP / decision logic
│   └── mdp_policy.py
├── control/             # High-level control laws
│   └── controller.py
├── perception/          # Interfaces to perception
│   ├── extractor_interface.py
│   └── state_extractor.py
├── safety/              # Safety guardrails
│   └── safety_guard.py
├── config/              # Config + shared types
│   ├── config.py
│   └── types.py
├── utils/
│   └── debug.py
├── main.py              # Entry point
└── README.md
``` It runs **above** the Tello firmware: no low-level attitude or motor control, only high-level commands (e.g. `send_control(lr, fb, ud, yaw)`) -- `left-right, forward-back, up-down, yaw`.

## System overview

Computer vision runs on a ground station and gives filtered measurements each tick:

- **x_error, y_error** — target offset in the image
- **distance** — distance to the person
- **confidence** — detection confidence (0–1)

The autonomy pipeline:

1. **State extraction** — Turn raw measurement + telemetry into a discrete state (buckets like "near", "good", "far", "nominal", "critical").
2. **MDP-style policy** — Decide which high-level behavior to run (FOLLOW, SEARCH, HOVER, or LAND) from the discrete state.
3. **Behavior manager** — Map that behavior to a concrete intention (e.g. “use follow controller” or “hover”).
4. **Controller** — In FOLLOW mode, produce RC commands from the vision measurement (yaw, vertical, forward/back).
5. **Safety guardrails** — Check telemetry (battery, latency, altitude, link). If safety fails, **force LAND** and never leave.

The system **always starts in TAKEOFF** and **always ends in LAND**. **LAND is absorbing**: once the system enters LAND, it never transitions back to any other state.

## Why an MDP-inspired design?

We use a discrete state space and a policy that picks behaviors so that:

- The same structure can later be driven by a **real MDP** (e.g. value or policy iteration) instead of hand-written rules.
- The **policy only chooses among behaviors**; it does not override safety. Safety sits above the policy and can force LAND from any state.

So: think of the current rule-based policy as a **scaffold** for a future learned or computed MDP policy, while keeping safety separate and authoritative.

## Safety guardrails override the policy

Safety is **above** the MDP:

- **Safety runs first** every tick (battery, latency, altitude, link, optional mission time).
- If any safety condition fails → transition to **LAND** and stay there forever.
- The policy **cannot** take the system out of LAND. Once in LAND, the only “action” is to remain in LAND.

So: **safety is authoritative**; the policy only decides when it is safe to continue.

## LAND is absorbing

- From any state, safety can force a transition to **LAND**.
- Once in **LAND**, the mission never transitions to FOLLOW, SEARCH, HOVER, or TAKEOFF again.
- The mission manager enforces this so that no component (including the policy) can override a forced landing.

## Replacing the mock extractor with real CV

The **extractor** is the only place that talks to the CV pipeline:

1. Open **`perception/extractor_interface.py`**.
2. Replace the mock (e.g. `_mock_vision_provider()` or `MockExtractor`) with a call that returns a **`VisionMeasurement`** from your system (e.g. ROS topic, shared memory, or callback from your CV process).
3. Ensure that function is used wherever the autonomy loop gets the “current” measurement (e.g. in `mission_manager.step(...)` or your main loop).

The rest of the stack only sees `VisionMeasurement` and does not care where it came from.

## Connecting ControlCommand to a real Tello

The output of the autonomy stack is a **`ControlCommand`** with `lr`, `fb`, `ud`, `yaw` (integers, typically -100..100).

To fly a real Tello:

1. Each tick, call `manager.step(measurement, telemetry)` to get `(state, command, debug)`.
2. If `manager.request_takeoff()` is true, send your drone’s takeoff command once.
3. If `manager.request_land()` is true, send your drone’s land command once (and stop sending RC).
4. Otherwise, send the command to the Tello, e.g.:

   ```python
   from djitellopy import Tello
   tello = Tello()
   tello.connect()
   # ... in the loop:
   state, cmd, debug = manager.step(measurement, telemetry)
   tello.send_control(cmd.lr, cmd.fb, cmd.ud, cmd.yaw)
   ```

Use your real telemetry (battery, latency, altitude, link) to build the **`TelemetrySnapshot`** you pass into `step()`.

## Architecture 

```
                    +--------------------+
                    |  CV Extractor      |  (the cv pipeline)
                    |  VisionMeasurement |
                    +--------+-----------+
                             |
    +------------------------+------------------------+
    |                  MISSION MANAGER                 |
    |  (owns MissionState, runs pipeline each tick)    |
    +------------------------+------------------------+
                             |
    +--------+----------------+----------------+------+
    |        |                |                |      |
    v        v                v                v      v
+-------+  +-------------+  +--------+  +----------+  +----------+
|Safety |  |State        |  |MDP     |  |Behavior  |  |Controller|
|Guard  |->|Extractor    |->|Policy  |->|Manager   |->|(follow/  |
|       |  |DiscreteState|  |        |  |          |  |hover/    |
+-------+  +-------------+  +--------+  +----------+  |search)   |
   |             |                |            |       +----------+
   |             |                |            |            |
   |     (if safety fails)        |            |            v
   +-----------------------------> LAND (absorbing)   ControlCommand
```

- **Safety** can force **LAND** from any state; once in LAND, the system never leaves.
- **State extractor** turns measurement + telemetry into **DiscreteState**.
- **Policy** chooses next **MissionState** (FOLLOW / SEARCH / HOVER / LAND).
- **Behavior manager** maps state to “use follow controller” / “hover” / “search” / “land”.
- **Controller** produces the actual **ControlCommand** for the Tello.
