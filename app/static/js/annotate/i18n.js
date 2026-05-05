// i18n for the Nature-Scribe annotate pages.
// window._ is already defined as a no-op shim in the HTML template; this
// module overrides it with a real lookup once the document body is available
// (ES modules are deferred, so document.body exists at execution time).

const ZH = {
  // Field labels
  "Collector": "採集者",
  "Or type name": "或輸入名稱",
  "Collector name": "採集者姓名",
  "Collect date": "採集日期",
  "As written": "原文",
  "Verbatim collector": "原始採集者",
  "Companion names": "同行人員",
  "Companion text": "同行人員（原文）",
  "Verbatim collect date": "原始採集日期",
  "e.g., 412": "例：412",
  "Field number": "野外編號",
  "Person": "人員",
  "Date": "日期",
  "Scientific name": "學名",
  "Verbatim identification": "原始鑑定名",
  "Locality text": "採集地點",
  "Verbatim locality": "原始地點描述",
  "Interpreted place name": "地名（解譯）",
  "Coordinates": "座標",
  "Administrative area": "行政區",
  "Altitude": "海拔",
  "Longitude": "經度",
  "Latitude": "緯度",
  "Country": "國家",
  "Admin area 1": "一級行政區",
  "Admin area 2": "二級行政區",
  "Admin area 3": "三級行政區",

  // Section titles
  "Collection Event": "採集事件",
  "Identification": "鑑定",
  "Geospatial": "地理空間",
  "Notes": "備註",
  "Handwritten label": "手寫標籤",
  "Traits": "特徵",
  "Flags & corrections": "標記與更正",

  // Identification entry
  "Identifier": "鑑定者",
  "Identification date": "鑑定日期",
  "Add new identification": "新增鑑定",
  "select person": "請選擇人員",
  "select taxon": "請選擇分類群",
  // Note: ordinal labels (初次鑑定, 二次鑑定…) live in IDENT_ORDINALS in
  // annotation.js; they pass through _() but resolve to themselves in zh.

  // Section hints
  "Who collected the specimen, when, and any field notes.": "誰採集了這份標本、何時採集，以及野外記錄。",
  "Help confirm or refine the taxonomic identification.": "協助確認或修正分類鑑定。",
  "Where the specimen was collected. Decimal and DMS auto-convert.": "標本的採集地點，十進位與度分秒格式可自動轉換。",

  // Dropdowns
  "— select —": "— 請選擇 —",
  "— select country —": "— 選擇國家 —",
  "— select country first —": "— 請先選擇國家 —",
  "— select adm1 first —": "— 請先選擇一級行政區 —",
  "— select adm2 first —": "— 請先選擇二級行政區 —",

  // Field actions
  "— not yet annotated —": "— 尚未轉錄 —",
  "Suggest edit": "建議修改",
  "Annotate": "標記",
  "Flag": "標記問題",

  // Notes
  "Free-text observations: condition, prior misclassifications, references…": "自由記錄：標本狀況、過往誤鑑定、參考文獻…",
  "Markdown supported. Visible to all contributors.": "支援 Markdown 格式，所有貢獻者皆可查看。",
  "Post note": "發佈備註",

  // Submission
  "Submit annotations": "提交轉錄",
  "Annotations saved successfully.": "轉錄資料已成功儲存。",
  "Error saving annotations.": "儲存轉錄資料時發生錯誤。",

  // Status badges
  "Verified": "已驗證",
  "In review": "審核中",
  "Needs help": "需要協助",

  // Image viewer
  "Image resolution": "影像解析度",
  "Fit": "符合視窗",
  "⤓ Download": "⤓ 下載",

  // Image rail
  "Specimen plate": "標本影像",
  "Recent annotators": "近期貢獻者",

  // Navigation
  "← Back to explorer": "← 返回瀏覽",
  "Catalog Number": "館號",

  // Panel tabs
  "History": "歷史",
  "Discuss": "討論",

  // Handwritten section
  "Transcribed": "已轉錄",
  "Save transcription": "儲存轉錄",
  "2 of 3 transcribers agree": "3 人中有 2 人同意",

  // Traits
  "+ add trait": "+ 新增特徵",

  // Flags
  "Possible misidentification": "可能誤鑑定",
  "Resolve": "解決",
  "⚑ Raise a new flag": "⚑ 提出新問題",

  // AI label reader panel
  "AI label reader": "AI 標籤辨識",
  "AI draft — verify before using": "AI 草稿 — 使用前請確認",
  "Read label": "讀取標籤",
  "Re-read": "重新讀取",
  "Reading…": "讀取中…",
  "Backend": "後端",
  "Anthropic API": "Anthropic API",
  "Remote (Claude session)": "遠端 (Claude session)",
  "Remote backend unavailable": "遠端後端無法連線",
  "Re-reading on the API backend will incur a billable call. Continue?": "在 API 後端重新讀取會產生費用，是否繼續？",
  "cached": "已快取",
  "no cost": "無費用",
  "ms": "毫秒",
  "Recent attempts": "近期嘗試",
  "Failed to read label": "讀取標籤失敗",

  // Top nav (also handled by Flask-Babel in the template, included here
  // so JS-rendered UI that duplicates these strings stays consistent)
  "Explore": "探索",
  "Collections": "館藏",
  "Contributors": "貢獻者",
  "About": "關於",
  "Bookmarks": "書籤",
  "Notifications": "通知",
};

const TRANSLATIONS = { zh: ZH };

const lang = document.body?.dataset?.lang || "en";
const dict = TRANSLATIONS[lang] || null;

window.gettext = (text) => (dict && dict[text]) || text;
window._ = window.gettext;
