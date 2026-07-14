import json
from pathlib import Path
from urllib.parse import urlencode

from flask import current_app, g, request, session

SUPPORTED_LOCALES = ("zh-Hant", "en", "fr", "es", "zh-Hans")
ENABLED_LOCALES = SUPPORTED_LOCALES
# French and Spanish translations remain available for content workflow and direct links,
# but are intentionally hidden from the public selector until their presentation is ready.
PUBLIC_SELECTOR_LOCALES = ("en", "zh-Hant", "zh-Hans")
LANGUAGE_NAMES = {
    "zh-Hant": "繁體中文",
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "zh-Hans": "简体中文",
}

CATALOG = {
    "en": {
        "首頁": "Home", "認識 CAIM": "About CAIM", "收費計劃": "Pricing",
        "宣教士支援": "Missionary Support", "教會AI轉型": "Church AI Transformation",
        "課程與講座": "Courses & Events", "專欄文章": "Articles", "聯絡我們": "Contact Us",
        "人工智能事工中心": "Centre for AI & Ministry", "新時代的智慧服事": "Wisdom for Ministry in a New Era",
        "預約講座及訓練": "Book", "聯絡": "Contact", "頁尾導覽": "Footer navigation",
        "主導覽": "Main navigation", "手機主導覽": "Mobile navigation", "開啟選單": "Open menu",
        "在 AI 時代，與教會同行，以神學深度、倫理智慧與使命意識，負責任地塑造科技在教會中的使用。": "Walking with churches in the age of AI, shaping responsible technology use through theological depth, ethical wisdom, and missional purpose.",
        "最新消息與活動": "Latest News & Events", "最新文章": "Latest Articles",
        "返回首頁": "Return Home", "找不到頁面": "Page Not Found", "你所尋找的頁面不存在或已經移動。": "The page you are looking for does not exist or has moved.",
        "返回文章列表": "Back to Articles", "最後更新於：": "Last updated: ", "作者：": "Author: ",
        "瀏覽課程與講座": "Browse Courses & Events", "聯絡 CAIM": "Contact CAIM",
        "學習、工作坊與群體同行": "Learning, Workshops & Community",
        "課程涵蓋人工智能基礎、信仰與倫理辨識、實用工具、教會應用與領袖策略。": "Courses cover AI foundations, faith and ethical discernment, practical tools, church applications, and leadership strategy.",
        "CAIM 願與你同行": "CAIM Is Ready to Walk with You", "姓名": "Name", "教會／機構": "Church / Organization",
        "電郵": "Email", "電話": "Phone", "查詢類別": "Inquiry Type", "訊息內容": "Message", "送出查詢": "Send Inquiry",
        "在人工智能時代，": "In the age of artificial intelligence,", "以智慧忠心服事": "serve faithfully with wisdom",
        "辨識．轉化．同行": "Discern. Transform. Walk Together.", "與教會迎向未來": "Facing the Future with the Church",
        "結合神學反思、倫理治理、AI 應用、教會培訓與策略顧問，與教會一起辨識科技、塑造實踐、回應使命。": "Bringing together theological reflection, ethical governance, AI application, church training, and strategic counsel to discern technology, shape practice, and answer the mission with churches.",
        "與我們同行": "Walk with Us", "人工智能事工中心是甚麼？": "What is the Centre for AI & Ministry?",
        "人工智能事工中心 (Centre for AI & Ministry, CAIM) 是一個結合神學反思、倫理治理、AI 應用、教會培訓與策略顧問的事工平台。我們與教會同行，幫助信仰群體在 AI 時代中，不只是追趕科技，而是以清晰的使命、成熟的辨識與負責任的實踐，塑造科技在教會中的合宜使用。": "The Centre for AI & Ministry (CAIM) brings theological reflection, ethical governance, AI application, church training, and strategic counsel into one ministry platform. We help faith communities move beyond chasing technology to shape its appropriate use through clear mission, mature discernment, and responsible practice.",
        "三個同行向度": "Three Dimensions of Partnership", "從信仰反思開始，建立清晰的使用界線，並將 AI 合宜地應用在實際事工之中。": "Begin with faithful reflection, establish clear boundaries, and apply AI appropriately in real ministry.",
        "DX Sermon：為牧者與信徒而設的人工智能聖經研習平台": "DX Sermon: AI Bible Study for Pastors and Believers",
        "DX Sermon 幫助牧者、傳道人、神學生及信徒從經文出發，進行多維度研究、釋經分析、講章構思與查經材料預備。它不是取代禱告、默想與釋經功夫，而是成為一個有啟迪、有深度、能促進信仰反思的研經空間。": "DX Sermon helps pastors, preachers, students, and believers begin with Scripture for multidimensional research, exegesis, sermon development, and study preparation. It supports rather than replaces prayer, meditation, and responsible interpretation.",
        "了解 DX Sermon": "Discover DX Sermon", "為牧者、領袖與信徒而設的實用 AI 課程": "Practical AI Courses for Pastors, Leaders, and Believers",
        "公開講座、實務工作坊、教會內部培訓及宗派領袖研討會。": "Public talks, practical workshops, in-church training, and denominational leadership seminars.",
        "立即報名": "Register Now", "CAIM 對人工智能、教會實踐與神學辨識的觀察和反思。": "CAIM observations and reflections on artificial intelligence, church practice, and theological discernment.",
        "從經文出發，讓研究更深入": "Begin with Scripture and Study More Deeply", "DX Sermon 將多個研經與講道預備流程整合在同一平台，協助使用者整理脈絡、探索觀點、建立結構，同時保留牧者個人的禱告、辨識與神學責任。": "DX Sermon integrates Bible study and sermon preparation workflows in one platform, helping users organize context, explore perspectives, and build structure while preserving prayer, discernment, and theological responsibility.",
        "查看收費計劃": "View Pricing", "講章工具箱": "Sermon Toolbox", "一鍵講章工具": "One-click Sermon Tools",
        "轉型不只是引入工具": "Transformation Is More Than Introducing Tools", "真正的教會 AI 轉型牽涉領導、文化、倫理、資料、流程、培訓與使命方向。": "Real church AI transformation involves leadership, culture, ethics, data, processes, training, and mission.",
        "現況與準備度評估": "Current State & Readiness Assessment", "了解教會的需要、能力、風險和優先次序。": "Understand the church’s needs, capabilities, risks, and priorities.", "策略與治理框架": "Strategy & Governance Framework", "訂立清晰的 AI 使用原則、責任和審視機制。": "Set clear AI principles, responsibilities, and review mechanisms.", "事工流程優化": "Ministry Process Improvement", "選擇適合的場景，以小步試行、回顧和改善。": "Choose suitable use cases and improve through small pilots and review.", "領袖與團隊裝備": "Leader & Team Equipping", "建立持續學習、辨識和負責任使用的能力。": "Build capacity for continuous learning, discernment, and responsible use.", "開始教會的 AI 轉型對話": "Start the Church AI Transformation Conversation", "讓我們先了解你的處境與需要。": "Let us first understand your context and needs.",
        "DX Sermon 免費開放給所有在職宣教士": "DX Sermon Is Free for Active Missionaries", "CAIM 深信，完成主所託付的福音使命，需要眾教會彼此連結、同心擺上。因此我們將 DX Sermon 向所有在職宣教士免費開放使用，盼望成為前線工人手中的實用工具。": "CAIM believes fulfilling the gospel mission requires churches to stand together. DX Sermon is therefore available free to active missionaries as a practical frontline tool.", "無論是全職或帶職宣教，只要你需要，我們都誠摯邀請你使用 DX Sermon，讓我們在主裡彼此扶持。": "Whether serving full-time or alongside other work, you are warmly invited to use DX Sermon so we may support one another in the Lord.",
        "邀請 CAIM 講座": "Invite a CAIM Talk", "教會 AI 顧問服務": "Church AI Consulting", "DX Sermon 查詢": "DX Sermon Inquiry", "一般查詢": "General Inquiry", "請簡介你的教會、機構或服事場景，以及希望 CAIM 如何支援你們。": "Tell us about your church, organization, or ministry context and how you would like CAIM to support you.",
    },
    "fr": {
        "首頁": "Accueil", "認識 CAIM": "À propos de CAIM", "收費計劃": "Tarifs",
        "宣教士支援": "Soutien missionnaire", "教會AI轉型": "Transformation IA de l’Église",
        "課程與講座": "Cours et événements", "專欄文章": "Articles", "聯絡我們": "Nous contacter",
        "人工智能事工中心": "Centre pour l’IA et le ministère", "新時代的智慧服事": "Servir avec sagesse dans une nouvelle ère",
        "預約講座及訓練": "Réserver", "聯絡": "Contact", "頁尾導覽": "Navigation de pied de page",
        "主導覽": "Navigation principale", "手機主導覽": "Navigation mobile", "開啟選單": "Ouvrir le menu",
        "在 AI 時代，與教會同行，以神學深度、倫理智慧與使命意識，負責任地塑造科技在教會中的使用。": "Accompagner les Églises à l’ère de l’IA afin de façonner un usage responsable de la technologie, avec profondeur théologique, sagesse éthique et vision missionnelle.",
        "最新消息與活動": "Actualités et événements", "最新文章": "Derniers articles",
        "返回首頁": "Retour à l’accueil", "找不到頁面": "Page introuvable", "你所尋找的頁面不存在或已經移動。": "La page recherchée n’existe pas ou a été déplacée.",
        "返回文章列表": "Retour aux articles", "最後更新於：": "Dernière mise à jour : ", "作者：": "Auteur : ",
        "瀏覽課程與講座": "Voir les cours et événements", "聯絡 CAIM": "Contacter CAIM",
        "學習、工作坊與群體同行": "Apprentissage, ateliers et cheminement communautaire",
        "課程涵蓋人工智能基礎、信仰與倫理辨識、實用工具、教會應用與領袖策略。": "Les cours couvrent les bases de l’IA, le discernement théologique et éthique, les outils pratiques, les usages en Église et la stratégie des responsables.",
        "CAIM 願與你同行": "CAIM vous accompagne", "姓名": "Nom", "教會／機構": "Église / Organisation",
        "電郵": "E-mail", "電話": "Téléphone", "查詢類別": "Type de demande", "訊息內容": "Message", "送出查詢": "Envoyer",
        "在人工智能時代，": "À l’ère de l’intelligence artificielle,", "以智慧忠心服事": "servir fidèlement avec sagesse",
        "辨識．轉化．同行": "Discerner. Transformer. Cheminer ensemble.", "與教會迎向未來": "Accueillir l’avenir avec l’Église",
        "結合神學反思、倫理治理、AI 應用、教會培訓與策略顧問，與教會一起辨識科技、塑造實踐、回應使命。": "Réunir réflexion théologique, gouvernance éthique, usages de l’IA, formation des Églises et conseil stratégique pour discerner la technologie, façonner les pratiques et répondre à la mission.",
        "與我們同行": "Cheminer avec nous", "人工智能事工中心是甚麼？": "Qu’est-ce que le Centre pour l’IA et le ministère ?",
        "人工智能事工中心 (Centre for AI & Ministry, CAIM) 是一個結合神學反思、倫理治理、AI 應用、教會培訓與策略顧問的事工平台。我們與教會同行，幫助信仰群體在 AI 時代中，不只是追趕科技，而是以清晰的使命、成熟的辨識與負責任的實踐，塑造科技在教會中的合宜使用。": "Le Centre pour l’IA et le ministère réunit réflexion théologique, gouvernance éthique, usages de l’IA, formation et conseil stratégique. Nous aidons les communautés chrétiennes à façonner un usage approprié de la technologie par une mission claire, un discernement mûr et une pratique responsable.",
        "三個同行向度": "Trois dimensions d’accompagnement", "從信仰反思開始，建立清晰的使用界線，並將 AI 合宜地應用在實際事工之中。": "Commencer par la réflexion dans la foi, poser des limites claires et appliquer l’IA de manière appropriée au ministère.",
        "DX Sermon：為牧者與信徒而設的人工智能聖經研習平台": "DX Sermon : étude biblique assistée par IA pour pasteurs et croyants",
        "DX Sermon 幫助牧者、傳道人、神學生及信徒從經文出發，進行多維度研究、釋經分析、講章構思與查經材料預備。它不是取代禱告、默想與釋經功夫，而是成為一個有啟迪、有深度、能促進信仰反思的研經空間。": "DX Sermon aide pasteurs, prédicateurs, étudiants et croyants à partir de l’Écriture pour la recherche, l’exégèse, la préparation de sermons et d’études, sans remplacer la prière, la méditation ni la responsabilité d’interprétation.",
        "了解 DX Sermon": "Découvrir DX Sermon", "為牧者、領袖與信徒而設的實用 AI 課程": "Cours pratiques d’IA pour pasteurs, responsables et croyants",
        "公開講座、實務工作坊、教會內部培訓及宗派領袖研討會。": "Conférences publiques, ateliers pratiques, formations en Église et séminaires pour responsables.",
        "立即報名": "S’inscrire", "CAIM 對人工智能、教會實踐與神學辨識的觀察和反思。": "Observations et réflexions de CAIM sur l’intelligence artificielle, la pratique ecclésiale et le discernement théologique.",
        "從經文出發，讓研究更深入": "Partir de l’Écriture pour approfondir l’étude", "DX Sermon 將多個研經與講道預備流程整合在同一平台，協助使用者整理脈絡、探索觀點、建立結構，同時保留牧者個人的禱告、辨識與神學責任。": "DX Sermon réunit l’étude biblique et la préparation de sermons sur une plateforme, tout en préservant la prière, le discernement et la responsabilité théologique.",
        "查看收費計劃": "Voir les tarifs", "講章工具箱": "Boîte à outils pour sermons", "一鍵講章工具": "Outils de sermon en un clic",
        "轉型不只是引入工具": "La transformation ne se limite pas aux outils", "真正的教會 AI 轉型牽涉領導、文化、倫理、資料、流程、培訓與使命方向。": "Une véritable transformation IA concerne le leadership, la culture, l’éthique, les données, les processus, la formation et la mission.",
        "現況與準備度評估": "Évaluation de l’état actuel et de la préparation", "了解教會的需要、能力、風險和優先次序。": "Comprendre les besoins, capacités, risques et priorités de l’Église.", "策略與治理框架": "Cadre stratégique et de gouvernance", "訂立清晰的 AI 使用原則、責任和審視機制。": "Définir des principes, responsabilités et mécanismes de contrôle clairs.", "事工流程優化": "Amélioration des processus ministériels", "選擇適合的場景，以小步試行、回顧和改善。": "Choisir des cas adaptés et progresser par petits pilotes et révisions.", "領袖與團隊裝備": "Équipement des responsables et équipes", "建立持續學習、辨識和負責任使用的能力。": "Développer l’apprentissage continu, le discernement et l’usage responsable.", "開始教會的 AI 轉型對話": "Commencer le dialogue sur la transformation IA", "讓我們先了解你的處境與需要。": "Commençons par comprendre votre contexte et vos besoins.",
        "DX Sermon 免費開放給所有在職宣教士": "DX Sermon est gratuit pour les missionnaires en activité", "CAIM 深信，完成主所託付的福音使命，需要眾教會彼此連結、同心擺上。因此我們將 DX Sermon 向所有在職宣教士免費開放使用，盼望成為前線工人手中的實用工具。": "CAIM croit que la mission de l’Évangile demande l’unité des Églises. DX Sermon est donc offert gratuitement aux missionnaires en activité comme outil pratique de terrain.", "無論是全職或帶職宣教，只要你需要，我們都誠摯邀請你使用 DX Sermon，讓我們在主裡彼此扶持。": "Que votre service soit à plein temps ou bivocationnel, nous vous invitons à utiliser DX Sermon afin de nous soutenir mutuellement dans le Seigneur.",
        "邀請 CAIM 講座": "Inviter CAIM pour une conférence", "教會 AI 顧問服務": "Conseil IA pour Églises", "DX Sermon 查詢": "Demande DX Sermon", "一般查詢": "Demande générale", "請簡介你的教會、機構或服事場景，以及希望 CAIM 如何支援你們。": "Présentez votre Église, organisation ou contexte de ministère et indiquez comment CAIM peut vous accompagner.",
    },
    "es": {
        "首頁": "Inicio", "認識 CAIM": "Acerca de CAIM", "收費計劃": "Precios",
        "宣教士支援": "Apoyo misionero", "教會AI轉型": "Transformación de IA para iglesias",
        "課程與講座": "Cursos y eventos", "專欄文章": "Artículos", "聯絡我們": "Contacto",
        "人工智能事工中心": "Centro de IA y Ministerio", "新時代的智慧服事": "Servir con sabiduría en una nueva era",
        "預約講座及訓練": "Reservar", "聯絡": "Contacto", "頁尾導覽": "Navegación del pie",
        "主導覽": "Navegación principal", "手機主導覽": "Navegación móvil", "開啟選單": "Abrir menú",
        "在 AI 時代，與教會同行，以神學深度、倫理智慧與使命意識，負責任地塑造科技在教會中的使用。": "Acompañamos a las iglesias en la era de la IA para formar un uso responsable de la tecnología con profundidad teológica, sabiduría ética y propósito misional.",
        "最新消息與活動": "Últimas noticias y eventos", "最新文章": "Últimos artículos",
        "返回首頁": "Volver al inicio", "找不到頁面": "Página no encontrada", "你所尋找的頁面不存在或已經移動。": "La página que buscas no existe o se ha movido.",
        "返回文章列表": "Volver a artículos", "最後更新於：": "Última actualización: ", "作者：": "Autor: ",
        "瀏覽課程與講座": "Ver cursos y eventos", "聯絡 CAIM": "Contactar con CAIM",
        "學習、工作坊與群體同行": "Aprendizaje, talleres y comunidad",
        "課程涵蓋人工智能基礎、信仰與倫理辨識、實用工具、教會應用與領袖策略。": "Los cursos cubren fundamentos de IA, discernimiento de fe y ética, herramientas prácticas, aplicaciones para iglesias y estrategia de liderazgo.",
        "CAIM 願與你同行": "CAIM camina contigo", "姓名": "Nombre", "教會／機構": "Iglesia / Organización",
        "電郵": "Correo electrónico", "電話": "Teléfono", "查詢類別": "Tipo de consulta", "訊息內容": "Mensaje", "送出查詢": "Enviar consulta",
        "在人工智能時代，": "En la era de la inteligencia artificial,", "以智慧忠心服事": "servir fielmente con sabiduría",
        "辨識．轉化．同行": "Discernir. Transformar. Caminar juntos.", "與教會迎向未來": "Afrontar el futuro con la Iglesia",
        "結合神學反思、倫理治理、AI 應用、教會培訓與策略顧問，與教會一起辨識科技、塑造實踐、回應使命。": "Integramos reflexión teológica, gobierno ético, aplicación de IA, formación para iglesias y asesoría estratégica para discernir la tecnología, formar prácticas y responder a la misión.",
        "與我們同行": "Camina con nosotros", "人工智能事工中心是甚麼？": "¿Qué es el Centro de IA y Ministerio?",
        "人工智能事工中心 (Centre for AI & Ministry, CAIM) 是一個結合神學反思、倫理治理、AI 應用、教會培訓與策略顧問的事工平台。我們與教會同行，幫助信仰群體在 AI 時代中，不只是追趕科技，而是以清晰的使命、成熟的辨識與負責任的實踐，塑造科技在教會中的合宜使用。": "El Centro de IA y Ministerio integra reflexión teológica, gobierno ético, aplicación de IA, formación y asesoría estratégica. Ayudamos a las comunidades de fe a formar un uso adecuado de la tecnología mediante una misión clara, discernimiento maduro y práctica responsable.",
        "三個同行向度": "Tres dimensiones de acompañamiento", "從信仰反思開始，建立清晰的使用界線，並將 AI 合宜地應用在實際事工之中。": "Comenzar con reflexión de fe, establecer límites claros y aplicar la IA apropiadamente en el ministerio real.",
        "DX Sermon：為牧者與信徒而設的人工智能聖經研習平台": "DX Sermon: estudio bíblico con IA para pastores y creyentes",
        "DX Sermon 幫助牧者、傳道人、神學生及信徒從經文出發，進行多維度研究、釋經分析、講章構思與查經材料預備。它不是取代禱告、默想與釋經功夫，而是成為一個有啟迪、有深度、能促進信仰反思的研經空間。": "DX Sermon ayuda a pastores, predicadores, estudiantes y creyentes a partir de las Escrituras para investigar, hacer exégesis y preparar sermones y estudios, sin sustituir la oración, la meditación ni la interpretación responsable.",
        "了解 DX Sermon": "Descubrir DX Sermon", "為牧者、領袖與信徒而設的實用 AI 課程": "Cursos prácticos de IA para pastores, líderes y creyentes",
        "公開講座、實務工作坊、教會內部培訓及宗派領袖研討會。": "Charlas públicas, talleres prácticos, formación en iglesias y seminarios para líderes denominacionales.",
        "立即報名": "Inscribirse", "CAIM 對人工智能、教會實踐與神學辨識的觀察和反思。": "Observaciones y reflexiones de CAIM sobre inteligencia artificial, práctica eclesial y discernimiento teológico.",
        "從經文出發，讓研究更深入": "Partir de las Escrituras para profundizar", "DX Sermon 將多個研經與講道預備流程整合在同一平台，協助使用者整理脈絡、探索觀點、建立結構，同時保留牧者個人的禱告、辨識與神學責任。": "DX Sermon integra el estudio bíblico y la preparación de sermones en una plataforma, preservando la oración, el discernimiento y la responsabilidad teológica.",
        "查看收費計劃": "Ver precios", "講章工具箱": "Caja de herramientas para sermones", "一鍵講章工具": "Herramientas de sermón con un clic",
        "轉型不只是引入工具": "La transformación es más que introducir herramientas", "真正的教會 AI 轉型牽涉領導、文化、倫理、資料、流程、培訓與使命方向。": "La verdadera transformación de IA implica liderazgo, cultura, ética, datos, procesos, formación y misión.",
        "現況與準備度評估": "Evaluación del estado y preparación", "了解教會的需要、能力、風險和優先次序。": "Comprender necesidades, capacidades, riesgos y prioridades.", "策略與治理框架": "Marco de estrategia y gobierno", "訂立清晰的 AI 使用原則、責任和審視機制。": "Definir principios, responsabilidades y mecanismos de revisión claros.", "事工流程優化": "Mejora de procesos ministeriales", "選擇適合的場景，以小步試行、回顧和改善。": "Elegir casos adecuados y mejorar mediante pequeños pilotos y revisión.", "領袖與團隊裝備": "Formación de líderes y equipos", "建立持續學習、辨識和負責任使用的能力。": "Desarrollar aprendizaje continuo, discernimiento y uso responsable.", "開始教會的 AI 轉型對話": "Iniciar la conversación sobre transformación de IA", "讓我們先了解你的處境與需要。": "Permítenos conocer primero tu contexto y necesidades.",
        "DX Sermon 免費開放給所有在職宣教士": "DX Sermon es gratuito para misioneros activos", "CAIM 深信，完成主所託付的福音使命，需要眾教會彼此連結、同心擺上。因此我們將 DX Sermon 向所有在職宣教士免費開放使用，盼望成為前線工人手中的實用工具。": "CAIM cree que cumplir la misión del evangelio requiere unidad entre iglesias. Por eso DX Sermon es gratuito para misioneros activos como herramienta práctica de primera línea.", "無論是全職或帶職宣教，只要你需要，我們都誠摯邀請你使用 DX Sermon，讓我們在主裡彼此扶持。": "Ya sirvas a tiempo completo o de forma bivocacional, te invitamos a usar DX Sermon para apoyarnos mutuamente en el Señor.",
        "邀請 CAIM 講座": "Invitar una charla de CAIM", "教會 AI 顧問服務": "Consultoría de IA para iglesias", "DX Sermon 查詢": "Consulta sobre DX Sermon", "一般查詢": "Consulta general", "請簡介你的教會、機構或服事場景，以及希望 CAIM 如何支援你們。": "Cuéntanos sobre tu iglesia, organización o contexto ministerial y cómo deseas que CAIM te apoye.",
    },
}

