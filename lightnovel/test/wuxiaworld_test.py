import unittest
from lightnovel.test.test_config import mock_request, load_har
from lightnovel.wuxiaworld import *


class HJCWuxiaWorldApiTest(unittest.TestCase):
    HJC = load_har('SearchHJC_p13_WW235_WWCover_WWC1')

    def mock_request_hjc(self, method: str, url: str, **kwargs):
        return mock_request(method, url, self.HJC)

    def test_parsing_novel_hjc(self):
        novel = WuxiaWorldApi(self.mock_request_hjc).get_novel('heavenly-jewel-change')
        self.assertIsNotNone(novel)
        self.assertEqual(novel.title, 'Heavenly Jewel Change')
        self.assertEqual(novel.translator, 'Stardu5t')
        self.assertEqual(novel.first_chapter_url, 'https://www.wuxiaworld.com/novel/heavenly-jewel-change/hjc-book-1'
                                                  '-chapter-1-01')
        self.assertListEqual(novel.tags, ['Chinese', 'Ongoing'])
        self.assertEqual(novel.img_url, 'https://cdn.wuxiaworld.com/images/covers/hjc.jpg?ver'
                                        '=f83790a5f2ff64bb6524c2cfd207845ba1d25ac6')
        self.assertEqual(novel.url, 'https://www.wuxiaworld.com/novel/heavenly-jewel-change')
        self.assertEqual(novel.description_html.text, "\n[Zen’s Synopsis]In a world where power means everything, "
                                                      "and the strong trample the weak; there was a boy born from a "
                                                      "Heavenly Jewel Master. Born in a small country which had to "
                                                      "struggle to survive, the boy was expected to do great things. "
                                                      "Alas he turned out to have blocked meridians and was unable to "
                                                      "cultivate, ending up the trash of society. His father’s "
                                                      "tarnished pride… his fianceé’s ultimate dishonour…Being almost "
                                                      "accidentally killed and left for the dead, heaven finally "
                                                      "smiles upon him as a miracle descends, awakening his potential "
                                                      "as a Heavenly Jewel Master. Or… is it truly a gift?Join our "
                                                      "dear rascally and shameless MC Zhou Weiqing in his exploits to "
                                                      "reach the peak of the cultivation world, form an army, "
                                                      "protect those he loves, and improve his country!An all new "
                                                      "world, an all new power system, unique weaponry & MC! Come "
                                                      "join me in laughing and crying together with this new "
                                                      "masterpiece from Tang Jia San Shao![Translated Synopsis]Every "
                                                      "human has their Personal Jewel of power, when awakened it can "
                                                      "either be an Elemental Jewel or Physical Jewel. They circle "
                                                      "the right and left wrists like bracelets of power.Heavenly "
                                                      "Jewels are like the twins born, meaning when both Elemental "
                                                      "and Physical Jewels are Awakened for the same person, "
                                                      "the pair is known as Heavenly Jewels.Those who have the "
                                                      "Physical Jewels are known as Physical Jewel Masters, "
                                                      "those with Elemental Jewels are Elemental Jewel Masters, "
                                                      "and those who train with Heavenly Jewels are naturally called "
                                                      "Heavenly Jewel Masters.Heavenly Jewel Masters have a highest "
                                                      "level of 12 pairs of jewels, as such their training progress "
                                                      "is known as Heavenly Jewels 12 Changes.Our MC here is an "
                                                      "archer who has such a pair of Heavenly Jewels.\n"
                         )
        self.assertEqual(len(novel.books), 7)
        book = novel.books[0]
        self.assertEqual(book.title, 'Volume 1')
        self.assertEqual(len(book.chapters), 27)
        chapter = book.chapters[0]
        self.assertEqual(chapter.title, 'Chapter 1 Big Sis, Im afraid this is a misunderstanding! (1)')
        self.assertEqual(chapter.url, 'https://www.wuxiaworld.com/novel/heavenly-jewel-change/hjc-book-1-chapter-1-01')
        book = novel.books[1]
        self.assertEqual(book.title, 'Volume 2')
        self.assertEqual(len(book.chapters), 29)
        book = novel.books[2]
        self.assertEqual(book.title, 'Volume 3')
        self.assertEqual(len(book.chapters), 28)
        book = novel.books[3]
        self.assertEqual(book.title, 'Volume 4')
        self.assertEqual(len(book.chapters), 13)
        book = novel.books[4]
        self.assertEqual(book.title, 'Volume 5')
        self.assertEqual(len(book.chapters), 31)
        book = novel.books[5]
        self.assertEqual(book.title, 'Volume 6')
        self.assertEqual(len(book.chapters), 55)
        book = novel.books[6]
        self.assertEqual(book.title, 'Remaining Chapters (To be sorted)')
        self.assertEqual(len(book.chapters), 694)

    def test_parsing_hjc_description_as_string(self):
        novel = WuxiaWorldApi(self.mock_request_hjc).get_novel('heavenly-jewel-change')
        self.assertEqual(novel.description_str(), """[Zen’s Synopsis]
In a world where power means everything, and the strong trample the weak; there was a boy born from a Heavenly Jewel Master. Born in a small country which had to struggle to survive, the boy was expected to do great things. Alas he turned out to have blocked meridians and was unable to cultivate, ending up the trash of society. His father’s tarnished pride… his fianceé’s ultimate dishonour…
Being almost accidentally killed and left for the dead, heaven finally smiles upon him as a miracle descends, awakening his potential as a Heavenly Jewel Master. Or… is it truly a gift?
Join our dear rascally and shameless MC Zhou Weiqing in his exploits to reach the peak of the cultivation world, form an army, protect those he loves, and improve his country!
An all new world, an all new power system, unique weaponry & MC! Come join me in laughing and crying together with this new masterpiece from Tang Jia San Shao!
[Translated Synopsis]
Every human has their Personal Jewel of power, when awakened it can either be an Elemental Jewel or Physical Jewel. They circle the right and left wrists like bracelets of power.
Heavenly Jewels are like the twins born, meaning when both Elemental and Physical Jewels are Awakened for the same person, the pair is known as Heavenly Jewels.
Those who have the Physical Jewels are known as Physical Jewel Masters, those with Elemental Jewels are Elemental Jewel Masters, and those who train with Heavenly Jewels are naturally called Heavenly Jewel Masters.
Heavenly Jewel Masters have a highest level of 12 pairs of jewels, as such their training progress is known as Heavenly Jewels 12 Changes.
Our MC here is an archer who has such a pair of Heavenly Jewels.""")

    def test_parsing_hjc_description_as_markdown(self):
        novel = WuxiaWorldApi(self.mock_request_hjc).get_novel('heavenly-jewel-change')
        self.assertEqual(novel.description_md(), """*[Zen’s Synopsis]*

In a world where power means everything, and the strong trample the weak; there was a boy born from a Heavenly Jewel Master. Born in a small country which had to struggle to survive, the boy was expected to do great things. Alas he turned out to have blocked meridians and was unable to cultivate, ending up the trash of society. His father’s tarnished pride… his fianceé’s ultimate dishonour…

Being almost accidentally killed and left for the dead, heaven finally smiles upon him as a miracle descends, awakening his potential as a Heavenly Jewel Master. Or… is it truly a gift?

Join our dear rascally and shameless MC Zhou Weiqing in his exploits to reach the peak of the cultivation world, form an army, protect those he loves, and improve his country!

An all new world, an all new power system, unique weaponry & MC! Come join me in laughing and crying together with this new masterpiece from Tang Jia San Shao!

---

*[Translated Synopsis]*

Every human has their Personal Jewel of power, when awakened it can either be an Elemental Jewel or Physical Jewel. They circle the right and left wrists like bracelets of power.

Heavenly Jewels are like the twins born, meaning when both Elemental and Physical Jewels are Awakened for the same person, the pair is known as Heavenly Jewels.

Those who have the Physical Jewels are known as Physical Jewel Masters, those with Elemental Jewels are Elemental Jewel Masters, and those who train with Heavenly Jewels are naturally called Heavenly Jewel Masters.

Heavenly Jewel Masters have a highest level of 12 pairs of jewels, as such their training progress is known as Heavenly Jewels 12 Changes.

Our MC here is an archer who has such a pair of Heavenly Jewels.""")
