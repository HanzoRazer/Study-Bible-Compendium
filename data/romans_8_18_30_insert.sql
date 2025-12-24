-- Study Bible Compendium: Romans 8:18-30 Core Sanctification Passage
-- Unit ID: SANCT_CORE_ROM_008_018_030
-- Created: 2024-12-24

PRAGMA foreign_keys=ON;

-- =============================================================================
-- CORE PASSAGE REGISTRY
-- =============================================================================
INSERT OR IGNORE INTO core_passages (unit_id, category, title, range_ref, summary_md, tags)
VALUES (
    'SANCT_CORE_ROM_008_018_030',
    'sanctification',
    'Romans 8:18-30 - Sanctification Through Groaning, Help, and Conformity',
    'Romans 8:18-30',
    'Romans 8:18-30 frames sanctification as Spirit-governed transformation toward Christ''s image. Creation groans, believers groan, and the Spirit intercedes within weakness according to God''s will-ensuring that suffering, prayer, hope, and providence converge toward conformity to the Son and final glory.',
    'sanctification,romans8,holy-spirit,prayer,conformity,image-of-christ'
);

-- =============================================================================
-- MIDRASH NOTES (verse_notes)
-- Verse IDs: 28861-28873 (Romans 8:18-30 in berean_verses)
-- =============================================================================

-- Romans 8:18 (id=28861)
INSERT INTO verse_notes (verse_id, note_kind, unit_id, title, note_md, tags, sort_order)
VALUES (28861, 'midrash', 'SANCT_CORE_ROM_008_018_030',
    'Romans 8:18-30 - Unified Midrash Unit',
    '**Midrash:** Suffering is weighed, not dismissed. Glory is revealed *to and in* God''s children-personal, not merely scenic.',
    'sanctification,romans8,glory,suffering', 10);

-- Romans 8:19 (id=28862)
INSERT INTO verse_notes (verse_id, note_kind, unit_id, note_md, tags, sort_order)
VALUES (28862, 'midrash', 'SANCT_CORE_ROM_008_018_030',
    '**Midrash:** Creation waits for the revealing of sons. Redemption is human-centered before it becomes cosmic-creation follows transformed heirs.',
    'sanctification,creation,sons,revealing', 20);

-- Romans 8:20 (id=28863)
INSERT INTO verse_notes (verse_id, note_kind, unit_id, note_md, tags, sort_order)
VALUES (28863, 'midrash', 'SANCT_CORE_ROM_008_018_030',
    '**Midrash:** Futility was imposed with a future in view. Even judgment carries a redemptive trajectory-*in hope*.',
    'sanctification,futility,hope', 30);

-- Romans 8:21 (id=28864)
INSERT INTO verse_notes (verse_id, note_kind, unit_id, note_md, tags, sort_order)
VALUES (28864, 'midrash', 'SANCT_CORE_ROM_008_018_030',
    '**Midrash:** Creation''s freedom is tethered to the freedom of glorified children. The world is healed as sons are restored.',
    'sanctification,freedom,glory,children', 40);

-- Romans 8:22 (id=28865)
INSERT INTO verse_notes (verse_id, note_kind, unit_id, note_md, tags, sort_order)
VALUES (28865, 'midrash', 'SANCT_CORE_ROM_008_018_030',
    '**Midrash:** Groaning is labor, not defeat. The metaphor promises birth-God is bringing something forth.',
    'sanctification,groaning,childbirth', 50);

-- Romans 8:23 (id=28866)
INSERT INTO verse_notes (verse_id, note_kind, unit_id, note_md, tags, sort_order)
VALUES (28866, 'midrash', 'SANCT_CORE_ROM_008_018_030',
    '**Midrash:** Believers groan inwardly because adoption is real yet unfinished in manifestation. The Spirit produces longing for completion-redemption of the body.',
    'sanctification,adoption,groaning,redemption', 60);

-- Romans 8:24 (id=28867)
INSERT INTO verse_notes (verse_id, note_kind, unit_id, note_md, tags, sort_order)
VALUES (28867, 'midrash', 'SANCT_CORE_ROM_008_018_030',
    '**Midrash:** Hope lives where sight has not yet arrived. Salvation includes unfinished expectation-faith waits without demanding immediate relief.',
    'sanctification,hope,faith', 70);

