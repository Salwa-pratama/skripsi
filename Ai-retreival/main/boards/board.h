#pragma once

#include <string>
#include <cstdint>

class AudioCodec;
class SingleLed;

class Board {
public:
    virtual ~Board() = default;
    virtual std::string GetBoardType() const = 0;
    virtual AudioCodec* GetAudioCodec() = 0;
    virtual SingleLed* GetLed() = 0;
    virtual void Initialize() = 0;
};
