#pragma once

#include <string>
#include <functional>
#include <freertos/FreeRTOS.h>
#include <freertos/event_groups.h>
#include <esp_wifi.h>
#include <esp_event.h>
#include <esp_netif.h>

class WifiManager {
public:
    static WifiManager& GetInstance();

    bool Initialize();
    bool Connect(const std::string& ssid, const std::string& password, uint32_t timeout_ms = 15000);
    void StartNetwork(const std::string& ssid, const std::string& password);
    void Disconnect();

    bool IsConnected() const { return connected_; }
    std::string GetIpAddress() const { return ip_address_; }
    int GetRssi() const;

    void SetConnectedCallback(std::function<void(const std::string& ip)> cb) {
        on_connected_ = std::move(cb);
    }
    void SetDisconnectedCallback(std::function<void()> cb) {
        on_disconnected_ = std::move(cb);
    }

private:
    WifiManager() = default;
    ~WifiManager();
    WifiManager(const WifiManager&) = delete;
    WifiManager& operator=(const WifiManager&) = delete;

    static void WifiEventHandler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data);

    EventGroupHandle_t event_group_ = nullptr;
    esp_netif_t* sta_netif_ = nullptr;
    esp_event_handler_instance_t instance_any_id_ = nullptr;
    esp_event_handler_instance_t instance_got_ip_ = nullptr;

    bool initialized_ = false;
    bool wifi_started_ = false;
    bool connected_ = false;
    std::string current_ssid_;
    std::string current_password_;
    std::string ip_address_;
    int retry_count_ = 0;

    std::function<void(const std::string& ip)> on_connected_;
    std::function<void()> on_disconnected_;
};
