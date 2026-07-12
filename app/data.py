SITE = {
    "name": "CAIM 人工智能事工中心",
    "short_name": "CAIM",
    "tagline": "新時代的智慧服事",
    "email": "admin@doxaxsolutions.com",
    "description": "CAIM 幫助教會、牧者、神學院、宣教士及基督教機構在 AI 時代中，以神學深度、倫理智慧與使命意識負責任地辨識、治理與應用人工智能。",
    "keywords": "人工智能事工中心, 教會 AI, 人工智能與神學, DX Sermon, 基督教 AI 倫理",
}

NAVIGATION = [
    {"label": "首頁", "endpoint": "public.home"},
    {"label": "認識 CAIM", "endpoint": "public.about"},
    {
        "label": "DX Sermon",
        "endpoint": "public.dx_sermon",
        "children": [
            {"label": "收費計劃", "endpoint": "public.dx_pricing"},
            {"label": "宣教士支援", "endpoint": "public.missionaries"},
        ],
    },
    {"label": "教會AI轉型", "endpoint": "public.church_ai_transformation"},
    {"label": "課程與講座", "endpoint": "public.courses"},
    {"label": "專欄文章", "endpoint": "public.articles"},
    {"label": "聯絡我們", "endpoint": "public.contact"},
]

PAGE_META = {
    "home": ("首頁｜CAIM 人工智能事工中心", SITE["description"]),
    "about": ("認識 CAIM｜人工智能事工中心", "在人工智能急速改變世界的時代，CAIM 盼望與教會同行。"),
    "services": ("教會AI轉型支援｜CAIM", "從評估、政策、系統設計到培訓，與教會同行。"),
    "dx_sermon": ("DX Sermon｜人工智能聖經研習與講道預備平台", "匯聚聖經智慧的一站式人工智能研經平台。"),
    "dx_pricing": ("DX Sermon 收費計劃｜CAIM", "選擇合適的 DX Sermon 使用計劃。"),
    "courses": ("課程與講座｜CAIM", "實用、清晰、具神學辨識的 AI 課程與講座。"),
    "course_registration": ("課程報名表｜CAIM", "CAIM 課程報名。"),
    "missionaries": ("宣教士支援｜CAIM", "DX Sermon 免費開放給在職宣教士。"),
    "articles": ("專欄文章｜CAIM", "人工智能、教會實踐與神學辨識的觀察和反思。"),
    "church_ai_transformation": ("教會AI轉型｜CAIM", "建立合宜、可信、可持續的人工智能轉化路徑。"),
    "contact": ("聯絡我們｜CAIM", "邀請 CAIM 講座、培訓或顧問服務。"),
}
