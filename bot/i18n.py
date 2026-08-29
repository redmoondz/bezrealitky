"""Fixed UI copy translated per language, for the handful of strings where
correct grammar (word order, pluralization) matters more than raw content —
unlike listing descriptions, which go through live machine translation in
``translate.py``. Covers exactly ``config.SUPPORTED_LANGUAGE_CODES``; any other
code falls back to English.
"""

from __future__ import annotations

_DEFAULT_LANGUAGE = "en"

# Shown on /start before a language is known at all — one line per supported
# language rather than a per-language lookup, so it's the one string in this
# module that isn't keyed by ``language``.
LANGUAGE_PROMPT_INITIAL = (
    "🌐 Welcome! Please choose your language.\n"
    "Vítejte! Vyberte prosím svůj jazyk.\n"
    "Привет! Пожалуйста, выберите язык.\n"
    "Вітаємо! Будь ласка, оберіть мову."
)

# Every other piece of fixed UI copy in the bot — onboarding prompts, button
# labels, error/status messages — keyed by a short id and looked up with
# :func:`t`. Listing data itself (format, location, raw furnished text) and
# argparse-generated CLI help stay untranslated, same scope boundary as the
# amenity/description translation below.
_TEXTS: dict[str, dict[str, str]] = {
    "language_prompt": {
        "en": "🌐 Pick a language:",
        "cs": "🌐 Vyberte jazyk:",
        "ru": "🌐 Выберите язык:",
        "uk": "🌐 Оберіть мову:",
    },
    "language_set_answer": {
        "en": "Language set to {label}.",
        "cs": "Jazyk nastaven na {label}.",
        "ru": "Язык изменён на {label}.",
        "uk": "Мову змінено на {label}.",
    },
    "language_set_confirm": {
        "en": "Language set to {label} — it now applies everywhere: menus, messages, and listing descriptions.",
        "cs": "Jazyk nastaven na {label} — platí teď všude: v nabídkách, zprávách i popisech inzerátů.",
        "ru": "Язык изменён на {label} — теперь он используется везде: в меню, сообщениях и описаниях объявлений.",
        "uk": "Мову змінено на {label} — тепер вона використовується всюди: у меню, повідомленнях та описах оголошень.",
    },
    "unknown_language": {
        "en": "Unknown language.",
        "cs": "Neznámý jazyk.",
        "ru": "Неизвестный язык.",
        "uk": "Невідома мова.",
    },
    "onboarding_reset_confirm": {
        "en": "🔄 Onboarding reset — let's start again.",
        "cs": "🔄 Onboarding byl resetován — pojďme na to znovu.",
        "ru": "🔄 Онбординг сброшен — начнём заново.",
        "uk": "🔄 Онбординг скинуто — почнімо знову.",
    },
    "onboarding_prompt": {
        "en": (
            "🔗 <b>One more thing — let's personalize your search.</b>\n\n"
            "Send me the link to your search results on bezrealitky.com:\n"
            "1️⃣ Open bezrealitky.com and set your filters (city, price, rooms…)\n"
            "2️⃣ Run the search so the results page loads\n"
            "3️⃣ Copy the URL from your browser's address bar\n"
            "4️⃣ Paste it here as a message\n\n"
            "Or tap the button below to start with the project's default search instead — "
            "you can always change it later with /parse_custom."
        ),
        "cs": (
            "🔗 <b>Ještě jedna věc — přizpůsobme si vyhledávání.</b>\n\n"
            "Pošlete mi odkaz na výsledky vyhledávání na bezrealitky.com:\n"
            "1️⃣ Otevřete bezrealitky.com a nastavte filtry (město, cena, počet pokojů…)\n"
            "2️⃣ Spusťte vyhledávání, aby se načetla stránka s výsledky\n"
            "3️⃣ Zkopírujte URL adresu z adresního řádku prohlížeče\n"
            "4️⃣ Vložte ji sem jako zprávu\n\n"
            "Nebo klepněte na tlačítko níže a začněte s výchozím vyhledáváním projektu — "
            "kdykoli ho můžete později změnit pomocí /parse_custom."
        ),
        "ru": (
            "🔗 <b>Ещё один шаг — настроим поиск под вас.</b>\n\n"
            "Пришлите мне ссылку на результаты поиска на bezrealitky.com:\n"
            "1️⃣ Откройте bezrealitky.com и задайте фильтры (город, цена, количество комнат…)\n"
            "2️⃣ Запустите поиск, чтобы загрузилась страница результатов\n"
            "3️⃣ Скопируйте URL из адресной строки браузера\n"
            "4️⃣ Вставьте его сюда сообщением\n\n"
            "Либо нажмите кнопку ниже, чтобы начать со стандартного поиска проекта — "
            "вы всегда сможете изменить его позже командой /parse_custom."
        ),
        "uk": (
            "🔗 <b>Ще один крок — налаштуємо пошук під вас.</b>\n\n"
            "Надішліть мені посилання на результати пошуку на bezrealitky.com:\n"
            "1️⃣ Відкрийте bezrealitky.com і встановіть фільтри (місто, ціна, кількість кімнат…)\n"
            "2️⃣ Запустіть пошук, щоб завантажилася сторінка результатів\n"
            "3️⃣ Скопіюйте URL з адресного рядка браузера\n"
            "4️⃣ Вставте його сюди повідомленням\n\n"
            "Або натисніть кнопку нижче, щоб почати зі стандартного пошуку проєкту — "
            "ви завжди зможете змінити його пізніше командою /parse_custom."
        ),
    },
    "pets_prompt": {
        "en": "🐾 Do you have — or want — a place that's pet-friendly?",
        "cs": "🐾 Máte domácího mazlíčka nebo chcete bydlení, kde jsou zvířata vítána?",
        "ru": "🐾 У вас есть питомец или вы хотите жильё, где разрешены животные?",
        "uk": "🐾 У вас є домашня тварина чи ви хочете житло, де дозволені тварини?",
    },
    "budget_prompt": {
        "en": (
            "💰 What's your monthly budget, <b>all costs included</b> (rent + service + "
            "utility charges), in <b>{currency}</b>? Send a plain number (e.g. 25000), "
            "or tap Skip.\n\n"
            "This only affects how listings are ranked for you — it won't hide anything."
        ),
        "cs": (
            "💰 Jaký je váš měsíční rozpočet <b>včetně veškerých poplatků</b> (nájem + "
            "služby + energie), v <b>{currency}</b>? Pošlete prosté číslo (např. 25000), "
            "nebo klepněte na Přeskočit.\n\n"
            "Toto ovlivňuje pouze řazení inzerátů — nic se nebude skrývat."
        ),
        "ru": (
            "💰 Какой у вас месячный бюджет <b>со всеми расходами</b> (аренда + сервисные "
            "платежи + коммунальные услуги), в <b>{currency}</b>? Отправьте просто число "
            "(например, 25000) или нажмите «Пропустить».\n\n"
            "Это влияет только на ранжирование объявлений — ничего не будет скрыто."
        ),
        "uk": (
            "💰 Який ваш місячний бюджет <b>з урахуванням усіх витрат</b> (оренда + "
            "сервісні платежі + комунальні послуги), у <b>{currency}</b>? Надішліть просто "
            "число (наприклад, 25000) або натисніть «Пропустити».\n\n"
            "Це впливає лише на ранжування оголошень — нічого не буде приховано."
        ),
    },
    "area_prompt": {
        "en": "📐 Any minimum size you need, in m²? Send a plain number (e.g. 40), or tap Skip.",
        "cs": "📐 Potřebujete minimální plochu v m²? Pošlete prosté číslo (např. 40), nebo klepněte na Přeskočit.",
        "ru": "📐 Нужна минимальная площадь в м²? Отправьте просто число (например, 40) или нажмите «Пропустить».",
        "uk": "📐 Потрібна мінімальна площа у м²? Надішліть просто число (наприклад, 40) або натисніть «Пропустити».",
    },
    "number_retry": {
        "en": "That doesn't look like a plain number. Please try again, or tap Skip.",
        "cs": "To nevypadá jako prosté číslo. Zkuste to prosím znovu, nebo klepněte na Přeskočit.",
        "ru": "Это не похоже на обычное число. Попробуйте ещё раз или нажмите «Пропустить».",
        "uk": "Це не схоже на звичайне число. Спробуйте ще раз або натисніть «Пропустити».",
    },
    "onboarding_running": {
        "en": "Saving your search and running the scraper now…",
        "cs": "Ukládám vaše vyhledávání a spouštím stahování dat…",
        "ru": "Сохраняю ваш поиск и запускаю сбор данных…",
        "uk": "Зберігаю ваш пошук і запускаю збір даних…",
    },
    "onboarding_no_results": {
        "en": "Saved! No listings match it yet — I'll keep checking and let you know when something turns up.",
        "cs": "Uloženo! Zatím žádné inzeráty neodpovídají — budu dál kontrolovat a dám vám vědět, jakmile se něco objeví.",
        "ru": "Сохранено! Пока нет подходящих объявлений — я продолжу проверять и сообщу, как только что-то появится.",
        "uk": "Збережено! Поки що немає відповідних оголошень — я продовжу перевіряти й повідомлю, щойно щось з'явиться.",
    },
    "onboarding_invalid_url": {
        "en": (
            "That doesn't look like a valid bezrealitky.com search link: {error}\n\n"
            "Please try again, or tap the button to use the default search instead."
        ),
        "cs": (
            "To nevypadá jako platný odkaz na vyhledávání bezrealitky.com: {error}\n\n"
            "Zkuste to prosím znovu, nebo klepněte na tlačítko a použijte výchozí vyhledávání."
        ),
        "ru": (
            "Это не похоже на действительную ссылку поиска bezrealitky.com: {error}\n\n"
            "Попробуйте ещё раз или нажмите кнопку, чтобы использовать поиск по умолчанию."
        ),
        "uk": (
            "Це не схоже на дійсне посилання пошуку bezrealitky.com: {error}\n\n"
            "Спробуйте ще раз або натисніть кнопку, щоб використати пошук за замовчуванням."
        ),
    },
    "onboarding_scrape_failed": {
        "en": "Scrape failed: {error}\n\nYou can retry anytime with /parse.",
        "cs": "Stahování se nezdařilo: {error}\n\nMůžete to kdykoli zkusit znovu příkazem /parse.",
        "ru": "Сбор данных не удался: {error}\n\nВы можете повторить попытку в любое время командой /parse.",
        "uk": "Збір даних не вдався: {error}\n\nВи можете повторити спробу будь-коли командою /parse.",
    },
    "onboarding_failures_note": {
        "en": "Note: {count} publication(s) failed to parse.",
        "cs": "Poznámka: nepodařilo se zpracovat inzerátů: {count}.",
        "ru": "Примечание: не удалось обработать объявлений: {count}.",
        "uk": "Примітка: не вдалося обробити оголошень: {count}.",
    },
    "help_text": {
        "en": (
            "<b>Bezrealitky listings bot</b>\n\n"
            "🌐 /start, /language — choose the bot's language (menus, messages, and listing descriptions)\n"
            "📋 /list — browse listings matching your saved search (❤️ Like / 👎 Pass on each)\n"
            "🔎 /view &lt;listing_id&gt; — full details and photos for one listing\n"
            "❤️ /liked — browse the listings you've liked\n"
            "🔄 /parse — run the scraper now with your saved search\n"
            "⚙️ /parse_custom — update your saved search with flags and run it (see /parse_help)\n"
            "🔍 /search — show your current saved search\n"
            "📊 /charts — distribution charts for your saved search\n\n"
            "Everyone has their own independent saved search — /parse_custom only ever "
            "changes yours. First time, it starts from the project's default (broad) search.\n\n"
            "Everything except language selection requires your Telegram user ID to be "
            "in the server's TELEGRAM_ALLOWED_USER_IDS.\n\n"
            "✨ Prefer a nicer screen? Tap the menu button (☰) next to the message box to "
            "open the same thing as a Mini App.\n\n"
            "💬 Questions or feedback? Write to redmoo.rsv@gmail.com anytime."
        ),
        "cs": (
            "<b>Bot s inzeráty Bezrealitky</b>\n\n"
            "🌐 /start, /language — vyberte jazyk bota (nabídky, zprávy i popisy inzerátů)\n"
            "📋 /list — procházejte inzeráty odpovídající vašemu uloženému vyhledávání "
            "(❤️ Líbí / 👎 Přeskočit u každého)\n"
            "🔎 /view &lt;listing_id&gt; — úplné podrobnosti a fotky jednoho inzerátu\n"
            "❤️ /liked — procházejte inzeráty, které se vám líbí\n"
            "🔄 /parse — spustit stahování dat s vaším uloženým vyhledáváním\n"
            "⚙️ /parse_custom — upravit vaše uložené vyhledávání pomocí přepínačů a spustit "
            "ho (viz /parse_help)\n"
            "🔍 /search — zobrazit vaše aktuální uložené vyhledávání\n"
            "📊 /charts — grafy rozložení pro vaše uložené vyhledávání\n\n"
            "Každý má vlastní nezávislé uložené vyhledávání — /parse_custom mění vždy jen "
            "to vaše. Poprvé vychází z výchozího (širokého) vyhledávání projektu.\n\n"
            "Vše kromě volby jazyka vyžaduje, aby vaše Telegram ID bylo v seznamu "
            "TELEGRAM_ALLOWED_USER_IDS na serveru.\n\n"
            "✨ Preferujete hezčí obrazovku? Klepněte na tlačítko menu (☰) vedle pole pro "
            "zprávy a otevřete totéž jako Mini App.\n\n"
            "💬 Dotazy nebo zpětná vazba? Napište kdykoli na redmoo.rsv@gmail.com."
        ),
        "ru": (
            "<b>Бот объявлений Bezrealitky</b>\n\n"
            "🌐 /start, /language — выбрать язык бота (меню, сообщения и описания объявлений)\n"
            "📋 /list — просматривать объявления по вашему сохранённому поиску "
            "(❤️ Нравится / 👎 Пропустить для каждого)\n"
            "🔎 /view &lt;listing_id&gt; — полная информация и фото одного объявления\n"
            "❤️ /liked — просматривать понравившиеся объявления\n"
            "🔄 /parse — запустить сбор данных прямо сейчас по вашему сохранённому поиску\n"
            "⚙️ /parse_custom — обновить сохранённый поиск флагами и запустить его "
            "(см. /parse_help)\n"
            "🔍 /search — показать ваш текущий сохранённый поиск\n"
            "📊 /charts — графики распределения для вашего сохранённого поиска\n\n"
            "У каждого свой независимый сохранённый поиск — /parse_custom меняет только "
            "ваш. В первый раз он берётся из стандартного (широкого) поиска проекта.\n\n"
            "Всё, кроме выбора языка, требует, чтобы ваш Telegram ID был в списке "
            "TELEGRAM_ALLOWED_USER_IDS на сервере.\n\n"
            "✨ Предпочитаете более удобный экран? Нажмите кнопку меню (☰) рядом с полем "
            "ввода, чтобы открыть то же самое как Mini App.\n\n"
            "💬 Вопросы или отзывы? Пишите в любое время на redmoo.rsv@gmail.com."
        ),
        "uk": (
            "<b>Бот оголошень Bezrealitky</b>\n\n"
            "🌐 /start, /language — обрати мову бота (меню, повідомлення та описи оголошень)\n"
            "📋 /list — переглядайте оголошення за вашим збереженим пошуком "
            "(❤️ Подобається / 👎 Пропустити для кожного)\n"
            "🔎 /view &lt;listing_id&gt; — повна інформація та фото одного оголошення\n"
            "❤️ /liked — переглядайте вподобані оголошення\n"
            "🔄 /parse — запустити збір даних зараз за вашим збереженим пошуком\n"
            "⚙️ /parse_custom — оновити збережений пошук прапорцями та запустити його "
            "(див. /parse_help)\n"
            "🔍 /search — показати ваш поточний збережений пошук\n"
            "📊 /charts — графіки розподілу для вашого збереженого пошуку\n\n"
            "У кожного свій незалежний збережений пошук — /parse_custom змінює лише ваш. "
            "Уперше він береться зі стандартного (широкого) пошуку проєкту.\n\n"
            "Усе, крім вибору мови, вимагає, щоб ваш Telegram ID був у списку "
            "TELEGRAM_ALLOWED_USER_IDS на сервері.\n\n"
            "✨ Хочете зручніший екран? Натисніть кнопку меню (☰) біля поля повідомлення, "
            "щоб відкрити те саме як Mini App.\n\n"
            "💬 Питання чи відгук? Пишіть у будь-який час на redmoo.rsv@gmail.com."
        ),
    },
    "denial_setup": {
        "en": (
            "This bot isn't configured yet: set TELEGRAM_ALLOWED_USER_IDS in the "
            "server's .env file to your Telegram user ID and restart the bot."
        ),
        "cs": (
            "Tento bot ještě není nakonfigurován: nastavte v souboru .env na serveru "
            "proměnnou TELEGRAM_ALLOWED_USER_IDS na vaše Telegram ID a restartujte bota."
        ),
        "ru": (
            "Этот бот пока не настроен: укажите в файле .env на сервере переменную "
            "TELEGRAM_ALLOWED_USER_IDS со своим Telegram ID и перезапустите бота."
        ),
        "uk": (
            "Цього бота ще не налаштовано: вкажіть у файлі .env на сервері змінну "
            "TELEGRAM_ALLOWED_USER_IDS зі своїм Telegram ID і перезапустіть бота."
        ),
    },
    "denial_not_authorized": {
        "en": "You're not authorized to use this bot.",
        "cs": "Nemáte oprávnění používat tohoto bota.",
        "ru": "У вас нет доступа к этому боту.",
        "uk": "У вас немає доступу до цього бота.",
    },
    "no_listings_match": {
        "en": "No listings match your saved search yet. Try /parse to scrape now, or /search to see what's saved.",
        "cs": "Žádné inzeráty zatím neodpovídají vašemu uloženému vyhledávání. Zkuste /parse pro okamžité stažení dat, nebo /search pro zobrazení uloženého vyhledávání.",
        "ru": "Пока нет объявлений, соответствующих вашему сохранённому поиску. Попробуйте /parse, чтобы собрать данные сейчас, или /search, чтобы посмотреть сохранённый поиск.",
        "uk": "Поки що немає оголошень, що відповідають вашому збереженому пошуку. Спробуйте /parse, щоб зібрати дані зараз, або /search, щоб переглянути збережений пошук.",
    },
    "no_liked_listings": {
        "en": "You haven't liked any listings yet — like one from /list.",
        "cs": "Zatím jste žádný inzerát neoznačili jako oblíbený — vyberte si nějaký v /list.",
        "ru": "Вы пока не отметили ни одного объявления как понравившееся — сделайте это в /list.",
        "uk": "Ви ще не позначили жодного оголошення як вподобане — зробіть це в /list.",
    },
    "view_usage": {
        "en": "Usage: /view <listing_id> — the ID shown on a listing card.",
        "cs": "Použití: /view <listing_id> — ID zobrazené na kartě inzerátu.",
        "ru": "Использование: /view <listing_id> — ID, указанный на карточке объявления.",
        "uk": "Використання: /view <listing_id> — ID, вказаний на картці оголошення.",
    },
    "listing_not_found": {
        "en": "No listing found with ID {id}.",
        "cs": "Nebyl nalezen žádný inzerát s ID {id}.",
        "ru": "Объявление с ID {id} не найдено.",
        "uk": "Оголошення з ID {id} не знайдено.",
    },
    "reacted_liked": {
        "en": "❤️ Liked",
        "cs": "❤️ Líbí se",
        "ru": "❤️ Понравилось",
        "uk": "❤️ Сподобалось",
    },
    "reacted_passed": {
        "en": "👎 Passed",
        "cs": "👎 Přeskočeno",
        "ru": "👎 Пропущено",
        "uk": "👎 Пропущено",
    },
    "charts_pick": {
        "en": "Pick a chart:",
        "cs": "Vyberte graf:",
        "ru": "Выберите график:",
        "uk": "Оберіть графік:",
    },
    "chart_unknown": {
        "en": "Unknown chart.",
        "cs": "Neznámý graf.",
        "ru": "Неизвестный график.",
        "uk": "Невідомий графік.",
    },
    "search_current": {
        "en": "Your saved search:\n{url}\n\nChange it with /parse_custom.",
        "cs": "Vaše uložené vyhledávání:\n{url}\n\nZměňte ho pomocí /parse_custom.",
        "ru": "Ваш сохранённый поиск:\n{url}\n\nИзмените его командой /parse_custom.",
        "uk": "Ваш збережений пошук:\n{url}\n\nЗмініть його командою /parse_custom.",
    },
    "parse_running": {
        "en": "Running the scraper with your saved search…",
        "cs": "Spouštím stahování dat s vaším uloženým vyhledáváním…",
        "ru": "Запускаю сбор данных по вашему сохранённому поиску…",
        "uk": "Запускаю збір даних за вашим збереженим пошуком…",
    },
    "parse_custom_running": {
        "en": "Updating your saved search and running the scraper…",
        "cs": "Aktualizuji vaše uložené vyhledávání a spouštím stahování dat…",
        "ru": "Обновляю ваш сохранённый поиск и запускаю сбор данных…",
        "uk": "Оновлюю ваш збережений пошук і запускаю збір даних…",
    },
    "parse_custom_no_flags": {
        "en": "No flags given — see /parse_help, or just use /parse to run your saved search.",
        "cs": "Nebyly zadány žádné přepínače — podívejte se na /parse_help, nebo použijte /parse pro spuštění uloženého vyhledávání.",
        "ru": "Флаги не указаны — см. /parse_help или просто используйте /parse для запуска сохранённого поиска.",
        "uk": "Прапорці не вказано — див. /parse_help або просто скористайтеся /parse, щоб запустити збережений пошук.",
    },
    "scrape_failed": {
        "en": "Scrape failed: {error}",
        "cs": "Stahování se nezdařilo: {error}",
        "ru": "Сбор данных не удался: {error}",
        "uk": "Збір даних не вдався: {error}",
    },
    "parse_flags_error": {
        "en": "Couldn't parse those flags. Send /parse_help to see the accepted options.",
        "cs": "Tyto přepínače se nepodařilo zpracovat. Odešlete /parse_help pro zobrazení přijímaných možností.",
        "ru": "Не удалось разобрать эти флаги. Отправьте /parse_help, чтобы увидеть допустимые параметры.",
        "uk": "Не вдалося розпізнати ці прапорці. Надішліть /parse_help, щоб побачити допустимі параметри.",
    },
    "sync_new_some": {
        "en": "{count} new",
        "cs": "{count} nových",
        "ru": "новых: {count}",
        "uk": "нових: {count}",
    },
    "sync_new_none": {
        "en": "no new matches",
        "cs": "žádné nové",
        "ru": "новых нет",
        "uk": "нових немає",
    },
    "sync_summary": {
        "en": "Synced {count} listings ({new_note}).",
        "cs": "Synchronizováno inzerátů: {count} ({new_note}).",
        "ru": "Синхронизировано объявлений: {count} ({new_note}).",
        "uk": "Синхронізовано оголошень: {count} ({new_note}).",
    },
    "sync_failures_suffix": {
        "en": " {count} publication(s) failed to parse.",
        "cs": " Nepodařilo se zpracovat inzerátů: {count}.",
        "ru": " Не удалось обработать объявлений: {count}.",
        "uk": " Не вдалося обробити оголошень: {count}.",
    },
    "parse_custom_updated": {
        "en": "Saved search updated:\n{url}\n\n{summary}",
        "cs": "Uložené vyhledávání aktualizováno:\n{url}\n\n{summary}",
        "ru": "Сохранённый поиск обновлён:\n{url}\n\n{summary}",
        "uk": "Збережений пошук оновлено:\n{url}\n\n{summary}",
    },
    "parse_help_prefix": {
        "en": (
            "Only --url, --price-from, --price-to, --delay, --timeout, and --max-retries "
            "apply here — they update *your own* saved search and run it right away.\n"
            "--output, --reset, --show, --run, and --config are CLI-only and are ignored.\n"
            "Example: /parse_custom --price-from 500 --price-to 1200\n\n"
        ),
        "cs": (
            "Zde platí pouze --url, --price-from, --price-to, --delay, --timeout a "
            "--max-retries — aktualizují *vaše vlastní* uložené vyhledávání a hned ho "
            "spustí.\n"
            "--output, --reset, --show, --run a --config jsou pouze pro CLI a jsou "
            "ignorovány.\n"
            "Příklad: /parse_custom --price-from 500 --price-to 1200\n\n"
        ),
        "ru": (
            "Здесь применяются только --url, --price-from, --price-to, --delay, --timeout "
            "и --max-retries — они обновляют *ваш собственный* сохранённый поиск и сразу "
            "его запускают.\n"
            "--output, --reset, --show, --run и --config предназначены только для CLI и "
            "игнорируются.\n"
            "Пример: /parse_custom --price-from 500 --price-to 1200\n\n"
        ),
        "uk": (
            "Тут застосовуються лише --url, --price-from, --price-to, --delay, --timeout "
            "і --max-retries — вони оновлюють *ваш власний* збережений пошук і одразу його "
            "запускають.\n"
            "--output, --reset, --show, --run і --config призначені лише для CLI та "
            "ігноруються.\n"
            "Приклад: /parse_custom --price-from 500 --price-to 1200\n\n"
        ),
    },
    "use_default_search_button": {
        "en": "▶️ Use the default search",
        "cs": "▶️ Použít výchozí vyhledávání",
        "ru": "▶️ Использовать поиск по умолчанию",
        "uk": "▶️ Використати пошук за замовчуванням",
    },
    "pets_yes_button": {
        "en": "🐾 Yes",
        "cs": "🐾 Ano",
        "ru": "🐾 Да",
        "uk": "🐾 Так",
    },
    "pets_no_button": {
        "en": "🚫 No",
        "cs": "🚫 Ne",
        "ru": "🚫 Нет",
        "uk": "🚫 Ні",
    },
    "skip_button": {
        "en": "⏭ Skip",
        "cs": "⏭ Přeskočit",
        "ru": "⏭ Пропустить",
        "uk": "⏭ Пропустити",
    },
    "pass_button": {
        "en": "👎 Pass",
        "cs": "👎 Přeskočit",
        "ru": "👎 Пропустить",
        "uk": "👎 Пропустити",
    },
    "like_button": {
        "en": "❤️ Like",
        "cs": "❤️ Líbí se",
        "ru": "❤️ Нравится",
        "uk": "❤️ Подобається",
    },
    "prev_button": {
        "en": "◂ Prev",
        "cs": "◂ Zpět",
        "ru": "◂ Назад",
        "uk": "◂ Назад",
    },
    "next_button": {
        "en": "Next ▸",
        "cs": "Další ▸",
        "ru": "Далее ▸",
        "uk": "Далі ▸",
    },
    "full_details_button": {
        "en": "Full details & photos",
        "cs": "Detaily a fotky",
        "ru": "Все детали и фото",
        "uk": "Усі деталі та фото",
    },
    "open_listing_button": {
        "en": "Open listing",
        "cs": "Otevřít inzerát",
        "ru": "Открыть объявление",
        "uk": "Відкрити оголошення",
    },
    "open_app_button": {
        "en": "Open App",
        "cs": "Otevřít aplikaci",
        "ru": "Открыть приложение",
        "uk": "Відкрити застосунок",
    },
    "top_match_badge": {
        "en": "Top match",
        "cs": "Nejlepší shoda",
        "ru": "Лучшее совпадение",
        "uk": "Найкращий збіг",
    },
    "untitled_listing": {
        "en": "Untitled listing",
        "cs": "Inzerát bez názvu",
        "ru": "Объявление без названия",
        "uk": "Оголошення без назви",
    },
    "rent_label": {
        "en": "Rent",
        "cs": "Nájem",
        "ru": "Аренда",
        "uk": "Оренда",
    },
    "deposit_label": {
        "en": "Deposit",
        "cs": "Kauce",
        "ru": "Депозит",
        "uk": "Депозит",
    },
    "furnished_label": {
        "en": "Furnished",
        "cs": "Vybavení",
        "ru": "Меблировка",
        "uk": "Меблювання",
    },
    "floor_label": {
        "en": "Floor",
        "cs": "Podlaží",
        "ru": "Этаж",
        "uk": "Поверх",
    },
    "pets_field_label": {
        "en": "Pets",
        "cs": "Zvířata",
        "ru": "Животные",
        "uk": "Тварини",
    },
    "open_on_bezrealitky": {
        "en": "Open on Bezrealitky",
        "cs": "Otevřít na Bezrealitky",
        "ru": "Открыть на Bezrealitky",
        "uk": "Відкрити на Bezrealitky",
    },
    "pets_label_yes": {
        "en": "Yes",
        "cs": "Ano",
        "ru": "Да",
        "uk": "Так",
    },
    "pets_label_no": {
        "en": "No",
        "cs": "Ne",
        "ru": "Нет",
        "uk": "Ні",
    },
    "pets_label_unknown": {
        "en": "Unknown",
        "cs": "Neznámé",
        "ru": "Неизвестно",
        "uk": "Невідомо",
    },
    "new_match_header": {
        "en": "🆕 <b>New match in your saved search</b>\n\n",
        "cs": "🆕 <b>Nová shoda ve vašem uloženém vyhledávání</b>\n\n",
        "ru": "🆕 <b>Новое совпадение по вашему сохранённому поиску</b>\n\n",
        "uk": "🆕 <b>Новий збіг за вашим збереженим пошуком</b>\n\n",
    },
}


