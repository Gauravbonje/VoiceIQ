import json
from pathlib import Path

def save_words(words, path="data/transcripts/words.json"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(words, f)

def load_words(path="data/transcripts/words.json"):
    with open(path, "r") as f:
        return json.load(f)