-- Romans 8:25 (id=28868)
INSERT INTO verse_notes (verse_id, note_kind, unit_id, note_md, tags, sort_order)
VALUES (28868, 'midrash', 'SANCT_CORE_ROM_008_018_030',
    '**Midrash:** Patience is endurance with trust. Waiting here is active-holding steady under God''s timing.',
    'sanctification,patience,endurance', 80);

-- Romans 8:26 (id=28869)
INSERT INTO verse_notes (verse_id, note_kind, unit_id, note_md, tags, sort_order)
VALUES (28869, 'midrash', 'SANCT_CORE_ROM_008_018_030',
    '**Midrash:** Weakness is the entry point of divine help. The Spirit does not shame inability-He joins it.',
    'sanctification,spirit,weakness,prayer', 90);

-- Romans 8:26 continued (intercession)
INSERT INTO verse_notes (verse_id, note_kind, unit_id, note_md, tags, sort_order)
VALUES (28869, 'midrash', 'SANCT_CORE_ROM_008_018_030',
    '**Midrash:** When words fail, the Spirit intercedes with groanings too deep for speech-Spirit-formed petition where language cannot reach.',
    'sanctification,intercession,groaning', 95);

-- Romans 8:27 (id=28870)
INSERT INTO verse_notes (verse_id, note_kind, unit_id, note_md, tags, sort_order)
VALUES (28870, 'midrash', 'SANCT_CORE_ROM_008_018_030',
    '**Midrash:** The Father who searches hearts knows the mind of the Spirit. Intercession is aligned "according to God"-the Trinity receives prayers already shaped by divine will.',
    'sanctification,trinity,intercession,will-of-god', 100);

-- Romans 8:28 (id=28871)
INSERT INTO verse_notes (verse_id, note_kind, unit_id, note_md, tags, sort_order)
VALUES (28871, 'midrash', 'SANCT_CORE_ROM_008_018_030',
    '**Midrash:** "Good" is defined by purpose, not comfort. Providence is sanctifying-events converge toward God''s intended end.',
    'sanctification,providence,good,purpose', 110);

-- Romans 8:29 (id=28872)
INSERT INTO verse_notes (verse_id, note_kind, unit_id, note_md, tags, sort_order)
VALUES (28872, 'midrash', 'SANCT_CORE_ROM_008_018_030',
    '**Midrash:** The goal is conformity to the Son-resemblance, not mere rescue. Sanctification is image-formation.',
    'sanctification,image-of-christ,conformity', 120);

-- Romans 8:30 (id=28873)
INSERT INTO verse_notes (verse_id, note_kind, unit_id, note_md, tags, sort_order)
VALUES (28873, 'midrash', 'SANCT_CORE_ROM_008_018_030',
    '**Midrash:** The chain is unbroken-called, justified, glorified. Glorification is spoken as certain: God completes what He initiates.',
    'sanctification,calling,justification,glorification', 130);

-- Unit summary (attached to v.30)
INSERT INTO verse_notes (verse_id, note_kind, unit_id, note_md, tags, sort_order)
VALUES (28873, 'summary', 'SANCT_CORE_ROM_008_018_030',
    '**Unit Summary:** Creation groans, believers groan, and the Spirit groans within believers. Through weakness, waiting, and suffering, the Spirit forms the image of the Son. The Father receives intercession aligned to His will, ensuring that everything moves toward Christlikeness and final glory.',
    'sanctification,unit-summary,romans8', 999);

-- =============================================================================
-- GREEK MARGINS (verb parsing)
-- =============================================================================

-- Romans 8:18 (id=28861)
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
VALUES (28861, 'SANCT_CORE_ROM_008_018_030',
    'logizomai', 'logizomai', 'present middle indicative', 'reckon / consider',
    'Settled evaluation (not mood): Paul weighs suffering against coming glory.', 10);

-- Romans 8:19 (id=28862)
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
VALUES (28862, 'SANCT_CORE_ROM_008_018_030',
    'apekdechomai', 'apekdechomai', 'present middle indicative', 'wait eagerly',
    'Strained anticipation: creation leans forward toward the revealing of sons.', 20);