def t(key: str, language: str, **kwargs) -> str:
    variants = _TEXTS[key]
    template = variants.get(language, variants[_DEFAULT_LANGUAGE])
    return template.format(**kwargs) if kwargs else template


_CHART_KEYS = [
    "area_hist",
    "price_hist",
    "price_per_unit_hist",
    "price_vs_area",
    "format_pie",
    "pets_pie",
]

_CHART_LABELS: dict[str, dict[str, str]] = {
    "area_hist": {
        "en": "Area distribution",
        "cs": "Rozložení plochy",
        "ru": "Распределение по площади",
        "uk": "Розподіл за площею",
    },
    "price_hist": {
        "en": "Price distribution",
        "cs": "Rozložení ceny",
        "ru": "Распределение по цене",
        "uk": "Розподіл за ціною",
    },
    "price_per_unit_hist": {
        "en": "Price per m² distribution",
        "cs": "Rozložení ceny za m²",
        "ru": "Распределение цены за м²",
        "uk": "Розподіл ціни за м²",
    },
    "price_vs_area": {
        "en": "Price vs. area",
        "cs": "Cena vs. plocha",
        "ru": "Цена и площадь",
        "uk": "Ціна і площа",
    },
    "format_pie": {
        "en": "By layout",
        "cs": "Podle dispozice",
        "ru": "По планировке",
        "uk": "За плануванням",
    },
    "pets_pie": {
        "en": "By pets_friendly",
        "cs": "Podle vhodnosti pro zvířata",
        "ru": "По разрешению животных",
        "uk": "За дозволом тварин",
    },
}


