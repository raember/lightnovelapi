import unittest

from urllib3.util import parse_url

from lightnovel.util.privatebin import decrypt


class PrivateBinTest(unittest.TestCase):
    def test_decryption(self):
        url = parse_url('https://priv.atebin.com/?9af12b307e8459e2#eU/QA7Rr/Cv58AcPD+iD9ZSrw9/yjTLhe5zkSY03DU8=')
        response = {
            "status": 0,
            "id": "9af12b307e8459e2",
            "url": "/?9af12b307e8459e2?9af12b307e8459e2",
            "meta": {
                "expire_date": 1579108171,
                "formatter": "markdown",
                "postdate": 1578503371,
                "remaining_time": 604635
            },
            "data": "{\"iv\":\"woIeuoI5WA73h7+x83Usng==\",\"v\":1,\"iter\":10000,\"ks\":256,\"ts\":128,\"mode\":\"gcm\",\"adata\":\"\",\"cipher\":\"aes\",\"salt\":\"w/iPRrIwf3M=\",\"ct\":\"8RNNSM/luR0nM5WTWzQ7rP/RRbskm83M\"}",
            "comments": [],
            "comment_count": 0,
            "comment_offset": 0,
            "@context": "js/paste.jsonld"
        }
        self.assertEqual('test', decrypt(url, response))


if __name__ == '__main__':
    unittest.main()