-- Romans 8:20 (id=28863)
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
VALUES (28863, 'SANCT_CORE_ROM_008_018_030',
    'hypotasso', 'hypotasso', 'aorist passive indicative', 'subject / place under',
    'Creation "was subjected" (passive): imposed condition, not voluntary.', 30);

-- Romans 8:21 (id=28864)
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
VALUES (28864, 'SANCT_CORE_ROM_008_018_030',
    'eleutheroo', 'eleutheroo', 'future passive indicative', 'set free / liberate',
    'Future liberation: the created order participates in the children''s freedom.', 40);

-- Romans 8:22 (id=28865)
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
VALUES (28865, 'SANCT_CORE_ROM_008_018_030',
    'systenazo', 'systenazo', 'present active indicative', 'groan together',
    'Corporate groaning: creation shares one laboring ache.', 50);

-- Romans 8:23 (id=28866)
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
VALUES (28866, 'SANCT_CORE_ROM_008_018_030',
    'apekdechomai', 'apekdechomai', 'present middle participle', 'await eagerly',
    'Believers share creation''s posture-eager waiting for bodily redemption.', 60);

-- Romans 8:24 (id=28867)
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
VALUES (28867, 'SANCT_CORE_ROM_008_018_030',
    'sozo', 'sozo', 'aorist passive indicative', 'save / rescue',
    'Decisive saving act, with ongoing hope for completion.', 70);

-- Romans 8:25 (id=28868)
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
VALUES (28868, 'SANCT_CORE_ROM_008_018_030',
    'apekdechomai', 'apekdechomai', 'present middle indicative', 'wait eagerly',
    'Present tense: hope keeps waiting active, not idle.', 80);

-- Romans 8:26 - Spirit helps (id=28869)
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
VALUES (28869, 'SANCT_CORE_ROM_008_018_030',
    'synantilambanomai', 'synantilambanomai', 'present middle indicative', 'take hold together with',
    'The Spirit joins the burden; He does not merely observe or replace the believer.', 90);

-- Romans 8:26 - Spirit intercedes
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
VALUES (28869, 'SANCT_CORE_ROM_008_018_030',
    'hyperentynchano', 'hyperentynchano', 'present active indicative', 'intercede on behalf of',
    'Advocacy language: Spirit-formed petition where words fail.', 95);

-- Romans 8:27 (id=28870)
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
VALUES (28870, 'SANCT_CORE_ROM_008_018_030',
    'entynchano', 'entynchano', 'present active indicative', 'appeal / petition',
    'Intercession "according to God" (aligned to divine will, not human guesswork).', 100);

-- Romans 8:28 (id=28871)
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
VALUES (28871, 'SANCT_CORE_ROM_008_018_030',
    'synergeo', 'synergeo', 'present active indicative', 'work together',
    'Providence is collaborative convergence: events are not isolated.', 110);

-- Romans 8:29 - foreknew (id=28872)
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
VALUES (28872, 'SANCT_CORE_ROM_008_018_030',
    'proginosko', 'proginosko', 'aorist active indicative', 'know beforehand',
    'Relational knowing that precedes purpose and calling.', 120);

-- Romans 8:29 - predestined
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
VALUES (28872, 'SANCT_CORE_ROM_008_018_030',
    'proorizo', 'proorizo', 'aorist active indicative', 'predestine / mark out',
    'Goal-oriented: conformed to the Son''s image (sanctification''s destination).', 125);

-- Romans 8:30 - called (id=28873)
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
VALUES (28873, 'SANCT_CORE_ROM_008_018_030',
    'kaleo', 'kaleo', 'aorist active indicative', 'call',
    'Aorist sequence: God''s action presented as decisive and sure.', 130);

-- Romans 8:30 - justified
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
VALUES (28873, 'SANCT_CORE_ROM_008_018_030',
    'dikaioo', 'dikaioo', 'aorist active indicative', 'justify',
    'Declared righteous-grounds the sanctifying transformation.', 135);

-- Romans 8:30 - glorified
INSERT INTO greek_margins (verse_id, unit_id, lemma_greek, translit, morph, gloss, note_md, sort_order)
VALUES (28873, 'SANCT_CORE_ROM_008_018_030',
    'doxazo', 'doxazo', 'aorist active indicative', 'glorify',
    'Spoken as completed: certainty of God''s finishing work.', 140);