def chart_options(language: str) -> list[tuple[str, str]]:
    return [(key, chart_label(key, language)) for key in _CHART_KEYS]


def chart_label(key: str, language: str) -> str:
    labels = _CHART_LABELS.get(key)
    if not labels:
        return key
    return labels.get(language, labels[_DEFAULT_LANGUAGE])


# Descriptions for Telegram's "/" command menu. The menu itself is registered
# per-chat with the user's chosen language right after they pick it (see
# handlers/start.py), plus once globally in English as the pre-choice default.
_BOT_COMMAND_ORDER = [
    "start",
    "help",
    "language",
    "onboarding",
    "list",
    "view",
    "liked",
    "parse",
    "parse_custom",
    "parse_help",
    "search",
    "charts",
]

_BOT_COMMAND_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "start": {
        "en": "Welcome message and language setup",
        "cs": "Uvítací zpráva a nastavení jazyka",
        "ru": "Приветствие и выбор языка",
        "uk": "Привітання та вибір мови",
    },
    "help": {
        "en": "Show available commands",
        "cs": "Zobrazit dostupné příkazy",
        "ru": "Показать доступные команды",
        "uk": "Показати доступні команди",
    },
    "language": {
        "en": "Choose the translation language",
        "cs": "Vybrat jazyk překladu",
        "ru": "Выбрать язык перевода",
        "uk": "Вибрати мову перекладу",
    },
    "onboarding": {
        "en": "Redo the onboarding wizard from scratch",
        "cs": "Projít onboarding znovu od začátku",
        "ru": "Пройти онбординг заново",
        "uk": "Пройти онбординг знову",
    },
    "list": {
        "en": "Browse listings matching your saved search",
        "cs": "Procházet inzeráty podle uloženého vyhledávání",
        "ru": "Просмотр объявлений по сохранённому поиску",
        "uk": "Перегляд оголошень за збереженим пошуком",
    },
    "view": {
        "en": "Full details for one listing (needs an ID)",
        "cs": "Podrobnosti k jednomu inzerátu (vyžaduje ID)",
        "ru": "Подробности об одном объявлении (нужен ID)",
        "uk": "Подробиці про одне оголошення (потрібен ID)",
    },
    "liked": {
        "en": "Browse the listings you've liked",
        "cs": "Procházet inzeráty, které se vám líbí",
        "ru": "Просмотр понравившихся объявлений",
        "uk": "Перегляд вподобаних оголошень",
    },
    "parse": {
        "en": "Run the scraper now with your saved search",
        "cs": "Spustit stahování dat s uloženým vyhledáváním",
        "ru": "Запустить сбор данных по сохранённому поиску",
        "uk": "Запустити збір даних за збереженим пошуком",
    },
    "parse_custom": {
        "en": "Update your saved search and run it",
        "cs": "Upravit uložené vyhledávání a spustit ho",
        "ru": "Обновить сохранённый поиск и запустить его",
        "uk": "Оновити збережений пошук і запустити його",
    },
    "parse_help": {
        "en": "Show the flags /parse_custom accepts",
        "cs": "Zobrazit přepínače přijímané /parse_custom",
        "ru": "Показать флаги, принимаемые /parse_custom",
        "uk": "Показати прапорці, які приймає /parse_custom",
    },
    "search": {
        "en": "Show your current saved search",
        "cs": "Zobrazit aktuální uložené vyhledávání",
        "ru": "Показать текущий сохранённый поиск",
        "uk": "Показати поточний збережений пошук",
    },
    "charts": {
        "en": "Distribution charts for your saved search",
        "cs": "Grafy rozložení pro uložené vyhledávání",
        "ru": "Графики распределения для сохранённого поиска",
        "uk": "Графіки розподілу для збереженого пошуку",
    },
}


