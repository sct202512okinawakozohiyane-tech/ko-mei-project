# TOEIC Part5 出題カテゴリ定義
#
# 構造:
#   grammar_category (カテゴリキー) → grammar_point (サブカテゴリキー) のマッピング
#
# generate_question.py でカテゴリ指定引数として使用する。
# question_distribution.py でカテゴリ別集計の基準として使用する。

CATEGORIES = {
    # --- Level 1: 頻出 ---
    "parts_of_speech": {
        "level": 1,
        "label": "品詞",
        "points": ["noun", "verb", "adjective", "adverb"],
    },
    "verb_form": {
        "level": 1,
        "label": "動詞の形",
        "points": ["tense", "subject_verb_agreement", "modal"],
    },
    "active_passive": {
        "level": 1,
        "label": "能動／受動",
        "points": ["passive_voice"],
    },
    "infinitive": {
        "level": 1,
        "label": "不定詞",
        "points": ["to_infinitive"],
    },
    "gerund": {
        "level": 1,
        "label": "動名詞",
        "points": ["gerund"],
    },
    "participle": {
        "level": 1,
        "label": "分詞",
        "points": ["present_participle", "past_participle"],
    },
    "preposition": {
        "level": 1,
        "label": "前置詞",
        "points": ["preposition"],
    },
    "conjunction": {
        "level": 1,
        "label": "接続詞",
        "points": ["conjunction"],
    },
    "pronoun": {
        "level": 1,
        "label": "代名詞",
        "points": ["pronoun"],
    },
    # --- Level 2: 中級 ---
    "comparison": {
        "level": 2,
        "label": "比較",
        "points": ["comparative", "superlative", "as_as"],
    },
    "relative_clause": {
        "level": 2,
        "label": "関係詞節",
        "points": ["relative_pronoun"],
    },
    "noun_clause": {
        "level": 2,
        "label": "名詞節",
        "points": ["noun_clause"],
    },
    "subjunctive": {
        "level": 2,
        "label": "仮定法",
        "points": ["subjunctive"],
    },
    "inversion": {
        "level": 2,
        "label": "倒置",
        "points": ["inversion"],
    },
    # --- Level 3: 高得点帯 ---
    "vocabulary": {
        "level": 3,
        "label": "語彙",
        "points": ["vocabulary"],
    },
    "collocation": {
        "level": 3,
        "label": "コロケーション",
        "points": ["collocation"],
    },
    "idiom": {
        "level": 3,
        "label": "イディオム",
        "points": ["idiom"],
    },
    "phrasal_verb": {
        "level": 3,
        "label": "句動詞",
        "points": ["phrasal_verb"],
    },
    "context": {
        "level": 3,
        "label": "文脈",
        "points": ["context"],
    },
}

LEVEL_NAMES = {1: "頻出", 2: "中級", 3: "高得点帯"}

# 全カテゴリキーのセット（バリデーション用）
ALL_CATEGORY_KEYS = set(CATEGORIES.keys())

# 全 grammar_point → grammar_category の逆引きマップ
POINT_TO_CATEGORY = {
    point: cat_key
    for cat_key, cat in CATEGORIES.items()
    for point in cat["points"]
}


def get_points(category_key):
    """カテゴリキーに対応する grammar_point リストを返す。"""
    return CATEGORIES[category_key]["points"]


def format_category_list():
    """プロンプト埋め込み用のカテゴリ一覧文字列を生成する。"""
    lines = []
    current_level = None
    for cat_key, cat in CATEGORIES.items():
        if cat["level"] != current_level:
            current_level = cat["level"]
            lines.append(f"\n  [Level {current_level}: {LEVEL_NAMES[current_level]}]")
        points_str = " / ".join(cat["points"])
        lines.append(f"  {cat_key} ({cat['label']}): {points_str}")
    return "\n".join(lines)
