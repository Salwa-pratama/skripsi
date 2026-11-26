#pragma once

#include <atomic>
#include <functional>
#include <mutex>
#include <vector>
#include "device_state.h"

class DeviceStateMachine {
public:
    DeviceStateMachine();
    ~DeviceStateMachine() = default;

    DeviceStateMachine(const DeviceStateMachine&) = delete;
    DeviceStateMachine& operator=(const DeviceStateMachine&) = delete;

    DeviceState GetState() const { return current_state_.load(); }
    bool TransitionTo(DeviceState new_state);
    bool CanTransitionTo(DeviceState target) const;
    static const char* GetStateName(DeviceState state);

    using StateCallback = std::function<void(DeviceState old_state, DeviceState new_state)>;
    void AddStateChangeListener(StateCallback callback);

private:
    std::atomic<DeviceState> current_state_{kDeviceStateUnknown};
    mutable std::mutex mutex_;
    std::vector<StateCallback> callbacks_;

    bool IsValidTransition(DeviceState from, DeviceState to) const;
};
