from typing import List

from lightnovel.test.test_config import HarTestCase, Hars
import lightnovel.wuxiaworld as ww


class WuxiaWorldApiHjcTest(HarTestCase):
    @classmethod
    def get_har_filename(cls) -> List[str]:
        return Hars.WW_HJC_COVER_C1_2.value

    def test_parsing_novel_hjc(self):
        api = ww.WuxiaWorld(self._request)
        novel = api.get_novel('heavenly-jewel-change')
        self.assertIsNotNone(novel)
        self.assertEqual(novel.title, 'Heavenly Jewel Change')
        self.assertEqual(novel.translator, 'Stardu5t')
        self.assertEqual(novel.first_chapter_url, 'https://www.wuxiaworld.com/novel/heavenly-jewel-change/hjc-book-1'
                                                  '-chapter-1-01')
        self.assertListEqual(novel.tags, ['Chinese', 'Ongoing'])
        self.assertEqual(novel.img_url, 'https://cdn.wuxiaworld.com/images/covers/hjc.jpg?ver'
                                        '=f83790a5f2ff64bb6524c2cfd207845ba1d25ac6')
        self.assertEqual(novel.url, 'https://www.wuxiaworld.com/novel/heavenly-jewel-change')
        self.assertEqual(novel.description.text, "\n[Zen’s Synopsis]In a world where power means everything, "
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
        self.assertEqual(len(book.chapters), 697)

    def test_parsing_chapter(self):
        api = ww.WuxiaWorld(self._request)
        chapter = api.get_chapter('heavenly-jewel-change/hjc-book-1-chapter-1-01')
        self.assertIsNotNone(chapter)
        self.assertEqual("Chapter 1 – Big Sis, I’m afraid this is a misunderstanding! (1)", chapter.title)
        self.assertEqual('https://www.wuxiaworld.com/novel/heavenly-jewel-change/hjc-book-1-chapter-1-01', chapter.url)
        self.assertEqual('Stardu5t', chapter.translator)
        self.assertFalse(chapter.is_teaser)
        self.assertEqual('', chapter.previous_chapter_path)
        self.assertEqual('/novel/heavenly-jewel-change/hjc-book-1-chapter-1-02', chapter.next_chapter_path)
        self.maxDiff = None
        self.assertEqual("""
Heavenly Bow Empire Capital City, Heavenly Bow City, Official Roads.

Heavenly Bow Empire is a small country in the western regions of Boundless Mainland (Hao Miao Da Lu). It isn’t bound to any larger countries, and its environment and climate are extremely suitable for humans to live in.

The weather was great today, the vast expanse of the sky seemed like a large blue crystal, with nary a blemish in sight. The only issue one might find would be that the clarity of the air caused the sunshine to be rather glaring on the eyes. Luckily, the official roads were lined with 100-year or older Sycamore Trees, their thick branches massed with leaves sheltering the wide roadways. This formed the famous boulevard which everyone in Heavenly Bow Empire knew about, stretching for nearly 100 li (50km) into a forest.

Heavenly Bow City had a very unique geographical location, in fact it could be almost described as second-to-none. This was because this capital city was totally surrounded by huge forests, and Heavenly Bow City was just like a brilliant jewel in the midst of the forest. Although Heavenly Bow Empire wasn’t particularly strong, its capital city was still quite famous. The surrounding forests were called Stars Forest, because this was the only place in the whole continent where the Stars Trees grew. The heart of the Stars Trees were extremely valuable materials in making top end bows. As such, with such an important natural resource, one could imagine the prosperity that Heavenly Bow City enjoyed.

Currently, a youth who looked around 15-16 years old was walking along the boulevard, muttering to himself.

“To be a playboy is to train the mind, to have an affair is to train the heart, chasing after girls will prevent old age, flirting is therapeutic, having a crush on someone means your heart will always be young, being lovesick is the cure for insomnia!

They often say that Heroes are unable to cross the beautiful maiden barrier [1. It's a chinese saying that means heroes are often susceptible to a pretty face, causing them to be fallen.], but what hero will think like this? Should the hero leave the beauty to some useless fellow? And what would the beauty think, wouldn’t she prefer to have the hero instead as well?

Another saying is that Rabbits don’t eat the grass near their nests [2. Literal translation of another Chinese idiom, it means that even villains won’t commit sins close to home. However his rant here is talking on the literal meaning of it.], but why would rabbits do that? Should they let other rabbits eat the grass? Even the grass won’t think like that, after all being eaten is being eaten, does it matter by whom? Why not let someone familiar eat them!

Yet another saying is that if you have money, you can make the devil push the millstone for you [3. Money makes the world go round], but the devil would think that it’s a given thing – after all shouldn’t labour of pushing the millstone be rewarded? Even money would think differently, after all, being given to the devil will not harm the devil, but if given to humans the scenario might be different! Hahahaha…”

The youth was tall, with broad shoulders, with a healthy strong look. He had black eyes and hair, and was dressed in a cloth shirt with its sleeves rolled up, showing off his arms. His skin colour was a healthy sheen of bronze, and his features had a heroic spirit within. He might not be very handsome, but was overall pleasing to the eye. Just judging by outward appearance, the words simple and honest would be an apt description. However, the words that streamed out from his mouth were the total opposite of simple and honest. Of course, he only revealed his true colours when there was nobody else around.

“Sigh… not being able to cultivate heavenly energy is such a tragedy. In today’s day and age, looking good is useless, only heavenly energy and heavenly jewels are king. Ahhhh… Heavens! Earth! Gods! Why do you play me like this, letting I, Zhou Weiqing, be born with such a body with blocked meridians yet such a handsome face? Not letting me be a Heavenly Jewel Master is such a waste of great talent ah!” Of course, the handsome face he referred to was only of his own belief, and as he spoke the youth rudely gave the sky the finger.

Of course, he wasn’t the sort to just blame heaven, after pointing the middle finger he said comfortingly to himself: “Oh well, not being able to cultivate Heavenly Energy has its good side as well. That old geezer is already so strict, if I really awakened a Heavenly Jewel, maybe my life would be worse now by a hundred times? At least now the old geezer has given up on me, and leading the decadent life of a rich official’s son seems not a bad choice. I’ll go take a bath now!” As he spoke, his face revealed his trademark honest smile. Of course, those who really knew him, Zhou Weiqing’s honest smile hid his true rascally nature.

Even though Zhou Weiqing was unable to cultivate heavenly energy, his youthful body was still extremely healthy and strong. He was only 13 years old this year, and yet he looked like a youth of 15 – 16. At least in this, he was following in his father’s footsteps.

After walking about 5 li along the boulevard to the Stars Forest, Zhou Weiqing suddenly swerved into the woods. He had grown up in the woods, especially ever since he was 8 years old when he had tested out to have his meridians blocked and unable to cultivate heavenly energy. Zhou Weiqing’s father no longer forced him to train, so his favourite thing to do was to run alone into the forest to play. There were no Heavenly Beasts in the Stars Forest, and it was one of the safest forests on the continent.

After entering the Stars Forest, Zhou Weiqing could practically navigate his way around with his eyes closed, after all he knew the place like the back of his hand. After walking for about an hour, he finally heard sounds of running water as he neared his destination. Thinking about the sweet, clear lakewater, Zhou Weiqing hastened his steps. It was a hot day and he was eager to relax in the cooling waters of the lake.

Not far from the path in the Stars Forest there lay a lake, and its waters originated from an underground ice spring. It was only about 100m in diameter, and was surrounded by large thick trees. As a result, not many people knew about this lake, but Zhou Weiqing had came across it by accident in the past. He had a natural liking for water and since he had no friends, he spent a lot of time bathing and relaxing in the lake.

Moving around a large tree, the Ice Spring Lake was right ahead. Zhou Weiqing did not rush to dive into the waters, but first took off his clothes and laid them at the side, before squatting down at the edge of the waters to look at his reflection, muttering to himself: “Damn! I’ve become more handsome again!”

Just as he was reflecting on his own looks narcissistically, he suddenly heard a splash, causing him to look up, and the sight that greeted him caused him to gape in surprise.

From the other end of the lake, someone else had just jumped into the water, causing the waters to splash out. As the rays of sunshine shone upon the lake, the refraction of light causing the area to seem to be bathed in gold. In the midst of the water ripples, a head of pink hair captured Zhou Weiqing’s attention.

The Ice Spring Lake’s water was pretty shallow, only a metre or so deep, and the young girl who had leapt into the lake had her back facing Zhou Weiqing, and the lake waters just covered her buttocks. Still, Zhou Weiqing was able to see her slim waist and alluring figure.

“This… this…”

With a light *pooh* sound, 2 lines of blood streamed down from Zhou Weiqing’s nostrils. Even though this fellow often had sexual fantasies, he was after all still a 13 year old virgin boy, no matter how precocious. Seeing a naked young girl at such close proximity for the first time was so exciting to him that his nose started bleeding.

“Wow, this is so awesome!” Zhou Weiqing quickly held his nose, but his eyes kept staring at the girl, completely forgetting how exposed he was to being found, he could only chant in his mind Turn around! Turn around!

As if the pink haired girl had heard his internal prayers, she actually slowly turned around, she seemed excited and her hands were on the top of the water as she turned towards Zhou Weiqing.
""".replace('\n', ''),
                         chapter.content.text)
