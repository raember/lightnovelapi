import logging
import unittest
from datetime import datetime

from spoofbot.adapter import HarAdapter
from spoofbot.util import TimelessRequestsCookieJar
from urllib3.util import parse_url

from tests.config import prepare_browser, Har
from lightnovel.webnovel_com import WebNovelComApi, WebNovelComNovel, WebNovelComChapter

# noinspection SpellCheckingInspection
logging.getLogger('chardet.charsetprober').setLevel(logging.ERROR)


# noinspection DuplicatedCode,SpellCheckingInspection
class WuxiaWorldComApiRITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser = prepare_browser(Har.WM_SEARCH_RI_C1_5)
        adapter = cls.browser.adapter
        if isinstance(adapter, HarAdapter):
            adapter.match_header_order = False
            adapter.match_headers = False
            adapter.match_data = True
            adapter.delete_after_matching = False
        cls.browser.cookies = TimelessRequestsCookieJar(datetime(2020, 1, 1))
        cls.browser.navigate('https://www.webnovel.com/')  # Get the csrf cookie

    def test_search_RI(self):
        api = WebNovelComApi(self.browser)
        results = api.search('Renegade Immortal')
        self.assertIsNotNone(results)
        self.assertEqual(3, len(results))
        result = results[1]
        self.assertEqual('Renegade Immortal', result.title)
        self.assertEqual(8094127105005005, result.id)
        self.assertEqual('https://www.webnovel.com/book/8094127105005005', result.url.url)

    def test_parsing_novel(self):
        api = WebNovelComApi(self.browser)
        novel = api._get_novel(parse_url('https://www.webnovel.com/book/renegade-immortal_8094127105005005'))
        self.assertIsNotNone(novel)
        self.assertTrue(isinstance(novel, WebNovelComNovel))
        self.assertFalse(novel.success)
        novel.timestamp = datetime.fromtimestamp(1613587005.303)
        self.assertTrue(novel.parse())
        self.assertTrue(novel.success)
        self.assertEqual('8094127105005005', novel.novel_id)
        self.assertEqual('https://www.webnovel.com/book/renegade-immortal_8094127105005005', novel.url.url)
        self.assertEqual('https://www.webnovel.com', novel.change_url(path=None).url)
        self.assertEqual('Renegade Immortal', novel.title)
        self.assertEqual('Er Gen', novel.author)
        self.assertListEqual(['Rex'], novel.translators)
        self.assertEqual('© 2021 Webnovel', novel.copyright)
        self.assertEqual(datetime.fromtimestamp(0), novel.release_date)
        self.assertEqual('https://www.webnovel.com/go/pcm/chapter/getContent'
                         '?_csrfToken=f4731e60-2913-416d-848f-6612e41767ea'
                         '&bookId=8094127105005005'
                         '&chapterId=21727507347361830'
                         '&_=1613587005303', novel.generate_chapter_entries().__next__()[1].url.url)
        self.assertListEqual(['Weak to Strong', 'Cultivation'], novel.tags)

    def test_parsing_chapter(self):
        api = WebNovelComApi(self.browser)
        chapter = api.get_chapter(parse_url('https://www.webnovel.com'
                                            '/go/pcm/chapter/getContent'
                                            '?_csrfToken=f4731e60-2913-416d-848f-6612e41767ea'
                                            '&bookId=8094127105005005'
                                            '&chapterId=21727507347378214'
                                            '&_=1613587011601'))
        self.assertIsNotNone(chapter)
        self.assertTrue(isinstance(chapter, WebNovelComChapter))
        self.assertFalse(chapter.success)
        chapter.timestamp = datetime.fromtimestamp(1578354148.203)
        self.assertTrue(chapter.parse())
        self.assertTrue(chapter.success)
        self.assertEqual('https://www.webnovel.com/go/pcm/chapter/getContent'
                         '?_csrfToken=f4731e60-2913-416d-848f-6612e41767ea'
                         '&bookId=8094127105005005'
                         '&chapterId=21727507347378214'
                         '&_=1613587011601', chapter.url.url)
        self.assertEqual('https://www.webnovel.com', chapter.change_url(path=None, query=None).url)
        self.assertEqual('Immortals', chapter.title)
        self.assertEqual(21727507347378214, chapter.chapter_id)
        self.assertTrue(chapter.is_complete())
        self.assertFalse(chapter.is_vip)
        self.assertEqual('https://www.webnovel.com/go/pcm/chapter/getContent'
                         '?_csrfToken=f4731e60-2913-416d-848f-6612e41767ea'
                         '&bookId=8094127105005005'
                         '&chapterId=21727507347361830'
                         '&_=1578354148203', chapter.previous_chapter.url.url)
        self.assertEqual('https://www.webnovel.com/go/pcm/chapter/getContent'
                         '?_csrfToken=f4731e60-2913-416d-848f-6612e41767ea'
                         '&bookId=8094127105005005'
                         '&chapterId=21727507347394598'
                         '&_=1578354148203', chapter.next_chapter.url.url)
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
""",
                         chapter.content.text)


# noinspection DuplicatedCode,SpellCheckingInspection
class WuxiaWorldComApiPOTTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser = prepare_browser(Har.WM_POTT_C40_41)
        adapter = cls.browser.adapter
        if isinstance(adapter, HarAdapter):
            adapter.match_header_order = False
            adapter.match_headers = False
            adapter.match_data = False
            adapter.delete_after_matching = False
        cls.browser.navigate('https://www.webnovel.com/')  # Get the csrf cookie
        # In case the CSRF token does not get assigned via cookies, it has expired already!
        # Change the expiration date to the heat death of the universe!

    def test_search_POTT(self):
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
        novel = api._get_novel(parse_url('https://www.webnovel.com/book/pursuit-of-the-truth_7853880705001905'))
        self.assertIsNotNone(novel)
        self.assertTrue(isinstance(novel, WebNovelComNovel))
        self.assertFalse(novel.success)
        novel.timestamp = datetime.fromtimestamp(1613685056.304)
        self.assertTrue(novel.parse())
        self.assertTrue(novel.success)
        self.assertEqual('7853880705001905', novel.novel_id)
        self.assertEqual('https://www.webnovel.com/book/pursuit-of-the-truth_7853880705001905', novel.url.url)
        self.assertEqual('https://www.webnovel.com', novel.change_url(path=None).url)
        self.assertEqual('Pursuit of the Truth', novel.title)
        self.assertEqual('Er Gen', novel.author)
        self.assertListEqual(['Mogumoguchan'], novel.translators)
        self.assertEqual('© 2021 Webnovel', novel.copyright)
        self.assertEqual(datetime.fromtimestamp(0), novel.release_date)
        self.assertEqual('https://www.webnovel.com/go/pcm/chapter/getContent'
                         '?_csrfToken=ea7e24b7-fd2c-494e-a940-ce49e1da393e'
                         '&bookId=7853880705001905'
                         '&chapterId=21104441805559885'
                         '&_=1613685056304', novel.generate_chapter_entries().__next__()[1].url.url)
        self.assertListEqual(sorted(['Cultivation', 'Male Protagonist', 'Adventure', 'Weak to Strong',
                                     'Unique Cultivation Technique', 'Multiple Realms', 'Hard-Working Protagonist',
                                     'Legendary Artifacts', 'handsome male lead', 'Gods', 'Tribal Society',
                                     'Death Of Loved Ones', 'Transplanted Memories', 'Revenge', 'Alchemy', 'Betrayal',
                                     'Demons', 'Underestimated Protagonist', 'Romantic Subplot', 'Secret Identity',
                                     'Hiding True Abilities', 'Pill Concocting', 'Blood Manipulation']),
                             sorted(novel.tags))

    def test_parsing_chapter_40(self):
        api = WebNovelComApi(self.browser)
        chapter = api.get_chapter(parse_url('https://www.webnovel.com'
                                            '/go/pcm/chapter/getContent'
                                            '?_csrfToken=ea7e24b7-fd2c-494e-a940-ce49e1da393e'
                                            '&bookId=7853880705001905'
                                            '&chapterId=21186817416027363'
                                            '&_=1613685072802'))
        self.assertIsNotNone(chapter)
        self.assertTrue(isinstance(chapter, WebNovelComChapter))
        self.assertFalse(chapter.success)
        chapter.timestamp = datetime.fromtimestamp(1613677829.700)
        self.assertTrue(chapter.parse())
        self.assertTrue(chapter.success)
        self.assertEqual('https://www.webnovel.com/go/pcm/chapter/getContent'
                         '?_csrfToken=ea7e24b7-fd2c-494e-a940-ce49e1da393e'
                         '&bookId=7853880705001905'
                         '&chapterId=21186817416027363'
                         '&_=1613685072802', chapter.url.url)
        self.assertEqual('https://www.webnovel.com', chapter.change_url(path=None, query=None).url)
        self.assertEqual('Feeling of Animosity!', chapter.title)
        self.assertEqual(21186817416027363, chapter.chapter_id)
        self.assertTrue(chapter.is_complete())
        self.assertFalse(chapter.is_vip)
        self.assertEqual('https://www.webnovel.com/go/pcm/chapter/getContent'
                         '?_csrfToken=ea7e24b7-fd2c-494e-a940-ce49e1da393e'
                         '&bookId=7853880705001905'
                         '&chapterId=21186809094528226'
                         '&_=1613677829700', chapter.previous_chapter.url.url)
        self.assertEqual('https://www.webnovel.com/go/pcm/chapter/getContent'
                         '?_csrfToken=ea7e24b7-fd2c-494e-a940-ce49e1da393e'
                         '&bookId=7853880705001905'
                         '&chapterId=21186868150328548'
                         '&_=1613677829700', chapter.next_chapter.url.url)
        self.maxDiff = None
        chapter.clean_content()
        self.assertEqual("""Time passed by as Su Ming immersed himself in the process of quenching herbs and his training. Xiao Hong returned to the cave exhausted after a few days as Su Ming was meditating. Its red fur had darkened several shades as well, illustrating just how tired it was. 
