#pragma once

#include "board.h"
#include "board_pins.h"
#include "audio/codecs/no_audio_codec.h"
#include "led/single_led.h"

class AsistenBelajarBoard : public Board {
public:
    AsistenBelajarBoard();
    virtual ~AsistenBelajarBoard();

    virtual std::string GetBoardType() const override { return "asisten-belajar-s3"; }
    virtual AudioCodec* GetAudioCodec() override;
    virtual SingleLed* GetLed() override;
    virtual void Initialize() override;

    void SetAmplifierPower(bool enable);

private:
    NoAudioCodecDuplex* audio_codec_ = nullptr;
    SingleLed* led_ = nullptr;
    bool amp_enabled_ = false;

    void InitializeGpio();
};
