#include "device_state_machine.h"
#include <esp_log.h>

static const char* TAG = "StateMachine";

static const char* const STATE_STRINGS[] = {
    "unknown",
    "starting",
    "wifi_configuring",
    "idle",
    "connecting",
    "listening",
    "thinking",
    "speaking",
    "fatal_error",
    "invalid_state"
};

DeviceStateMachine::DeviceStateMachine() {
}

const char* DeviceStateMachine::GetStateName(DeviceState state) {
    if (state >= 0 && state <= kDeviceStateFatalError) {
        return STATE_STRINGS[state];
    }
    return STATE_STRINGS[kDeviceStateFatalError + 1];
}

bool DeviceStateMachine::IsValidTransition(DeviceState from, DeviceState to) const {
    if (from == to) {
        return true;
    }

    switch (from) {
        case kDeviceStateUnknown:
            return to == kDeviceStateStarting;

        case kDeviceStateStarting:
            return to == kDeviceStateIdle ||
                   to == kDeviceStateWifiConfiguring;

        case kDeviceStateWifiConfiguring:
            return to == kDeviceStateIdle;

        case kDeviceStateIdle:
            return to == kDeviceStateConnecting ||
                   to == kDeviceStateListening ||
                   to == kDeviceStateThinking ||
                   to == kDeviceStateSpeaking;

        case kDeviceStateConnecting:
            return to == kDeviceStateIdle ||
                   to == kDeviceStateListening;

        case kDeviceStateListening:
            return to == kDeviceStateThinking ||
                   to == kDeviceStateIdle;

        case kDeviceStateThinking:
            return to == kDeviceStateSpeaking ||
                   to == kDeviceStateListening ||
                   to == kDeviceStateIdle;

        case kDeviceStateSpeaking:
            return to == kDeviceStateListening ||
                   to == kDeviceStateIdle;

        case kDeviceStateFatalError:
            return false;

        default:
            return false;
    }
}

bool DeviceStateMachine::CanTransitionTo(DeviceState target) const {
    return IsValidTransition(current_state_.load(), target);
}

bool DeviceStateMachine::TransitionTo(DeviceState new_state) {
    DeviceState old_state = current_state_.load();
    if (old_state == new_state) {
        return true;
    }

    if (!IsValidTransition(old_state, new_state)) {
        ESP_LOGW(TAG, "Invalid state transition from %s to %s",
                 GetStateName(old_state), GetStateName(new_state));
        return false;
    }

    current_state_.store(new_state);
    ESP_LOGI(TAG, "State changed: %s -> %s",
             GetStateName(old_state), GetStateName(new_state));

    std::vector<StateCallback> callbacks_copy;
    {
        std::lock_guard<std::mutex> lock(mutex_);
        callbacks_copy = callbacks_;
    }

    for (const auto& callback : callbacks_copy) {
        callback(old_state, new_state);
    }

    return true;
}

void DeviceStateMachine::AddStateChangeListener(StateCallback callback) {
    std::lock_guard<std::mutex> lock(mutex_);
    callbacks_.push_back(std::move(callback));
}
