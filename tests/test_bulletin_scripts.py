import stat
from pathlib import Path


def test_bulletin_aprschat_script_contents():
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / 'tools' / 'bulletin-aprschat.sh'

    assert script.exists()
    assert script.stat().st_mode & stat.S_IXUSR

    lines = script.read_text().splitlines()
    send_lines = [line for line in lines if line.startswith('aprsd send-message -n')]

    assert send_lines == [
        'aprsd send-message -n BLN0 "APRS Chat now on Google Play Store!"',
        'aprsd send-message -n BLN1 "Install: https://tinyurl.com/APRSChat"',
        'aprsd send-message -n BLN2 "Android app for APRS chat and messaging"',
        'aprsd send-message -n BLN3 "Search Google Play for APRS Chat"',
    ]
