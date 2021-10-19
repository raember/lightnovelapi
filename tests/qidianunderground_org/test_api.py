import logging
import unittest
from datetime import datetime, timezone

from spoofbot.adapter import FileCacheAdapter, HarAdapter

from lightnovel.qidianunderground_org import QidianUndergroundOrgApi, QidianUndergroundOrgChapter, \
    QidianUndergroundOrgNovel
from lightnovel.qidianunderground_org.api import QidianUndergroundOrgNovelEntry
from tests.config import prepare_browser, Har, resolve_path

# noinspection SpellCheckingInspection
logging.getLogger('chardet.charsetprober').setLevel(logging.ERROR)


class QidianUndergroundOrgPoTTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser = prepare_browser(Har.QU_POT_C89_103)
        cls.har_adapter = cls.browser.adapter
        if isinstance(cls.har_adapter, HarAdapter):
            cls.har_adapter.match_header_order = False
            cls.har_adapter.match_headers = False
            cls.har_adapter.match_data = True
            cls.har_adapter.delete_after_matching = False
        cls.file_cache_adapter = FileCacheAdapter(resolve_path('.cache'))
        # Get the csrf cookie
        cls.browser.navigate('https://toc.qidianunderground.org/')
        cls.api = QidianUndergroundOrgApi(cls.browser)

    def test_searching_novel(self):
        # self.browser.adapter = self.file_cache_adapter
        novels = self.api.search('Pursuit of the Truth', complete=True)
        # self.browser.adapter = self.har_adapter
        self.assertIsNotNone(novels)
        self.assertEqual(1, len(novels))
        novel = novels[0]
        self.assertTrue(isinstance(novel, QidianUndergroundOrgNovelEntry))
        self.assertEqual('Pursuit of the Truth', novel.title)
        self.assertEqual('b984e3b6625ce22f', novel.novel_id)
        self.assertEqual(1604537046, int(novel.last_update.replace(tzinfo=timezone.utc).timestamp()))
        self.assertTrue(novel.complete)

    def test_parsing_novel(self):
        # self.browser.adapter = self.file_cache_adapter
        novel = self.api.get_novel(QidianUndergroundOrgNovelEntry(
            'Pursuit of the Truth',
            'b984e3b6625ce22f',
            datetime.utcfromtimestamp(1604537046),
            True
        ))
        # self.browser.adapter = self.har_adapter
        self.assertIsNotNone(novel)
        self.assertTrue(isinstance(novel, QidianUndergroundOrgNovel))
        self.assertTrue(novel.success)

    def test_parsing_chapter(self):
        # self.browser.adapter = self.file_cache_adapter
        self.api.get_novel(QidianUndergroundOrgNovelEntry(
            'Pursuit of the Truth',
            'b984e3b6625ce22f',
            datetime.utcfromtimestamp(1604537046),
            True
        ))  # Cache novel as active
        # self.browser.adapter = self.har_adapter
        chapter = self.api.get_chapter(94)
        self.assertIsNotNone(chapter)
        self.assertTrue(isinstance(chapter, QidianUndergroundOrgChapter))
        self.assertFalse(chapter.success)
        self.assertTrue(chapter.parse())
        self.assertTrue(chapter.success)
        self.assertEqual('https://vim.cx/?7254a27db5af3377#ARwznrey5WNPJc9gTYwRrXgnKqgQuUViauBCx43tN4kh',
                         chapter.url.url)
        self.assertEqual('https://vim.cx', chapter.change_url(path=None, query=None, fragment=None).url)
        self.assertEqual('The Fourth Arrow!', chapter.title)
        self.assertEqual(94, chapter.index)
        self.assertTrue(chapter.is_complete())
        self.assertIsNone(chapter.previous_chapter)
        self.assertIsNone(chapter.next_chapter)
        self.maxDiff = None
        chapter.clean_content()
        self.assertEqual("""

Chapter 94: The Fourth Arrow!

The terrifying image of the blood moon appeared in Su Ming's eyes. The moon looked enchanting, causing all of those who saw it to feel their hearts tremble. At that moment, Bi Tu, who was fighting against the elder in the sky, suddenly felt agitated for a reason that he could not understand. That agitation suddenly appeared, but it was not the first time it had occurred. He remembered distinctly that he had also felt this sort of agitation and restlessness several months ago.

It was as if he could no longer control his Qi, and it wanted to leave his body so as to worship something.

Mo Sang, who was fighting against Bi Tu, was originally exhausted, but a glint suddenly appeared in his eyes. He noticed the change in Bi Tu's Qi and quickly took a step forward. The dark python by his side roared, using the chance to show off the might of its Berserker Art.

The huge wave of blood fog tumbled violently in the sky, imitating the motion of Bi Tu moving backwards.

That scene made all the people on the ground, who were already taken aback by the blood moon in Su Ming's eyes to begin with, become even more shocked by the strongest battle in the sky.

"Retreat!"

A brilliant light flashed through Nan Song's eyes. He swung his arm and led the Berserkers from Dark Mountain Tribe by his side in a quick retreat. As they fled, the nine people from Black Mountain Tribe quelled the shock they felt and no longer looked at the sky as they rapidly gave chase.

Once they were thousands of feet away, Nan Song bit his tongue and coughed out a mouthful of blood. The blood turned into a gigantic arm, and it swung against the nine people from Black Mountain Tribe chasing after them.

Thunderous sounds echoed in the air, and the earth trembled. The giant arm of blood shoved their pursuers from Black Mountain Tribe 500 feet backwards.

"I can feel it. There are still some Berserkers from Black Mountain Tribe coming towards us... I'll cast a Berserker Art. Protect me and stall for time!" As Nan Song spoke, he sat down on the ground cross-legged and closed his eyes. His Qi disappeared at that instant, but the blood veins on his body began to twist strangely as if about to form a picture.

Bei Ling carried his father. He no longer had any strength to continue fighting. Even running was difficult for him. As for the Head of the Guards, he was forcing himself to stay awake, but judging by his looks, he would not be able to stay conscious for much longer due to the loss of his legs.

Lei Chen struggled down from Su Ming's back. Compared to Bei Ling and the others, while he might also be running dry, he could still fight, and he stood beside Nan Song to guard him.

At that moment, besides Su Ming, there was another man who was in his thirties who could still fight. His face was pale, and his left arm a bloody stump, but he held tightly onto a long spear with his right hand. He cast a glance at Su Ming, then with him, stood at the forefront.

"Su Ming!" from behind Su Ming came the weak voice belonging to the Head of the Guards. "I give you this bow!"

When Su Ming turned around and looked, the Head of the Guards was staring at him. He motioned for Bei Ling to take down the bow and threw the three remaining arrows towards Su Ming.

"From now on, you are the Head of the Guards of Dark Mountain Tribe! I've seen your skills with the bow before, you're very good..." The Head of the Guards gave a weak smile and closed his eyes slowly. He did not die, but simply could not stay conscious anymore and fainted.

Su Ming took the bow and arrows. The bow was very heavy, and there was a malicious air coming from it. There was also a lot of blood staining it. Once she held it in his hands, he silently shifted the quiver behind his back. He gave a nod to Bei Ling and turned towards the people from Black Mountain Tribe, who were blocked by the giant hand made from Nan Song's blood.

Time passed by quickly. As they breathed, a horrific presence slowly built up within Nan Song. They could all tell that once he finished preparing and eventually cast the Berserker Art, the effects would be shocking.

Yet at that moment, cracks appeared on that gigantic hand of blood. The nine people from Black Mountain rushed out with savage looks on their faces, charging towards Su Ming and the tribe member standing beside him.

A murderous look appeared in Su Ming's eyes. He lifted the bow with his left hand, and with his right brought out an arrow from his back before drawing the bowstring. The bow echoed and the bowstring curled into the shape of a full moon. An indescribable presence erupted forth from Su Ming, and all his blood veins manifested on his body with a roar, all his power being focused on the arrow. He let go, and a sharp cry shook the air as the arrow flew.

With an air of madness that spoke of certain death, the arrow sliced through the air with a piercing cry and charged forward, closing in on one of the nine people from the Black Mountain Tribe in an instant.

Su Ming knew that he could not waste even a single arrow. That was why he did not shoot the arrow towards the tribe leader of Black Mountain Tribe, neither did he shoot it at Bi Su. Instead, he shot the arrow towards the only person from Black Mountain Tribe who was at the fifth level of the Blood Solidification Realm.

The arrow flew out and abruptly turned into a dark ray of light, piercing the target's chest in the blink of an eye. His chest immediately burst apart. The man staggered back several steps with the arrow protruding from his chest, and then fell.

That same moment, Su Ming brought out the second arrow and drew the bow. The remaining eight people from Black Mountain Tribe were already only 300 feet away from him. They would be able to close in on Su Ming before he could even fire the arrow.

Yet at that moment, the young adult standing by his side laughed loudly and charged forward. As he got closer to the men from Black Mountain Tribe, without any hesitation, he made all his blood veins swell, and his body began letting off a blinding red light. He was going to self-destruct!

He would make his body explode to hold back those from Black Mountain Tribe so that Su Ming could have as much time as he needed to draw his bow. Su Ming was silent. He would use his actions to show his grief and anger at his tribe member's sacrifice. When the second arrow shot out, he heard a bang, and knew that his tribe member had died.

It was not as if the man in his thirties did not value his life. Yet if he compared his life with those of the people in the tribe, then he would choose his tribe's safety over his own. As he self-destructed and the blasting sounds echoed through the air, the eight people from Black Mountain were held back for the span of three breaths!

During those three breaths, Su Ming had already fired the second arrow and once again shot through the heart of another person from Black Mountain Tribe. That person coughed out blood as his breath stilled, and he died.

At the same moment the second person died, Su Ming fired the third arrow as the explosions caused by his tribe member became weaker!

He did not look at who he shot when the arrow left the bow. Instead, he slung the bow across his back and charged forward without hesitation. A red light flashed on his right hand, and Blood Scales materialized in his hand.

Su Ming remained silent and did not roar. He dashed forward, instead, without hesitation. Behind him was Nan Song, who was preparing a powerful Berserker Art, Lei Chen, who did not have much strength left to fight, Bei Ling, who was heavily wounded, and the Head of the Guards, who was unconscious. The only person who could fight now was him.

He could not turn away. He could only move forward! His vision was becoming blurry. The arrow that had penetrated his chest was still there. He could pull it out. But once he did, his injuries would worsen. Besides, the internal injuries he sustained from before by forcefully raising his level of cultivation had begun to show its effects.

He charged forward towards his destination. Including the tribe leader of Black Mountain Tribe, there were six people left before him! These six people all had various injuries on them, but they were still madly closing in on him.

Lei Chen clenched his fists but held back because he knew that he was the last line of defence. Even if he died, he had to die there. He took a few steps forward and stood before Nan Song. As he looked at Su Ming fighting, tears fell from his eyes.

'Su Ming, you said before that I can't die. If I wanted to die, we'll die together..! I'll keep to that promise..!'

There were no loud booming sounds, as if Su Ming had become mute. Yet every single time he made a move, the ruthlessness of his actions far surpassed the viciousness that someone his age should possess. He held the long spear and fought against the tribe leader of Black Mountain Tribe!

The tribe leader from Black Mountain Tribe was a powerful Berserker at the eight level of the Blood Solidification Realm. It could even be said that he was slightly stronger than Ye Wang. He may be injured, but he was still someone whom Su Ming could not hope to oppose. The moment they engaged each other in battle, blood flowed out of the corners of Su Ming's mouth. He suffered a direct punch from the tribe leader on his person, but his body twisted oddly, and he swept the long spear in his hands sideways. His target was the savage looking person by his side.

That person was a Berserker at the sixth level of the Blood Solidification Realm. He was originally grinning viciously by the tribe leader's side. He could already imagine Su Ming's body blowing apart at the next moment, but he was not meant to see that sight. Blood Scales closed in on him with a whistle. As that person stood there, stunned, it went straight through his right eye. With a bang, he was impaled to the ground.

Blood spilled out of Su Ming's body. He tumbled backwards and fell to the ground. Just as the remaining five people from Black Mountain Tribe were about to leap over the body of their dead comrade and charge towards him, Su Ming struggled up silently. He smiled brokenly and spread his arms wide open. Moonlight descended on him from the sky and turned into fine threads that surrounded his body. He flung it outwards, and those threads rushed towards the five people.

A murderous look appeared in the tribe leader's eyes. He pushed Bi Su aside with his right hand, causing Bi Su to use that momentum to charge forward and rush towards Lei Chen with the intent to kill.

The tribe leader himself growled. As blood red light erupted from his body, the shape of a bloody bear about 100 feet tall appeared behind him. That was the transfiguration of his Mark of Calamity, which had yet to solidify. The moment it appeared, it let off a loud roar that shook the skies, and its body blocked the thread of moonlight that Su Ming flung out.

Nonetheless, the tribe leader underestimated Su Ming's unique skill. It was an especially glaring mistake during the moon of that day. It might not be full, but it was already close. The instant the might of the moon touched the blood bear, it tore through its body, causing the bear to let out a sharp cry. Yet it only made a bright flash appear in the tribe leader's eyes. The blood bear exploded, the force created by the explosion not only caused the thread of moonlight to crumble, it also lashed through its surroundings and crashed into Su Ming, causing his body to be thrown into midair as he coughed out blood.

Su Ming was beginning to fall unconscious while midair. He saw dozens of new Berserkers from Black Mountain Tribe charging through the forest towards them. He saw Lei Chen standing before Nan Song, roaring as he dashed out towards his opponent – the cruel Bi Su.

'Is this the end..? But I... can still fight... I still have one more arrow!'

It was as if everything slowed down. He could no longer hear anything, but his eyes were trained onto Bi Su, who was closing in on Lei Chen. As he surrounded himself in moonlight, Su Ming grabbed the bow with his left hand and the arrow on his chest with his right hand. He pulled it out viciously, and his pain turned into killing intent. As blood poured out from his body, he notched the bloody arrow on the bow and aimed it at Bi Su. Then with a vicious might, he fired the arrow!
""",
                         chapter.content.text)


if __name__ == '__main__':
    unittest.main()
