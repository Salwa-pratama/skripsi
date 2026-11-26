#pragma once

#include "audio_codec.h"
#include <driver/gpio.h>
#include <mutex>

class NoAudioCodec : public AudioCodec {
public:
    virtual ~NoAudioCodec();

    virtual int Write(const int16_t* data, int samples) override;
    virtual int Read(int16_t* dest, int samples) override;
    virtual void EnableInput(bool enable) override;
    virtual void EnableOutput(bool enable) override;

protected:
    std::mutex data_if_mutex_;
};

// Mode Full-Duplex (Clock BCLK & Word-Select WS dipakai bersama antara MAX98357A & INMP441)
class NoAudioCodecDuplex : public NoAudioCodec {
public:
    NoAudioCodecDuplex(int input_sample_rate, int output_sample_rate,
                       gpio_num_t bclk, gpio_num_t ws, gpio_num_t dout, gpio_num_t din);
};