# Generated v3 page copy lives separately so the reviewed core navigation
# translations remain readable and take precedence over generated entries.
_static_catalog_path = Path(__file__).with_name("static_translations.json")
if _static_catalog_path.exists():
    with _static_catalog_path.open(encoding="utf-8") as catalog_file:
        _generated_catalog = json.load(catalog_file)
    for _locale, _translations in _generated_catalog.items():
        CATALOG.setdefault(_locale, {})
        CATALOG[_locale] = {**_translations, **CATALOG[_locale]}

PAGE_COPY = {
    "en": {
        "about": ("About CAIM", "In a world rapidly reshaped by artificial intelligence, CAIM walks with churches so faith communities can answer God’s call with theological depth, ethical wisdom, and creative courage."),
        "services": ("Church AI Transformation Support", "From readiness assessment and ethical policy to AI system design and pastoral training, CAIM helps churches build a safe, responsible, faith-led path for AI adoption."),
        "dx": ("DX Sermon", "A one-stop AI Bible study platform that brings biblical wisdom together for research, exegesis, sermon development, and study preparation."),
        "courses": ("Courses & Events", "Practical, clear, theologically discerning AI learning for pastors, leaders, believers, and church teams."),
        "missionaries": ("Missionary Support", "CAIM supports frontline gospel workers by helping AI reduce administrative burdens and strengthen mission."),
        "articles": ("Articles", "CAIM observations and reflections on artificial intelligence, church practice, theological discernment, and mission."),
        "churchAiTransformation": ("Church AI Transformation", "CAIM helps churches and organizations build an appropriate, trustworthy, and sustainable AI transformation path for their context and mission."),
        "contact": ("Contact Us", "Invite CAIM to speak or train, ask about DX products and AI consulting, or explore collaboration with us."),
    },
    "fr": {
        "about": ("À propos de CAIM", "Dans un monde rapidement transformé par l’intelligence artificielle, CAIM accompagne les Églises afin qu’elles répondent fidèlement à l’appel de Dieu avec profondeur théologique, sagesse éthique et courage créatif."),
        "services": ("Accompagnement de la transformation IA", "De l’évaluation de préparation aux politiques éthiques, à la conception de systèmes IA et à la formation pastorale, CAIM aide les Églises à bâtir une démarche sûre, responsable et guidée par la foi."),
        "dx": ("DX Sermon", "Une plateforme intégrée d’étude biblique assistée par IA pour la recherche, l’exégèse, la préparation de sermons et d’études."),
        "courses": ("Cours et événements", "Des formations pratiques, claires et théologiquement discernées pour pasteurs, responsables, croyants et équipes d’Église."),
        "missionaries": ("Soutien missionnaire", "CAIM accompagne les ouvriers de l’Évangile afin que l’IA réduise les tâches administratives et soutienne la mission."),
        "articles": ("Articles", "Observations et réflexions de CAIM sur l’intelligence artificielle, la pratique ecclésiale, le discernement théologique et la mission."),
        "churchAiTransformation": ("Transformation IA de l’Église", "CAIM aide les Églises et organisations à construire une démarche de transformation IA adaptée, fiable et durable."),
        "contact": ("Nous contacter", "Invitez CAIM pour une conférence ou une formation, renseignez-vous sur les produits DX et le conseil en IA, ou explorez une collaboration."),
    },
    "es": {
        "about": ("Acerca de CAIM", "En un mundo transformado rápidamente por la inteligencia artificial, CAIM acompaña a las iglesias para responder fielmente al llamado de Dios con profundidad teológica, sabiduría ética y valor creativo."),
        "services": ("Apoyo para la transformación de IA", "Desde la evaluación de preparación y las políticas éticas hasta el diseño de sistemas de IA y la formación pastoral, CAIM ayuda a construir un camino seguro, responsable y guiado por la fe."),
        "dx": ("DX Sermon", "Una plataforma integral de estudio bíblico con IA para investigación, exégesis, preparación de sermones y estudios."),
        "courses": ("Cursos y eventos", "Formación práctica, clara y con discernimiento teológico para pastores, líderes, creyentes y equipos de iglesia."),
        "missionaries": ("Apoyo misionero", "CAIM acompaña a quienes sirven en primera línea para que la IA reduzca cargas administrativas y fortalezca la misión."),
        "articles": ("Artículos", "Observaciones y reflexiones de CAIM sobre inteligencia artificial, práctica eclesial, discernimiento teológico y misión."),
        "churchAiTransformation": ("Transformación de IA para iglesias", "CAIM ayuda a iglesias y organizaciones a construir un camino de transformación de IA adecuado, confiable y sostenible."),
        "contact": ("Contacto", "Invita a CAIM a dar una charla o formación, consulta sobre productos DX y asesoría de IA, o explora una colaboración."),
    },
}