def bot_command_descriptions(language: str) -> list[tuple[str, str]]:
    """``(command, description)`` pairs, in menu order — plain data rather than
    an ``aiogram.types.BotCommand`` list, since this module (unlike the rest of
    the ``bot`` package) is also imported by the webapp backend, which doesn't
    install aiogram. The bot builds the actual ``BotCommand`` objects itself.
    """
    return [
        (
            command,
            _BOT_COMMAND_DESCRIPTIONS[command].get(language, _BOT_COMMAND_DESCRIPTIONS[command][_DEFAULT_LANGUAGE]),
        )
        for command in _BOT_COMMAND_ORDER
    ]

_BATCH_SUMMARY = {
    "en": "👋 <b>Hi!</b> Your saved search is ready.\n\nFound <b>{count}</b> listings for you.",
    "cs": "👋 <b>Ahoj!</b> Váš uložený požadavek je připraven.\n\nNalezeno inzerátů: <b>{count}</b>.",
    "ru": "👋 <b>Привет!</b> Ваш сохранённый поиск готов.\n\nНайдено объявлений: <b>{count}</b>.",
    "uk": "👋 <b>Привіт!</b> Ваш збережений пошук готовий.\n\nЗнайдено оголошень: <b>{count}</b>.",
}

_BROWSE_BUTTON = {
    "en": "📋 Browse listings",
    "cs": "📋 Procházet inzeráty",
    "ru": "📋 Смотреть объявления",
    "uk": "📋 Переглянути оголошення",
}

