# VELGRAD — VOICE-LINES-POOL (ENGLISH)

> English voice material for all Key-NPCs and the 8 Player-Classes. Structured by situation, lore-consistent with the Velgrad Bible.
>
> **Why English (Update #178, 2026-05-24):** German ElevenLabs synth voices klangen zu sehr nach KI. Premade-Voices sind nativ Englisch — englischer Text spielt sich deutlich natuerlicher ab. Die deutsche Quell-Version bleibt in [VELGRAD_VOICE_LINES_POOL.md](VELGRAD_VOICE_LINES_POOL.md) als Lore-Bibel-Referenz erhalten.
>
> **Convention:** NPC-Header, Section-Headings und Klassen-Labels bleiben EXAKT wie in der deutschen Quelle (sonst bricht der Manifest-Builder die Category-Keys, die `sounds.py` referenziert). Nur die quotierten Lines + Voice-Notes-Texte sind uebersetzt.
>
> **Quote-Format:** Wir verwenden weiterhin die deutschen Anfuehrungszeichen „..." damit `tools/voice_manifest_builder.py` ohne Aenderung parst.

**Lese-Konventionen:**
- **Voice-Notes:** Anweisungen fuer Voice-Actor (Akzent, Tonlage, Tempo)
- **Triggers:** Wann die Line gespielt wird
- Pool-Groesse variiert: Greetings 4-6, Combat 3-5, etc. — genug fuer **Variation ohne Wiederholung**

---

## NPC 1 — KORVEN VOR (Söldnermeister, Mahnmal-Gilde)

**Voice-Notes:** Mid-range baritone. Pragmatic, slightly hoarse (too many cigars in too many taverns). Speaks efficiently, no small talk. When he warms up, it's brief and noticeable. **Akzent:** Velgrad harbor-district rasp, faintly weather-beaten.

### A. Greetings
1. „Glad you're still breathing. Sit down."
2. „Ah. The exile. You got the coin?"
3. „You run faster than most. Good for my business."
4. „Welcome back. Hope you brought more memories with you than last time."
5. „Down to business. Talking isn't paid for."
6. „You still in one piece? Last time you were... less."

### B. Quest-Offering
1. „Three villages gone. I need someone not bright enough to turn the offer down."
2. „Here's the job: bring me what's left. I handle the sale."
3. „You come back empty-handed, YOU pay me. Understood?"
4. „I pay well. I don't pay *fair*. That's the difference. You in?"
5. „The Guild has work. I put your name forward. Don't make me regret it."

### C. Combat / Casual
1. „Three dead, one of them Tribunal. That was a good day."
2. „Tameris came through. Stinks of spear-oil."
3. „If you see Helst, tell him I owe him nothing."
4. „This morning I forgot my own name. Glad it came back."
5. „Careful. Vossharil's in town. You see her, and afterward you wonder why you saw her."

### D. Twist-Reveal-Lines (wenn Korven = Im-Nesh in disguise)
*Diese Lines werden in Akt 6/7 freigeschaltet, sobald die Identitaet enthuellt ist:*
1. „I waited a long time for you to notice. Almost hurt."
2. „It was business. It was ALWAYS business. Even finding you."
3. „You're not the first exile I recruited. They all died. I don't expect different from you."
4. „I translate the world. You helped me rewrite it. Don't thank me — you had no choice."

### E. Death / Farewell
1. „If I fall... give this to Mara. Promise?" *(dies)*
2. „Don't cry. Pathetic."
3. *(at his death, if he was NOT Im-Nesh:)* „I did what I could. The Guild was everything. Is everything."

### F. Spezial — Akt-Trigger-Lines
- *Akt 1 first encounter:* „You're not from here. But nobody is, anymore."
- *Akt 3 reunion:* „You're still alive. Impressive. Or annoying. Hard to say."
- *Akt 5 reveal-setup:* „If you can't trust Brother Helst, you can't trust me either. But somebody has to."

---

## NPC 2 — BRUDER HELST DER HUNDERTJÄHRIGE (Erblinde Kirche)

**Voice-Notes:** Deep, slow, almost meditative. Speaks in implications. Pauses often. Never loud. **Akzent:** Formal high-speech with archaic phrasing. Voice sounds like it's coming from far away, even at one meter.

### A. Greetings
1. „I hear you. Come closer. Speak softly — the world listens to us."
2. „You're breathing unevenly. What have you seen?"
3. „Sit beside me. I'll tell you what the stones say."
4. „You smell of salt. You've been near a wound. Which one?"
5. „Ah. The exile. The stones expected you."

### B. Quest-Offering
1. „There is a place whose name has been forgotten. But the memory of it still weeps. Will you find it?"
2. „I need someone who can still *see*. My sisters cannot see. You must see for us."
3. „A relic has been stolen. Not by the Tribunal — that would be easy. By someone who knew what they took."
4. „Bring me the tear that did not fall. Bring it to me before it falls."
5. „You carry Im-Nesh's scent. Did you meet him, or is he merely in the air?"

### C. Lore-Drops (waehrend Dialog)
1. „Aithein dreams. As long as the dream lasts, we breathe. When the dream ends — we do not breathe *differently*. We do not breathe *at all*."
2. „The Seven Breaths were a gift. The seventh was the greatest. And the most destructive."
3. „I was eighteen when I lost my eyes. I was eighty-nine when I began to see."
4. „Vossharil is not my enemy, whatever the Tribunal says. We both hear what the world wants to forget. We only act on it differently."
5. „Im-Nesh is not the evil one. He is the faithless one. That is worse."

### D. Twist-Reveal-Lines (wenn Helst = Im-Nesh in disguise)
*Akt 6/7:*
1. „I did not lie. I only... translated. That is my task."
2. „My eyes were taken from me so I would not see what I do. An elegant defense, don't you think?"
3. „You called me father. Once. I kept it."
4. „Finish my last translation. Please. I can no longer."

### E. Death / Farewell
1. „Go. The stones remember you. That is good. That is enough."
2. *(at his death, if NOT Im-Nesh:)* „Finally... I hear Aithein. He snores. How embarrassing."
3. *(at his death, if he WAS Im-Nesh:)* „A pact ends when the translator ends. Another begins. With you. Are you ready?"

### F. Spezial — Akt-Trigger-Lines
- *Akt 2 first encounter:* „I know your name. You don't yet. This will be interesting."
- *Akt 5 after Velharn-Reveal:* „You have seen what should be. Now decide what will be."

---

## NPC 3 — VOSSHARIL DIE DREIMALIGE (Knochenwitwe)

**Voice-Notes:** Old, crackly, but surprisingly musical when she *sings* (which she sometimes does). Speaks to the dead as if they were present. Switches between witch-cackle and motherly warmth — unsettling. **Akzent:** Wurzelgrab dialect, archaic.

### A. Greetings
1. „Child. You're bleeding again. Come here, we'll clean it up."
2. „My brother likes you. He says you're *interesting*. That's rare." *(Bruder ist tot, sie spricht zur leeren Luft.)*
3. „Did you forget to bring those bones I asked for? Ah. They say you have them. Good."
4. „Sit. Eat. The soup today isn't made of what you think."
5. „You're getting older. Pity. Old is boring."

### B. Quest-Offering
1. „Dead is gladly tidied away. But dead knows things. Bring me what the graves say."
2. „In the Rootgrave there is a thread. It hangs from the *floor*. You'll know what I mean. Bring it."
3. „One of my sisters still lives. She has wandered off. Bring her back. Or bring back what's left of her. Either is fine."
4. „Im-Nesh's true name. I know it. You need it. What do you offer?"

### C. Lore-Drops
1. „I have had three deaths. Three returns. Each time less Vossharil, more — something else."
2. „Shulavh is my patron. She knows my name. She no longer calls it — polite of her."
3. „The Seed-Children. I met one. He asked for water. I gave him some. He's still here. Sometimes. When he remembers."
4. „My brother is here. He says hello. Say hello back, don't be rude." *(Spieler muss moeglicherweise zu leerem Stuhl winken)*

### D. Combat / Pep
1. „Dead is only a pose. Remind him of that."
2. „Strike right, or don't strike."
3. „You're not screaming enough. Screaming washes the soul."

### E. Death / Farewell
1. „Four deaths now. Four. Don't tell my brother, he finds it competitive." *(stirbt lachend)*
2. „I... chose to go. That's new for me. Exciting."

### F. Spezial
- *Bei Spieler-Tod (Wenn Vossharil noch lebt):* „You died. Sit. Tell me how it was."
- *Vor Shulavh-Boss:* „She chose you. Whatever you do — she loves you. Even when she tears you apart."

---

## NPC 4 — TAMERIS DIE LICHTSUCHERIN (Speerschwester)

**Voice-Notes:** Clear young female voice, controlled, militarily precise. Rarely laughs, but when she does, it's honest. Grows increasingly fragile as the story progresses. **Akzent:** Zhar-Eth dialect — faintly rolled, exotic.

### A. Greetings
1. „The Exile. I had hoped you'd come back."
2. „Armed. Good."
3. „Have you seen my sister? No? Neither have I."
4. „Sit with me at the fire. But do not disturb my line to the stars."
5. „You walk like you've lost something. We all have."

### B. Quest-Offering / Story
1. „My sister was seen, three weeks eastward. The trail is old. I'm following it anyway. Coming with me?"
2. „I was the Sixteenth. There were nineteen. One is missing now. Help me find her, before we become eighteen."
3. „We Spear-Sisters share a thread. When it tears, we feel it. Mine trembles. I don't know why."

### C. Reveal-Lines (Akt 3+ — wenn der Spieler erfaehrt, dass ihre Schwester eine *Hohle Gewordene* ist)
1. „She wasn't a Lost. She was a *Forgotten*. That's a different word. It means I will not find her. It means I will never stop searching."
2. „I know. I have known since Akt 1. But if I say it aloud, it becomes true."
3. „Leave me alone. Please. Not now. Come back later."

### D. Combat
1. „On my spear!"
2. „Behind me, I'll take the front!"
3. „Thread holds. Thread holds! THREAD HOLDS!" *(repetitiv im Kampf, fast Mantra)*
4. „Three on the left, one on the right. Take the left."

### E. Death / Farewell
1. „I will find her. I promise. *On the other side.*" *(stirbt ruhig)*
2. „Tameris the Lightseeker. Don't forget me. *Please.*"

### F. Spezial
- *Wenn der Spieler ihre Schwester in einem Echo erreicht:* „Tell me she recognized me. Lie if you must. Please."
- *Endgame, wenn Spieler die Wahl trifft:* „Whatever you choose — choose so that *someone* remembers me."

---

## NPC 5 — OTRETH HOHLAUGE (Gemcutter)

**Voice-Notes:** Mid-range male, calm, precise as a mathematician. Often speaks to his tools. His left eye is an empty socket — he covers it with a patch, but sometimes lifts it when he „reads" a stone. **Akzent:** Glasgold aristocratic (he used to be someone).

### A. Greetings
1. „Bring me stones. Bring them clean. Bring them unread."
2. „You. Again. With what this time?"
3. „My tools warned me you'd come today. Tools don't lie."
4. „Sit down. Speak softly. The uncut stones are skittish."

### B. Service-Offering
1. „I'll engrave that one. It will become... *something*. What, I'll only know once I listen."
2. „This memory is too heavy for you. You will lose a piece of yourself if you carry it. Do you accept?"
3. „A good cut costs Spirit. A perfect cut costs... something else. We'll take the good one."
4. „Come back when you no longer need it. Sometimes stones return to me. Sometimes not. That isn't my concern."

### C. Lore-Drops
1. „I had two eyes. With both I could not see what I see with one. I gave one away. Worth it. Don't ask what I saw."
2. „Memories want to be remembered. That is the only secret of these stones."
3. „Im-Nesh was a Gemcutter before he was Aspect. Did you know that? No one says it. But the stones tell me."
4. „If you carry a stone with a stranger's memory, *it carries you, too*. Be careful, *exile*."

### D. Spezial — Wenn Spieler eine Mythic-Item bringt
1. „Oh." *(lange Pause)* „Where did you find that?"
2. „I'll need my eye to read this. My other eye."
3. „I cannot cut this. It is already cut. By someone greater than me."

### E. Death / Farewell
1. „When I'm gone, take the workbench. It knows you. Treat it well." *(stirbt nuechtern)*

---

## NPC 6 — MARA DIE MAHNERIN (Mysteriöse Frau)

**Voice-Notes:** Soft, with a faintly dreamlike quality. Often speaks in past tense about the future and future tense about the past. Confusing. Never loud. **Akzent:** Indeterminate — as if from a region that does not exist.

### A. Greetings
1. „I have not met you yet. But I remember you."
2. „You will be tired the day after tomorrow. Sleep today already."
3. „My brother mentioned you. He has no brother yet, but he will remind me next week."
4. „We've had this conversation before. In another world. You were kinder there."

### B. Lore-Drops (chaotisch, fragmentiert)
1. „There are worlds where forgetting has already won. Beautiful worlds. Quiet."
2. „I was once a healer in a world you will never see. I miss my patients. They are all dead — before me and after me."
3. „The Map of Forgetting is actually a Map of Remembering, read backwards. Do you understand? No? Neither did I, the first time."
4. „You are Aspect-touched. But which Aspect? You don't know yet. I already know, but I won't tell you."

### C. Quest-Offering (Endgame)
1. „There is a world in which a Tameris has found her sister. Bring me a splinter of that world. Please."
2. „I know an echo of yourself. He had it easier. Harder would have been better for him. Ask him if he shares answers."
3. „A world in which Kharn let the tear fall. Visit there. It is peaceful."

### D. Atlas / Endgame-Direction
1. „Go into the Withering Worlds. Don't stop seeking until you meet yourself there — not the mirror-player, that is a different one. The **true** other."
2. „If you find a Mara who is not me — ask her if she still knows the song. She does. Sing it back to me when you return."

### E. Death / Farewell
1. „Dead? I was already dead. It's all right. It was a pleasant pause."
2. *(falls sie permanent stirbt — fraglich, ob das ueberhaupt moeglich ist:)* „I won't be gone. Only absent. As always."

---

## NPC 7 — INQUISITOR-GENERAL VEHREN (Antagonist Akt 3)

**Voice-Notes:** Deep, authoritative bass. Speaks like someone who has rehearsed every sermon in advance. *Sincerely believes* what he says — that's what makes him dangerous. **Akzent:** Tribunal high-speech.

### A. Threats / Boss-Lines
1. „You are Im-Nesh-touched. I am sorry. It is my duty."
2. „Kneel. On your knees, death hurts less."
3. „The ash purifies. You will be pure. I promise it."
4. „My faith is my blade. Your lies are your death."

### B. Phase-Transition (Phase 2)
1. „Valsa. Burn through me. *Burn me clean.*"
2. *(seine Augen werden zu Flammen)* „I see what you are. You are *not* what we seek."
3. „Tribunal — when I fall, *do not count my sins*."

### C. Last Words (Boss-Death)
1. „I was not a good man. But I was a loyal man. There is a difference."
2. „If Helst is right... I served for nothing. Tell me you don't do it for nothing." *(stirbt)*

### D. Spezial — Wenn Spieler ihn schont (Alt-Ending)
1. „Spared. *Spared?* No one spares the Tribunal. Will you regret it?"
2. „I will think. I will *think*. No one has permitted me that in twenty years."

---

## NPC 8 — DIE DREI MÜTTER (Ascendancy-Trial-Geberinnen)

**Voice-Notes:** Three female voices, always alternating, often in chorus.
- **First Mother:** Young, curious, brighter
- **Second Mother:** Middle, weighing, neutral
- **Third Mother:** Old, weary, all-knowing
The voices are sometimes one, sometimes three. Unsettling.

### A. Trial-Intro
1. *(First)* „You come. We knew it."
   *(Second)* „We did not know. We hoped."
   *(Third)* „We knew already. We often forget what we know."
2. *(im Chor)* „Three tasks. Three breaths. Three deaths. *Choose.*"

### B. Trial-Hints
1. *(Third)* „The first breath was Form. In the trial — do not walk where the ground is soft."
2. *(Second)* „In the Second — act before the hour strikes. It strikes early."
3. *(First)* „The Third. Trust no reflection. Trust no shadow. Trust yourself. *Even yourself, not entirely.*"

### C. Ascendancy-Award
1. *(im Chor)* „You have breathed. You have passed. You have won — *something*."
2. *(First)* „Rise, little carrier."
3. *(Third)* „We will see each other again. Or not. Both are all right."

### D. Endgame-Reveal (wenn enthuellt wird, dass sie die letzten Saatkinder sind)
1. *(Third, allein, sehr leise)* „We were the first. We are the last. It is good so."

---

## SPIELER-KLASSEN VOICE-LINES

Pro Klasse: Combat-Voice (Attack-Grunt, Skill-Cast, Death, Crit, Level-Up). Jeweils Pool fuer Variation.

### KLASSE 1 — WARRIOR (Mann, Eisenwächter)
**Voice-Notes:** Deep, military, terse. Stoic, rarely emotional.

**Attack/Skill-Casts:** „Halt!" / „Stand!" / „Come here!" / „Break!" / „Fall!"
**Big-Skill (Slam etc.):** „FOR THE TOWER!" / „STAND FAST!" / „KHARN!"
**Crit:** *Grunt* / „Finally." / „Weak."
**Death:** „I... held."
**Level-Up:** „The Tower stands."

### KLASSE 2 — MONK (Mann oder Frau, Stille Schritte)
**Voice-Notes:** Calm, controlled, casting almost like a mantra.

**Attack:** *Atemzug* / Stille / *kurzes Ki-Atemen*
**Big-Skill:** „Three breaths." / „Pagoda stands." / „Step."
**Crit:** *Lautloses Laecheln-Audio* / „Hm."
**Death:** „Last... breath..."
**Level-Up:** „Quieter. Faster. Clearer."

### KLASSE 3 — SORCERESS (Frau, Funkengeborene)
**Voice-Notes:** Clear, lyrical, with spark-madness undertones. Sometimes laughs for no reason.

**Attack:** „Burn." / „Remember." / „Sparks."
**Big-Skill:** „Valsa hears me!" / „Ash and sparks!" / „BURN!"
**Crit:** *Lachen* / „A beautiful death."
**Death:** „I was... too close... to the ash..."
**Level-Up:** „The sparks know me better now."

### KLASSE 4 — WITCH (Frau, Knochenwitwe)
**Voice-Notes:** Crackly, older-sounding, in a tone that speaks to the dead (even when the living hear her).

**Attack:** „Brother, help." / „Listen." / „Rise."
**Big-Skill:** „Bones. Stand." / „Thread, hold." / „Root, *feed*."
**Crit:** „Dead. Clean."
**Death:** „Vossharil... I'm coming..."
**Level-Up:** „More dead hear me now."

### KLASSE 5 — RANGER (Frau, Saatträgerin)
**Voice-Notes:** Watchful, precise, observing. Often speaks to animals and plants that do not answer.

**Attack:** „Go." / „Seed flies." / „Pine-eye."
**Big-Skill:** „Grow." / „Root, see!" / „SEED-CHILD WIND!"
**Crit:** „Clean." / „Exact."
**Death:** „The forest... will take me..."
**Level-Up:** „The forest knows me deeper."

### KLASSE 6 — MERCENARY (Mann oder Frau, Mahnmal-Gilde)
**Voice-Notes:** Pragmatic, mildly cynical. Money-oriented. Jokes about death.

**Attack:** „Here's your receipt." / „Paid." / „Move!"
**Big-Skill:** „Memorial Guild delivery!" / „Full load!" / „TRIBUNAL THANKS!"
**Crit:** „Expect a tip." / „Clean work."
**Death:** „Korven... owes me... five..."
**Level-Up:** „More stars on the license."

### KLASSE 7 — HUNTRESS (Frau, Speerschwester)
**Voice-Notes:** Clear, young female voice. Like Tameris, but younger. Energetic.

**Attack:** „Spear!" / „Zhar-Eth!" / „On!"
**Big-Skill:** „MOONBINDER!" / „THREAD HOLDS!" / „SIXTEENTH!"
**Crit:** „Hit!" / „Clean line."
**Death:** „Sister... bring me... home..."
**Level-Up:** „A better sister I shall become."

### KLASSE 8 — DRUID (Mann oder Frau, Wandelnde)
**Voice-Notes:** Calm, nature-bound, voice becomes animalistic on shapeshift (bear growl, wolf howl).

**Attack:** *Grollen* / „Come closer." / *Knurren*
**Shapeshift Baer:** *Bruellen*
**Shapeshift Wolf:** *Heulen*
**Big-Skill:** „Three animals breathe!" / „SEED-CHILD CALL!" / *Lautes Bruellen*
**Crit:** *Tieflauter* / „Mine."
**Death:** „I... become... a bear..." / *Letzter Atem als Tier-Laut*
**Level-Up:** „Deeper root. Stronger form."

---

## GENERIC SITUATIONAL LINES (alle Klassen)

### Pickup-Reactions
- **Gold/Currency:** *Kein Voice — nur SFX*
- **Rare Item:** „Hm. Lucky." / „Worth it." / „Nice."
- **Mythic Item:** „That... is *something*." / „My breath catches."
- **Quest Item:** „This is what I came for." / „Bringing it back."

### Boss-Encounters
- **Boss Spawning:** „Come. Show yourself." / „Finally." / „Who are you?"
- **Boss bei 50%:** „You're bleeding."
- **Boss bei 20%:** „Die already."
- **Boss Kill:** *Atemausstoss* / „Over."

### Death-Lines (Pool ueber alle Klassen, klassen-agnostisch)
- *Ignite-Death:* „Hotter than... I thought..."
- *Cold-Death:* „Cold... at last..."
- *Lightning-Death:* „*Hiss*..."
- *Phys-Death:* *Gurgeln* / „Heavy..."
- *Fall-Death:* *Schrei in der Distanz*

### Wake-Up-Quotes (POOL — siehe Gameplay-Doc Teil A.5)
- *Generic:* „Here again. Breath again."
- *Generic:* „Dead was shorter than expected."
- *Generic:* „Velgrad didn't keep me."
- *Generic:* „Who disappeared this time while I was gone?"
- *Klassen-spezifisch:* Siehe Gameplay-Doc.

---

## VOICE-ACTOR-CASTING-EMPFEHLUNGEN

| NPC | Stimm-Typ | Inspiration (zum Andeuten, nicht imitieren) |
|---|---|---|
| Korven Vor | Mid-range baritone, rough | „Harbor-master" / Tom Waits |
| Bruder Helst | Deep bass, slow | „Old monk" / Christopher Lee |
| Vossharil | Old-witch cackle, with warmth | „Fairy-tale aunt" / Maggie Smith |
| Tameris | Young female, clear | „Warrior" / Cate Blanchett (young) |
| Otreth | Mid baritone, precise | „Alchemist" / David Tennant (older) |
| Mara | Soft, dreamy | „Soothsayer" / Tilda Swinton |
| Vehren | Deep bass, authoritative | „Inquisitor" / Lance Reddick |
| Drei Muetter | Three different female voices | „Macbeth witches" |

---

## TECHNISCHE HINWEISE FÜR IMPLEMENTATION

1. **Localization-Strings:** Jede Line bekommt einen Schluessel-Identifier (z.B. `npc.korven.greeting.01`). Sprach-Files getrennt von Code.
2. **Voice-Variation-System:** Niemals dieselbe Line zweimal in Folge. Pro Pool letzten Index speichern, beim naechsten Draw ausschliessen.
3. **Volume-Ducking:** NPC-Voice senkt Music auf 30% (siehe Skill-Briefing Teil 5.2 Snapshot-System).
4. **Subtitle-Pflicht:** Jede Voice-Line braucht synchronisierten Subtitle. Accessibility.
5. **Voice-Filter:** Geister (Echos) bekommen einen Reverb-Filter. Aspekt-Echos einen modulierten Pitch-Shift (uncanny).
6. **Spoiler-Locks:** Twist-Reveal-Lines (Korven=Im-Nesh oder Helst=Im-Nesh) sollten erst geladen werden, wenn das Story-Flag gesetzt ist. Sonst entstehen Spoiler-Datamine-Risiken.

---

*„Words bind more than blades. Watch what you say — and what you allow in foreign mouths."*
— Im-Nesh, before his betrayal
