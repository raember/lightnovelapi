from pbincli.format import Paste
from urllib3.util import Url


def decrypt(url: Url, json_data: dict) -> str:
    p = Paste()
    p.setVersion(json_data.get('v', 1))
    p.setHash(url.fragment)
    p.loadJSON(json_data)
    p.decrypt()
    return p.getText().decode('utf8')