def normalize_locale(value):
    return value if value in current_app.config["ENABLED_LOCALES"] else current_app.config["DEFAULT_LOCALE"]


def select_locale():
    requested = request.args.get("lang")
    if requested in current_app.config["ENABLED_LOCALES"]:
        session["locale"] = requested
    g.locale = normalize_locale(session.get("locale", current_app.config["DEFAULT_LOCALE"]))


def translate(text, locale=None):
    if text is None:
        return ""
    locale = locale or getattr(g, "locale", current_app.config["DEFAULT_LOCALE"])
    if locale == "zh-Hant":
        return text
    if locale == "zh-Hans":
        try:
            from opencc import OpenCC
            return OpenCC("t2s").convert(str(text))
        except ImportError:
            return str(text)
    return CATALOG.get(locale, {}).get(str(text), str(text))


def language_url(locale):
    args = request.args.to_dict(flat=True)
    args["lang"] = locale
    query = urlencode(args)
    return f"{request.path}?{query}"


def localize_page(page_content, key, locale):
    if not page_content:
        return page_content
    page_content = dict(page_content)
    if locale == "zh-Hans":
        page_content["title"] = translate(page_content.get("title", ""), locale)
        page_content["subtitle"] = translate(page_content.get("subtitle", ""), locale)
        if page_content.get("sections"):
            page_content["sections"] = [
                {field: translate(value, locale) for field, value in section.items()}
                for section in page_content["sections"]
            ]
    elif locale in PAGE_COPY and key in PAGE_COPY[locale]:
        page_content["title"], page_content["subtitle"] = PAGE_COPY[locale][key]
    return page_content
