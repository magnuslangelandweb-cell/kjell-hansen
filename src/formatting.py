"""Light post-processing safety net on top of Whisper's own punctuation/casing."""

_TERMINAL_PUNCTUATION = (".", "!", "?", ":", ";", ",", '"', "'")


def clean_transcript(text: str) -> str:
    text = text.strip()
    if not text:
        return text

    text = text[0].upper() + text[1:]

    if not text.endswith(_TERMINAL_PUNCTUATION):
        text += "."

    return text