_CHARTS_BUTTON = {
    "en": "📊 Charts",
    "cs": "📊 Grafy",
    "ru": "📊 Графики",
    "uk": "📊 Графіки",
}

_TRANSLATION_FAILED_NOTE = {
    "en": "⚠️ Translation temporarily unavailable — showing the original text:",
    "cs": "⚠️ Překlad je dočasně nedostupný — zobrazen původní text:",
    "ru": "⚠️ Перевод временно недоступен — показан оригинальный текст:",
    "uk": "⚠️ Переклад тимчасово недоступний — показано оригінальний текст:",
}


def translation_failed_note(language: str) -> str:
    return _TRANSLATION_FAILED_NOTE.get(language, _TRANSLATION_FAILED_NOTE[_DEFAULT_LANGUAGE])

# Emoji is the actual color-coding here — Telegram's HTML/MarkdownV2 parse modes
# have no colored-text feature, so a distinct emoji per amenity is the only
# per-tag visual distinction the message text can actually carry.
_AMENITY_EMOJI = {
    "air_conditioning": "❄️",
    "has_washing_machine": "🧺",
    "has_dryer": "🌀",
    "has_internet": "📶",
    "has_dishwasher": "🍽",
    "mansard": "🔺",
    "balcony": "🌇",
    "oven": "🔥",
    "microwave": "♨️",
    "refrigerator": "🧊",
    "quiet_surroundings": "🤫",
    "garage": "🚗",
    "english_speaking": "🗣",
}

