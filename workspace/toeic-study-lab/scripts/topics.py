# TOEIC Part5 題材ジャンル定義
#
# generate_question.py が問題ごとにランダムで1つ選び、プロンプトに埋め込む。
# 目的: 生成される英文がビジネス分野（社内コミュニケーション）に偏るのを防ぎ、
# 実際のTOEICで出題される幅広い分野をカバーすること。

TOPIC_DOMAINS = {
    "business_office": "社内業務・オフィスコミュニケーション（会議・人事・総務・社内メール）",
    "business_external": "社外ビジネス（取引先とのやり取り・契約・営業・マーケティング）",
    "daily_life": "日常生活（家庭・近所付き合い・買い物・家事）",
    "travel": "旅行・交通（空港・ホテル・公共交通機関）",
    "entertainment": "娯楽・文化（映画・音楽・スポーツ・イベント）",
    "dining": "飲食（レストラン・カフェ）",
    "health": "健康・医療（病院・フィットネス）",
    "education": "教育・研修（学校・セミナー・資格）",
    "housing_facility": "住宅・公共施設（不動産・図書館・公共施設）",
    "announcement_media": "案内放送・広告・ニュース（天気予報・お知らせ）",
}

ALL_TOPIC_KEYS = set(TOPIC_DOMAINS.keys())
