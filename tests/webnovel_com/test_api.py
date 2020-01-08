import logging
import unittest
from datetime import datetime

from urllib3.util import parse_url

from tests.config import prepare_browser, Har
from webnovel_com import WebNovelComApi, WebNovelComNovel, WebNovelComChapter

# noinspection SpellCheckingInspection
logging.getLogger('chardet.charsetprober').setLevel(logging.ERROR)


# noinspection DuplicatedCode,SpellCheckingInspection
class WuxiaWorldComApiRITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser = prepare_browser(Har.WM_SEARCH_RI_C1_5)
        cls.browser.navigate('https://www.webnovel.com/')  # Get the csrf cookie

    def test_search_RI(self):
        api = WebNovelComApi(self.browser)
        results = api.search('Renegade Immortal')
        self.assertIsNotNone(results)
        self.assertEqual(1, len(results))
        result = results[0]
        self.assertEqual('Renegade Immortal', result.title)
        self.assertEqual(8094127105005005, result.id)
        self.assertEqual('https://www.webnovel.com/book/8094127105005005', result.url.url)

    def test_parsing_novel(self):
        api = WebNovelComApi(self.browser)
        novel = api.get_novel(parse_url('https://www.webnovel.com/book/8094127105005005'))
        self.assertIsNotNone(novel)
        self.assertTrue(isinstance(novel, WebNovelComNovel))
        self.assertFalse(novel.success)
        novel.timestamp = datetime.fromtimestamp(1578354148.203)
        self.assertTrue(novel.parse())
        self.assertTrue(novel.success)
        self.assertEqual(8094127105005005, novel.novel_id)
        self.assertEqual('https://www.webnovel.com/book/8094127105005005', novel.alter_url().url)
        self.assertEqual('https://www.webnovel.com', novel.alter_url('').url)
        self.assertEqual('Renegade Immortal', novel.title)
        self.assertEqual('Er Gen', novel.author)
        self.assertEqual('Rex', novel.translator)
        self.assertEqual('© 2020 Webnovel', novel.rights)
        self.assertEqual(datetime.fromtimestamp(0), novel.release_date)
        self.assertEqual('/apiajax/chapter/GetContent'
                         '?_csrfToken=64nio7VwoiRDMT9sSOyrQFIQ9gWb1fQZxbIdqIpJ'
                         '&bookId=8094127105005005'
                         '&chapterId=21727507347361830'
                         '&_=1578354148203', novel.first_chapter.path)
        self.assertListEqual(['Cultivation', 'Weak to Strong'], novel.tags)

    def test_parsing_chapter(self):
        api = WebNovelComApi(self.browser)
        chapter = api.get_chapter(parse_url('https://www.webnovel.com'
                                            '/apiajax/chapter/GetContent'
                                            '?_csrfToken=64nio7VwoiRDMT9sSOyrQFIQ9gWb1fQZxbIdqIpJ'
                                            '&bookId=8094127105005005'
                                            '&chapterId=21727507347378214'
                                            '&_=1578354148202'))
        self.assertIsNotNone(chapter)
        self.assertTrue(isinstance(chapter, WebNovelComChapter))
        self.assertFalse(chapter.success)
        chapter.timestamp = datetime.fromtimestamp(1578354148.203)
        self.assertTrue(chapter.parse())
        self.assertTrue(chapter.success)
        self.assertEqual('https://www.webnovel.com/apiajax/chapter/GetContent'
                         '?_csrfToken=64nio7VwoiRDMT9sSOyrQFIQ9gWb1fQZxbIdqIpJ'
                         '&bookId=8094127105005005'
                         '&chapterId=21727507347378214'
                         '&_=1578354148202', chapter.url.url)
        self.assertEqual('https://www.webnovel.com', chapter.alter_url('').url)
        self.assertEqual('Immortals', chapter.title)
        self.assertEqual('en', chapter.language)
        self.assertEqual('Er Gen', chapter.author)
        self.assertEqual('Rex', chapter.translator)
        self.assertEqual(21727507347378214, chapter.chapter_id)
        self.assertTrue(chapter.is_complete())
        self.assertFalse(chapter.is_vip)
        self.assertEqual('https://www.webnovel.com/apiajax/chapter/GetContent'
                         '?_csrfToken=64nio7VwoiRDMT9sSOyrQFIQ9gWb1fQZxbIdqIpJ'
                         '&bookId=8094127105005005'
                         '&chapterId=21727507347361830'
                         '&_=1578354148203', chapter.previous_chapter.url)
        self.assertEqual('https://www.webnovel.com/apiajax/chapter/GetContent'
                         '?_csrfToken=64nio7VwoiRDMT9sSOyrQFIQ9gWb1fQZxbIdqIpJ'
                         '&bookId=8094127105005005'
                         '&chapterId=21727507347394598'
                         '&_=1578354148203', chapter.next_chapter.url)
        self.maxDiff = None
        chapter.clean_content()
        self.assertEqual("""The carriage quickly rolled along the road. Wang Lin’s body bounced with the uneven ground. In his arm was the package that contained all of his parents’ hope as he left the village he had lived in for 15 years.
The trip won’t be a short one. Wang Lin lied down and fell asleep in the carriage. Not knowing how much time had passed, he was gently nudged. He opened his eyes and looked up to see fourth uncle, who looked at him with smiling face and asked, “Tie Zhu, how do you feel about leaving home for the first time?”
Wang Lin noticed that the carriage had stopped and smiled. “Not much to say, just a little afraid if I will be selected by the immortals or not.”
Fourth uncle let out a laugh and patted Tie Zhu’s shoulder, saying, “Okay, don’t over think it. This is uncle’s house. You go rest first, then I’ll take you to the family tomorrow morning.”
After getting off the carriage, in front of Wang Lin was a tile roofed house. He followed fourth uncle to a room. Wang Lin sat on the bed. He was unable to sleep. The things that his parents, the villagers, and relatives said flashed through his mind. He signed in his heart. The thought of becoming the disciple of an immortal become heavier in his mind.
Time passed by, bit by bit. A moment later, the sun gradually started to rise. Wang Lin didn’t get much rest throughout the night, but he was still full of energy. With a trace of fear, he followed fourth uncle to the main house of the Wang family.
This was the first time Wang Lin had seen a house this big, leaving him in a daze. Fourth uncle said, while walking, “Tie Zhu, you have to make your father proud. Don’t let the relatives ridicule you.”
Wang Lin’s mind became more tense. He bit his lips and nodded.
Soon, fourth uncle brought him to the middle of the courtyard. Tie Zhu’s father’s eldest brother was standing there. When he saw Tie Zhu, he nodded and said, “Tie Zhu, when the immortal arrives, don’t freak out, just follow your older brother Wang Zhuo. Do everything he does.”
The old man’s tone was very hard on those last few words.
Wang Lin stayed silent. He looked around and noticed that besides Wang Zhuo, there was another youth. The youth’s skin was a bit dark, his build was very large, and his eyes showed a hint of intelligence. There was a bulge in his shirt, like he was hiding something.
He look at Tie Zhu and made a face, then ran over and said, “So you’re second uncle’s son? My name is Wang Hao.”
Wang Lin chuckled and nodded.
When the old man saw Wang Lin ignoring him, he became very annoyed and was about to scold him.
Right at that moment, the clouds in the sky suddenly split. A sword of light suddenly descended like lightning. After the light disappeared, there stood a youth in white, whose eyes were bright and piercing, emitting an elegant spirit. This cold eyes swept across the three youths, especially at the youth with the bulge in his shirt. He coldly asked, “Are these three the ones recommended by the Wang family?”
“This is an immortal?” Under his gaze, Wang Lin started to feel cold. His heart started pounding and his face became pale while staring at the immortal.
The dark skinned youth, after seeing the immortal, placed his hands near the pockets of his pants, showing a respectful demeanour. His eyes held a fanatical expression.
Only Wang Zhuo casually looked at the others and snorted.
Wang Zhuo’s father quickly stepped forward and respectfully said, “Immortal, these three are the Wang family’s recommended youths.”
The youth nodded and impatiently said, “Who is Wang Zhuo?”
The old man’s face showed a flash of happiness, then he quickly pulled Wang Zhuo. “Immortal, this is my son, Wang Zhuo.”
The immortal youth gave Wang Zhuo a deep look. His face brightened and he nodded. “Wang Zhuo is indeed talented. No wonder Uncle-Master took a liking to him.”
Wang Zhuo proudly looked at Wang Lin and proudly said, “This is natural. In order to become an immortal, one must have a strong spirit.”
The youth made a frown, but it quickly disappeared. He directed a faint a smile at Wang Zhuo’s direction, waved his sleeves, and took the three youths on the rainbow and disappeared.
Fourth uncle looked into the sky and muttered, “Tie Zhu, you must be selected!”
Wang Lin felt his body lighten. The wind hitting his face caused him pain. On closer inspection, he noticed that he was under the arm of the youth, flying quickly through the sky. The village turned into little black dots as they quickly flew forward.
After just a little while, the wind caused his eyes to turn red and tear up.
“Unless you three want to become blind, close your eyes,” the youth coldly said. Wang Lin’s heart tensed. He quickly closed his eyes, afraid to keep looking.
After a short period of time, Wang Lin could feel that the youth was short of breath and that his speed started decreasing. Then, in a flash, the youth quickly descended. The moment before landing, the youth loosened his arm and the three youths fell to the ground.
Thankfully, the fall wasn’t hard. The three got up quickly. In front of Wang Lin was a paradise-like scene, with mountains, flowers, and a river. It was a truly idyllic scene.
Straight ahead was a towering mountain. Its peak was covered in clouds, which hid its true appearance. Echoes of beasts’ cries could be heard. There was a path of twisted steps that snaked its way down the mountain, like a painting, evoking a feeling of a different world.
Far off in the in the distance, at the top of the mountain, stood a hall. Even though it was covered by the clouds, the shining bright light made people to want to worship it.
Next to the hall was a silver colored bridge with the shape of a crescent moon, which connected that peak with another mountain peak.
With these natural beauties, this was truly worthy of being the location of the Heng Yue Sect. The Heng Yue Sect was one of the few existing immortal sects. 500 years ago, it was the leading force of the entire cultivation world, with many branch sects. However, with the passage of time, it had shrunk to its current size and was only barely able to have a foothold in the cultivation world.
However, for the mortals near the Heng Yue sect, it was still an elusive figure.
“Little brother Zhang, are these the three candidates recommended by the Wang family?” A middle aged man dressed in black with an immortal demeanor floated down from the mountain’s peak.
The youth showed a face full of respect and said, “Third brother, these are the Wang family’s three recommended youths.”
The middle aged man’s gaze swept across them. He focused on Wang Zhuo a few times. Smiling, he said, “I know you are about to have a breakthrough. I’ll handle the test, you go cultivate.”
The youth agreed. His body moved toward the mountain, and in the blink of an eye, disappeared without a trace.
Wang Lin stared at the scene before him, full of excitement. Suddenly, he noticed someone tugging his clothes and turned around. It was Wang Hao. His eyes were filled with excitement. He said, “This is where the immortals live! F*ck my grandmother! No matter what, I, Wang Hao, must be selected.” Saying so, he touched the bulging object concealed in his shirt.
""".replace('\n', '\r\n'),
                         chapter.content.text)