_AMENITY_LABELS = {
    "air_conditioning": {
        "en": "AC",
        "cs": "Klimatizace",
        "ru": "Кондиционер",
        "uk": "Кондиціонер",
    },
    "has_washing_machine": {
        "en": "Washer",
        "cs": "Pračka",
        "ru": "Стиральная машина",
        "uk": "Пральна машина",
    },
    "has_dryer": {
        "en": "Dryer",
        "cs": "Sušička",
        "ru": "Сушильная машина",
        "uk": "Сушильна машина",
    },
    "has_internet": {
        "en": "Internet",
        "cs": "Internet",
        "ru": "Интернет",
        "uk": "Інтернет",
    },
    "has_dishwasher": {
        "en": "Dishwasher",
        "cs": "Myčka",
        "ru": "Посудомоечная машина",
        "uk": "Посудомийна машина",
    },
    "mansard": {
        "en": "Attic/mansard",
        "cs": "Podkroví",
        "ru": "Мансарда",
        "uk": "Мансарда",
    },
    "balcony": {
        "en": "Balcony",
        "cs": "Balkón",
        "ru": "Балкон",
        "uk": "Балкон",
    },
    "oven": {
        "en": "Oven",
        "cs": "Trouba",
        "ru": "Духовка",
        "uk": "Духовка",
    },
    "microwave": {
        "en": "Microwave",
        "cs": "Mikrovlnka",
        "ru": "Микроволновка",
        "uk": "Мікрохвильовка",
    },
    "refrigerator": {
        "en": "Fridge",
        "cs": "Lednice",
        "ru": "Холодильник",
        "uk": "Холодильник",
    },
    "quiet_surroundings": {
        "en": "Quiet area",
        "cs": "Klidné okolí",
        "ru": "Тихое окружение",
        "uk": "Тиха місцевість",
    },
    "garage": {
        "en": "Garage",
        "cs": "Garáž",
        "ru": "Гараж",
        "uk": "Гараж",
    },
    "english_speaking": {
        "en": "English OK",
        "cs": "Anglicky",
        "ru": "Английский",
        "uk": "Англійська",
    },
}


def amenity_tags(language: str, row: dict) -> list[str]:
    """Emoji+label tags for every amenity confirmed present (``True``) on ``row``.

    Amenities that are absent or unknown are left out entirely, the same way a
    listing's own feature list only ever mentions what's there.
    """
    tags = []
    for field, emoji in _AMENITY_EMOJI.items():
        if row.get(field) is True:
            labels = _AMENITY_LABELS[field]
            tags.append(f"{emoji} {labels.get(language, labels[_DEFAULT_LANGUAGE])}")
    return tags


def batch_summary_text(language: str, count: int) -> str:
    template = _BATCH_SUMMARY.get(language, _BATCH_SUMMARY[_DEFAULT_LANGUAGE])
    return template.format(count=count)


def browse_button_label(language: str) -> str:
    return _BROWSE_BUTTON.get(language, _BROWSE_BUTTON[_DEFAULT_LANGUAGE])


def charts_button_label(language: str) -> str:
    return _CHARTS_BUTTON.get(language, _CHARTS_BUTTON[_DEFAULT_LANGUAGE])