However, tired as it may be, there were expressions of longing and pride on its face. It kept sniffing its right paw and grinned as if it was giggling foolishly.  
When Xiao Hong came back, Su Ming opened his eyes slightly. When he saw Xiao Hong, he remembered what he witnessed the day he followed Xiao Hong into the forest. An awkward expression settled on his face.
Xiao Hong noticed Su Ming’s gaze and turned around to look at him. It immediately ran towards him and raised its right paw proudly. It extended its right paw to Su Ming, urging Su Ming to sniff it again. It felt that it had to share everything that was good with everyone.
Su Ming did not know whether to laugh or cry. He no longer paid any attention to Xiao Hong and once again immersed himself in his training.
The month soon passed by. The date Su Ming was to go with the elder to Wind Stream Tribe loomed near.
During this period of time, Su Ming used up all of the Cloud Gauze Grass in his possession but only managed to create one Mountain Spirit. The high failure rate made Su Ming’s spirits incredibly low.
At the very least, his training had been pretty successful. He had completely settled into the fourth level of the Blood Solidification Realm and managed to manifest two more blood veins, bringing the total blood veins he manifested up to 49 blood veins. He had also gradually adapted to the strangeness of the Fire Berserker Art. 
However, the further down the path of the Blood Solidification Realm, the harder it was to solidify more blood veins. Lately, no matter how hard Su Ming trained, he could no longer solidify any more of his blood. He understood that this was related to the incompletion of the third burning of his blood.
Moreover when the moon was out at night, Su Ming acted according to his senses and tried to control the moonlight multiple times. However, the results were not obvious. It seemed like he could only control no more than a small ray of moonlight.
Even though it was only a small ray of moonlight, in Su Ming’s hands, it was incredibly sharp, even more so than his horn. Most importantly, Xiao Hong could not see the ray of moonlight. From that observation alone, Su Ming believed that he was the only one who could see the moonlight, no one else.
It was daylight. Su Ming stood up and looked around the fire cave. After a moment of silence he pushed his Barren Cauldron aside. He did not know how long he would stay at Wind Stream Tribe. He needed to make preparations.
On the walls of the fire cave were numerous fine ravines decorating the walls densely. Those ravines were created during the days Su Ming learned how to control the moonlight.
Once he packed up, Su Ming left the cave. Xiao Hong had already woken up. When it saw that Su Ming was about to leave, it followed him quickly. When they arrived outside the cave, it climbed onto Su Ming’s shoulders, too lazy to descend the mountain on its own.
‘It’s a pity Mountain Spirit is too hard to make… There were eight holes underneath the picture of Mountain Spirit on the second door so it’s obvious I have to offer eight of them… I wonder how long it’ll take for me to offer up 8 Mountain Spirits without forsaking my own training…
‘Besides, I also need to offer the pills called Fire of the South for the second door to open… But I’ve never seen the herbs required for the pills before. Thank the heavens for the bamboo slip the elder gave me. At least there are some descriptions of herbs there.’ 
Su Ming stood outside the cave and looked at the sun rising from the horizon He breathed in the refreshing cold air around him.
‘I can only open the second door after I have gathered enough Mountain Spirit and Fire of the South… At the very least there is no need for me to create The Welcoming of Deities. Still, it just shows how rare The Welcoming of Deities is!’
As Su Ming was deep in his thoughts, Xiao Hong who was sprawled across his shoulders, grabbed his hair and hissed impatiently.
Su Ming patted the little monkey’s head and jumped down the mountain peak. The wind blew against him. It made his shirt and hair flutter. It also made Xiao Hong clutch onto Su Ming’s hair tightly as it screamed in terror.
Su Ming laughed. He grabbed onto a stone within his right hand’s reach as he fell. Once he regained his momentum, he jumped down again. With his current abilities, Su Ming arrived at the foot of Black Flame Mountain before long.
Snow still covered the forests. They were really soft under his feet as well. He sank when he stepped on them. Su Ming then ran into the distance. He originally intended to return to the tribe but when he arrived at a crossroads, his footsteps faltered and he hesitated for a moment.
Xiao Hong was sitting on Su Ming’s shoulders. It seemed to be in a comfortable position. Occasionally, it would sniff its right paw with an exhilarated expression. It was slightly surprised when it saw Su Ming stop. 
The right path led back to his own tribe whereas the left path… Su Ming gazed at the path. It led to Dark Dragon Tribe.
"I’ll just go and take a look… Xiao Hong, have you ever seen Bai Ling? Oh, that’s right, you’ve never seen her. Do you want to see her?" Su Ming asked softly.
Xiao Hong widened its eyes. It scratched the fur on its face and did not make a sound.
"Alright. Since you want to see her, I’ll let you look at her from afar," Su Ming spoke as if he suddenly had a perfectly logical reason to go to Dark Dragon Tribe. He smiled and patted Xiao Hong’s head. When Xiao Hong looked at him with an unamused expression, Su Ming ran down the left lane quickly.
Su Ming arrived at the spot where he parted with Bai Ling when dusk arrived. The sun had turned red as it began to set. He squatted there and looked at the silhouette of Dark Dragon Tribe. He saw the other members of Dark Dragon Tribe moving in there but he did not see Bai Ling.
After a long time, Su Ming sank into his thoughts. He did not know what he was thinking. He only thought that Bai Ling was pretty. She was the prettiest girl he had ever seen in his life and he wanted to look at her a few more times.
After a moment of hesitation, he sat down quietly and chose not to take any action. Instead, he looked at the sky. When the sun was about to set and the sky about to darken completely, he stood up and walked forward briskly. He still kept a hint of awareness to his surroundings as he approached Dark Dragon Tribe. Nonetheless, he did not dare go too near the tribe. It was after all, not Dark Mountain Tribe. If he was discovered, there was a possibility he would be in danger. 
While the relationship between Dark Mountain Tribe and Dark Dragon Tribe was not as tense as Dark Mountain Tribe and Black Mountain Tribe, it did not mean that they were at peace with each other. If they met in the wild, they still regarded each other with hostility. It would have been even more so if they had discovered Su Ming, who had been lingering outside Dark Dragon Tribe.
"Ah… I shouldn’t have done this." Su Ming mumbled as he continued walking forward. When he was about 10,000 feet away from Dark Dragon Tribe, he stopped walking. Su Ming grew up in the tribe and had been regularly going out into the wild to collect herbs. On occasion, he even ran into members from Black Mountain Tribe.  Caution and vigilance was practically second nature to him. 
He had seen too much violence in his life. Even if most of the violence happened to beasts which the hunting team brought back, living in such conditions for years had already influenced him unconsciously as a child. Besides, he had already killed someone!
Not even Lei Chen had stained his hands with human blood before.
As such, even if Su Ming wanted to see Bai Ling for some unknown reason, his instincts that were buried deep within told him to move only during the night. As an act of caution, Su Ming also chose to stop 10,000 feet away from the tribe.
He squatted down and took a look at Dark Dragon Tribe. Then, he turned around resolutely without hesitation and left the area around Dark Dragon Tribe quickly.
Yet just as he took a few steps forward, Su Ming felt goosebumps. A sense of danger far stronger than his meeting with the two Berserkers from Black Mountain Tribe came crashing towards him.
As he leaped forward, he twisted his body abruptly and covered his head with both hands. His entire body curled into a ball as he hugged Xiao Hong tightly in his bosom, stopping in midair for a brief moment as if he was frozen.
That moment, a sharp whistling sound sliced through the air. A long gigantic spear about 30 feet flew towards Su Ming like lightning from within the giant wooden fence surrounding Dark Dragon Tribe. It rushed past Su Ming’s body and stuck itself into the ground, creating a loud noise. The ground shook and snow flew into the air.   
It also stirred up a wave of air which spread across a wide area around the spear. Su Ming was lucky he was cautious enough to avoid it beforehand. He landed on the ground as he moved along the air’s wave current and ran forward at full speed immediately.
"Leaving?" A cold voice traveled from afar. A man with long hair wearing a shirt made of sackcloth chased after him with a fierce look in his eyes.
As Su Ming ran forward, he turned back and looked at him with a cold glare in his eyes.
""",
                         chapter.content.text)

    def test_parsing_chapter_41(self):
        api = WebNovelComApi(self.browser)
        chapter = api.get_chapter(parse_url('https://www.webnovel.com'
                                            '/go/pcm/chapter/getContent'
                                            '?_csrfToken=ea7e24b7-fd2c-494e-a940-ce49e1da393e'
                                            '&bookId=7853880705001905'
                                            '&chapterId=21186868150328548'
                                            '&_=1613685072806'))
        self.assertIsNotNone(chapter)
        self.assertTrue(isinstance(chapter, WebNovelComChapter))
        self.assertFalse(chapter.success)
        chapter.timestamp = datetime.fromtimestamp(1613677829.700)
        self.assertTrue(chapter.parse())
        self.assertTrue(chapter.success)
        self.assertEqual('https://www.webnovel.com/go/pcm/chapter/getContent'
                         '?_csrfToken=ea7e24b7-fd2c-494e-a940-ce49e1da393e'
                         '&bookId=7853880705001905'
                         '&chapterId=21186868150328548'
                         '&_=1613685072806', chapter.url.url)
        self.assertEqual('https://www.webnovel.com', chapter.change_url(path=None, query=None).url)
        self.assertEqual('Si Kong', chapter.title)
        self.assertEqual(21186868150328548, chapter.chapter_id)
        self.assertFalse(chapter.is_complete())
        self.assertTrue(chapter.is_vip)
        self.assertEqual('https://www.webnovel.com/go/pcm/chapter/getContent'
                         '?_csrfToken=ea7e24b7-fd2c-494e-a940-ce49e1da393e'
                         '&bookId=7853880705001905'
                         '&chapterId=21186817416027363'
                         '&_=1613677829700', chapter.previous_chapter.url.url)
        self.assertEqual('https://www.webnovel.com/go/pcm/chapter/getContent'
                         '?_csrfToken=ea7e24b7-fd2c-494e-a940-ce49e1da393e'
                         '&bookId=7853880705001905'
                         '&chapterId=21186881303665893'
                         '&_=1613677829700', chapter.next_chapter.url.url)
        self.maxDiff = None
        chapter.clean_content()
        self.assertEqual("""The young man looked to be about 18 to 19 years old. He was strongly built. So much so that he could compete with Lei Chen. In his hands, he held a long spear. The spear was only about five feet long but its black body gave it a shocking and chilling aura. There was also a golden dazzle on the tip of the spear.
However, the spear was essentially not made of stone. It was made out of a material Su Ming had never seen before. He looked back from afar and when his eyes landed on the spear, his heart froze in fear.
It was a very, very familiar feeling.
Yet, he did not know where that familiarity came from. Nonetheless, it made him feel that danger was looming over his head. Su Ming ignored everything else. Only a basic instinctual need for him to remain calm was left.
‘That person is not wearing hides but is wearing sackcloth instead. This sort of clothes… This person must have a pretty high status in Dark Dragon Tribe!
‘I don’t regret going near Dark Dragon Tribe!’ 
""",
                         chapter.content.text)


if __name__ == '__main__':
    unittest.main()