# noinspection DuplicatedCode,SpellCheckingInspection
class WuxiaWorldComApiPOTTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser = prepare_browser(Har.WM_POTT_C92_95)
        cls.browser.navigate('https://www.webnovel.com/')  # Get the csrf cookie

    def test_search_RI(self):
        api = WebNovelComApi(self.browser)
        results = api.search('Pursuit of the Truth')
        self.assertIsNotNone(results)
        self.assertEqual(1, len(results))
        result = results[0]
        self.assertEqual('Pursuit of the Truth', result.title)
        self.assertEqual(7853880705001905, result.id)
        self.assertEqual('https://www.webnovel.com/book/7853880705001905', result.url.url)

    def test_parsing_novel(self):
        api = WebNovelComApi(self.browser)
        novel = api.get_novel(parse_url('https://www.webnovel.com/book/7853880705001905'))
        self.assertIsNotNone(novel)
        self.assertTrue(isinstance(novel, WebNovelComNovel))
        self.assertFalse(novel.success)
        novel.timestamp = datetime.fromtimestamp(1578419298.005)
        self.assertTrue(novel.parse())
        self.assertTrue(novel.success)
        self.assertEqual(7853880705001905, novel.novel_id)
        self.assertEqual('https://www.webnovel.com/book/7853880705001905', novel.alter_url().url)
        self.assertEqual('https://www.webnovel.com', novel.alter_url('').url)
        self.assertEqual('Pursuit of the Truth', novel.title)
        self.assertEqual('Er Gen', novel.author)
        self.assertEqual('Mogumoguchan', novel.translator)
        self.assertEqual('© 2020 Webnovel', novel.rights)
        self.assertEqual(datetime.fromtimestamp(0), novel.release_date)
        self.assertEqual('/apiajax/chapter/GetContent'
                         '?_csrfToken=7KRqdh9Hl2OF1xajN4rA94KXpJ9cCRYPwAGrsUiK'
                         '&bookId=7853880705001905'
                         '&chapterId=21104441805559885'
                         '&_=1578419298005', novel.first_chapter.path)
        self.assertListEqual(['Cultivation', 'Male Protagonist', 'Adventure', 'Weak to Strong',
                              'Unique Cultivation Technique', 'Multiple Realms', 'Hard-Working Protagonist',
                              'Legendary Artifacts', 'handsome male lead', 'Gods', 'Tribal Society',
                              'Death Of Loved Ones', 'Transplanted Memories', 'Revenge', 'Alchemy', 'Betrayal',
                              'Demons', 'Underestimated Protagonist', 'Romantic Subplot', 'Secret Identity',
                              'Hiding True Abilities', 'Pill Concocting', 'Blood Manipulation'], novel.tags)

    def test_parsing_chapter(self):
        api = WebNovelComApi(self.browser)
        chapter = api.get_chapter(parse_url('https://www.webnovel.com'
                                            '/apiajax/chapter/GetContent'
                                            '?_csrfToken=7KRqdh9Hl2OF1xajN4rA94KXpJ9cCRYPwAGrsUiK'
                                            '&bookId=7853880705001905'
                                            '&chapterId=21654434396301979'
                                            '&_=1578419315007'))
        self.assertIsNotNone(chapter)
        self.assertTrue(isinstance(chapter, WebNovelComChapter))
        self.assertFalse(chapter.success)
        chapter.timestamp = datetime.fromtimestamp(1578419315.007)
        self.assertTrue(chapter.parse())
        self.assertTrue(chapter.success)
        self.assertEqual('https://www.webnovel.com/apiajax/chapter/GetContent'
                         '?_csrfToken=7KRqdh9Hl2OF1xajN4rA94KXpJ9cCRYPwAGrsUiK'
                         '&bookId=7853880705001905'
                         '&chapterId=21654434396301979'
                         '&_=1578419315007', chapter.url.url)
        self.assertEqual('https://www.webnovel.com', chapter.alter_url('').url)
        self.assertEqual('The Fourth Arrow!', chapter.title)
        self.assertEqual('en', chapter.language)
        self.assertEqual('Er Gen', chapter.author)
        self.assertEqual('Mogumoguchan', chapter.translator)
        self.assertEqual(21654434396301979, chapter.chapter_id)
        self.assertFalse(chapter.is_complete())
        self.assertTrue(chapter.is_vip)
        self.assertEqual('https://www.webnovel.com/apiajax/chapter/GetContent'
                         '?_csrfToken=7KRqdh9Hl2OF1xajN4rA94KXpJ9cCRYPwAGrsUiK'
                         '&bookId=7853880705001905'
                         '&chapterId=21654421779835543'
                         '&_=1578419315007', chapter.previous_chapter.url)
        self.assertEqual('https://www.webnovel.com/apiajax/chapter/GetContent'
                         '?_csrfToken=7KRqdh9Hl2OF1xajN4rA94KXpJ9cCRYPwAGrsUiK'
                         '&bookId=7853880705001905'
                         '&chapterId=21654540428307122'
                         '&_=1578419315007', chapter.next_chapter.url)
        self.maxDiff = None
        chapter.clean_content()
        self.assertEqual("""The terrifying image of the blood moon appeared in Su Ming's eyes. The moon looked enchanting, causing all of those who saw it to feel their hearts tremble. At that moment, Bi Tu, who was fighting against the elder in the sky, suddenly felt agitated for a reason that he could not understand. That agitation suddenly appeared, but it was not the first time it had occurred. He remembered distinctly that he had also felt this sort of agitation and restlessness several months ago.
It was as if he could no longer control his Qi, and it wanted to leave his body so as to worship something.
Mo Sang, who was fighting against Bi Tu, was originally exhausted, but a glint suddenly appeared in his eyes. He noticed the change in Bi Tu's Qi and quickly took a step forward. The dark python by his side roared, using the chance to show off the might of its Berserker Art.
The huge wave of blood fog tumbled violently in the sky, imitating the motion of Bi Tu moving backwards.
That scene made all the pe""".replace('\n', '\r\n'),
                         chapter.content.text)


if __name__ == '__main__':
    unittest.main()
