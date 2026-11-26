#include "wifi_manager.h"
#include <esp_log.h>
#include <cstring>

#define TAG "WifiManager"

static constexpr int WIFI_CONNECTED_BIT = BIT0;
static constexpr int WIFI_FAIL_BIT      = BIT1;
static constexpr int MAX_RETRY_COUNT    = 10;

WifiManager& WifiManager::GetInstance() {
    static WifiManager instance;
    return instance;
}

WifiManager::~WifiManager() {
    Disconnect();
    if (event_group_) {
        vEventGroupDelete(event_group_);
    }
}

bool WifiManager::Initialize() {
    if (initialized_) return true;

    event_group_ = xEventGroupCreate();
    if (!event_group_) {
        ESP_LOGE(TAG, "Failed to create FreeRTOS event group!");
        return false;
    }

    ESP_ERROR_CHECK(esp_netif_init());
    esp_err_t err = esp_event_loop_create_default();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "Failed to create default event loop: %s", esp_err_to_name(err));
        return false;
    }

    sta_netif_ = esp_netif_create_default_wifi_sta();
    if (!sta_netif_) {
        ESP_LOGE(TAG, "Failed to create default WiFi STA netif!");
        return false;
    }

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        WIFI_EVENT,
        ESP_EVENT_ANY_ID,
        &WifiManager::WifiEventHandler,
        this,
        &instance_any_id_));

    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        IP_EVENT,
        IP_EVENT_STA_GOT_IP,
        &WifiManager::WifiEventHandler,
        this,
        &instance_got_ip_));

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));

    initialized_ = true;
    ESP_LOGI(TAG, "WiFi Station subsystem initialized successfully.");
    return true;
}

void WifiManager::StartNetwork(const std::string& ssid, const std::string& password) {
    if (!initialized_ && !Initialize()) {
        return;
    }

    current_ssid_ = ssid;
    current_password_ = password;
    connected_ = false;
    retry_count_ = 0;
    xEventGroupClearBits(event_group_, WIFI_CONNECTED_BIT | WIFI_FAIL_BIT);

    wifi_config_t wifi_config = {};
    strncpy((char*)wifi_config.sta.ssid, ssid.c_str(), sizeof(wifi_config.sta.ssid) - 1);
    strncpy((char*)wifi_config.sta.password, password.c_str(), sizeof(wifi_config.sta.password) - 1);
    // Terima mode autentikasi WPA/WPA2/WPA3 apa pun agar fleksibel
    wifi_config.sta.threshold.authmode = WIFI_AUTH_OPEN;
    wifi_config.sta.pmf_cfg.capable = true;
    wifi_config.sta.pmf_cfg.required = false;

    ESP_LOGI(TAG, "Memulai koneksi WiFi ke SSID: '%s' (Asinkron)...", ssid.c_str());
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));

    if (!wifi_started_) {
        ESP_ERROR_CHECK(esp_wifi_start());
        wifi_started_ = true;
    } else {
        esp_wifi_connect();
    }
}

bool WifiManager::Connect(const std::string& ssid, const std::string& password, uint32_t timeout_ms) {
    StartNetwork(ssid, password);

    EventBits_t bits = xEventGroupWaitBits(
        event_group_,
        WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
        pdFALSE,
        pdFALSE,
        pdMS_TO_TICKS(timeout_ms));

    return (bits & WIFI_CONNECTED_BIT) != 0;
}

void WifiManager::Disconnect() {
    if (connected_) {
        esp_wifi_disconnect();
        connected_ = false;
        ip_address_.clear();
    }
}

int WifiManager::GetRssi() const {
    if (!connected_) return 0;
    wifi_ap_record_t ap_info;
    if (esp_wifi_sta_get_ap_info(&ap_info) == ESP_OK) {
        return ap_info.rssi;
    }
    return 0;
}

void WifiManager::WifiEventHandler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data) {
    auto* self = static_cast<WifiManager*>(arg);

    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        ESP_LOGI(TAG, "WiFi Station dimulai, memanggil esp_wifi_connect()...");
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        auto* disconn = static_cast<wifi_event_sta_disconnected_t*>(event_data);
        self->connected_ = false;
        ESP_LOGW(TAG, "WiFi terputus, alasan: %d (0x%x)", disconn->reason, disconn->reason);

        if (self->retry_count_ < MAX_RETRY_COUNT) {
            self->retry_count_++;
            ESP_LOGI(TAG, "Mencoba menghubungkan ulang ke AP (Percobaan %d/%d)...",
                     self->retry_count_, MAX_RETRY_COUNT);
            esp_wifi_connect();
        } else {
            ESP_LOGW(TAG, "Batas percobaan koneksi tercapai. Sistem tetap jalan dalam standby.");
            xEventGroupSetBits(self->event_group_, WIFI_FAIL_BIT);
            if (self->on_disconnected_) {
                self->on_disconnected_();
            }
        }
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        auto* event = static_cast<ip_event_got_ip_t*>(event_data);
        char ip_str[32];
        esp_ip4addr_ntoa(&event->ip_info.ip, ip_str, sizeof(ip_str));
        self->ip_address_ = ip_str;
        self->connected_ = true;
        self->retry_count_ = 0;

        // Daya pancar seimbang 17 dBm (68) agar stabil & tidak memicu brownout USB
        esp_wifi_set_max_tx_power(68);
        esp_wifi_set_ps(WIFI_PS_MIN_MODEM);

        ESP_LOGI(TAG, "WiFi Terhubung! IP: %s (TxPower: 17 dBm, PowerSave: MinModem)", self->ip_address_.c_str());

        xEventGroupSetBits(self->event_group_, WIFI_CONNECTED_BIT);

        if (self->on_connected_) {
            self->on_connected_(self->ip_address_);
        }
    }
}
