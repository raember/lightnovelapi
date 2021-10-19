import json
import shutil
import zlib
from base64 import b64encode, b64decode
from pathlib import Path

from Crypto.Cipher import AES
from pbincli.format import Paste
from pbincli.utils import PBinCLIError
from urllib3.util import Url


class KeyCachedPaste(Paste):
    _keys: dict[str, str]
    _key_file: Path
    _tmp_key_file: Path

    def __init__(self, keys: dict[str, str] = None, key_file: str = 'privatebin.keys'):
        super(KeyCachedPaste, self).__init__()
        self._key_file = Path(key_file)
        self._tmp_key_file = self._key_file.with_name(f"{self._key_file.name}.tmp")
        if keys is None or len(keys) == 0:
            if self._key_file.exists():
                with open(self._key_file, 'r') as fp:
                    keys = json.load(fp)
            else:
                keys = {}
        self._keys = keys

    @property
    def keys(self) -> dict[str, str]:
        return self._keys

    def _decryptV2(self):
        from json import loads as json_decode
        iv = b64decode(self._data['adata'][0][0])
        salt = b64decode(self._data['adata'][0][1])

        self._iteration_count = self._data['adata'][0][2]
        self._block_bits = self._data['adata'][0][3]
        self._tag_bits = self._data['adata'][0][4]
        cipher_tag_bytes = int(self._tag_bits / 8)

        keyb64 = self._keys.get(self._data['id'], None)
        if keyb64 is None:
            key = self.__deriveKey(salt)
            self._keys[self._data['id']] = b64encode(key).decode()
            with open(self._tmp_key_file, 'w') as fp:
                json.dump(self._keys, fp, indent=4)
            shutil.copyfile(self._tmp_key_file, self._key_file)
        else:
            key = b64decode(keyb64)

        # Get compression type from received paste
        self._compression = self._data['adata'][0][7]

        cipher = self.__initializeCipher(key, iv, self._data['adata'], cipher_tag_bytes)
        # Cut the cipher text into message and tag
        cipher_text_tag = b64decode(self._data['ct'])
        cipher_text = cipher_text_tag[:-cipher_tag_bytes]
        cipher_tag = cipher_text_tag[-cipher_tag_bytes:]
        cipher_message = json_decode(self.__decompress(cipher.decrypt_and_verify(cipher_text, cipher_tag)).decode())

        self._text = cipher_message['paste'].encode()

        if 'attachment' in cipher_message and 'attachment_name' in cipher_message:
            self._attachment = cipher_message['attachment']
            self._attachment_name = cipher_message['attachment_name']

    def __deriveKey(self, salt):
        from Crypto.Protocol.KDF import PBKDF2
        from Crypto.Hash import HMAC, SHA256

        # Key derivation, using PBKDF2 and SHA256 HMAC
        return PBKDF2(
            self._key + self._password.encode(),
            salt,
            dkLen=int(self._block_bits / 8),
            count=self._iteration_count,
            prf=lambda password, salt: HMAC.new(
                password,
                salt,
                SHA256
            ).digest())

    @classmethod
    def __initializeCipher(self, key, iv, adata, tagsize):
        from pbincli.utils import json_encode

        cipher = AES.new(key, AES.MODE_GCM, nonce=iv, mac_len=tagsize)
        cipher.update(json_encode(adata))
        return cipher

    def __decompress(self, s):
        if self._version == 2 and self._compression == 'zlib':
            # decompress data
            return zlib.decompress(s, -zlib.MAX_WBITS)
        elif self._version == 2 and self._compression == 'none':
            # nothing to do, just return original data
            return s
        elif self._version == 1:
            return zlib.decompress(bytearray(map(lambda c: ord(c) & 255, b64decode(s.encode('utf-8')).decode('utf-8'))),
                                   -zlib.MAX_WBITS)
        else:
            PBinCLIError('Unknown compression type provided in paste!')

    def __compress(self, s):
        if self._version == 2 and self._compression == 'zlib':
            # using compressobj as compress doesn't let us specify wbits
            # needed to get the raw stream without headers
            co = zlib.compressobj(wbits=-zlib.MAX_WBITS)
            return co.compress(s) + co.flush()
        elif self._version == 2 and self._compression == 'none':
            # nothing to do, just return original data
            return s
        elif self._version == 1:
            co = zlib.compressobj(wbits=-zlib.MAX_WBITS)
            b = co.compress(s) + co.flush()
            return b64encode(''.join(map(chr, b)).encode('utf-8'))
        else:
            PBinCLIError('Unknown compression type provided!')


def decrypt(url: Url, json_data: dict, keys: dict[str, str] = None) -> tuple[str, dict[str, str]]:
    p = KeyCachedPaste(keys)
    p.setVersion(json_data.get('v', 1))
    p.setHash(url.fragment)
    p.loadJSON(json_data)
    p.decrypt()
    return p.getText().decode('utf8'), p.keys
