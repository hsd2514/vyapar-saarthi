/**
 * Minimal i18n for the app's core chrome and page headers - navigation,
 * buttons, step titles/descriptions. Covers what a low-literacy user reads
 * before they ever get to a paragraph of body text: the stepper, the
 * back/next buttons, and every page's header block. Body copy inside each
 * page stays English for now - this is a deliberate scope cut, not an
 * oversight, so what's here is fully translated rather than half of
 * everything being partially translated.
 *
 * Usage: const { t } = useUiLanguage(); t("steps.1.label")
 * Interpolation: t("feasibility.title", { type: "Dairy", block: "Ausa" })
 * replaces {type} and {block} in the matched string.
 */

export const UI_LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिंदी" },
  { code: "mr", label: "मराठी" },
];

const DICT = {
  en: {
    nav: {
      tagline: "Plan your business",
      footerFormula: "Every rupee shown here is worked out by a fixed formula, so a bank can check it.",
      mobileFooterNote: "Voice collects your details. Every financial figure is still a deterministic calculation, never a guess.",
      mobileStepOf: "Step {current} of {total}",
    },
    steps: {
      1: { label: "Tell us about you" },
      2: { label: "Will it work here?" },
      3: { label: "How much you can get" },
      4: { label: "What you'll pay back" },
      5: { label: "Your plan" },
    },
    common: { back: "Back", next: "Next" },
    intake: {
      eyebrow: "Step 1 of 5",
      title: "Tell us about the business you want to start",
      description: "Talk to Saarthi like you would to a person. It will ask one thing at a time and fill in the answers here. You can also type or change anything yourself.",
    },
    feasibility: {
      eyebrow: "Step 2 of 5",
      title: "Will a {type} business work in {block}?",
      description: "We looked at how many people live near you, how many shops like yours are already there, and what prices are like in your area.",
    },
    financial: {
      eyebrow: "Step 3 of 5",
      title: "How much money you can get",
      description: "For every ₹10 the business needs, you put in ₹1 and the government scheme lends the other ₹9. How big your business is decides which scheme you get.",
    },
    repayment: {
      eyebrow: "Step 4 of 5",
      title: "What you will pay back, and when",
      description: "You do not pay anything for the first few months. After that, the same amount every month until the loan is finished.",
    },
    summary: {
      eyebrow: "Step 5 of 5",
      title: "Your full plan",
      description: "Everything on one page. Print this and take it with you to the bank, the CSC centre, or your SHG group.",
    },
  },
  hi: {
    nav: {
      tagline: "अपना व्यवसाय योजना बनाएं",
      footerFormula: "यहाँ दिखाया गया हर रुपया एक तय फॉर्मूले से निकाला गया है, ताकि बैंक इसे जांच सके।",
      mobileFooterNote: "आवाज़ से आपकी जानकारी ली जाती है। हर पैसों का आंकड़ा हमेशा तय गणना से निकलता है, कभी अंदाज़ा नहीं।",
      mobileStepOf: "चरण {current} / {total}",
    },
    steps: {
      1: { label: "अपने बारे में बताएं" },
      2: { label: "क्या यह यहाँ चलेगा?" },
      3: { label: "आपको कितना मिल सकता है" },
      4: { label: "आपको कितना चुकाना होगा" },
      5: { label: "आपकी योजना" },
    },
    common: { back: "पीछे", next: "आगे" },
    intake: {
      eyebrow: "चरण 1 / 5",
      title: "आप जो व्यवसाय शुरू करना चाहते हैं, उसके बारे में बताएं",
      description: "सारथी से वैसे ही बात करें जैसे किसी व्यक्ति से करते हैं। यह एक-एक करके सवाल पूछेगा और यहाँ जवाब भर देगा। आप खुद भी टाइप कर सकते हैं या कुछ भी बदल सकते हैं।",
    },
    feasibility: {
      eyebrow: "चरण 2 / 5",
      title: "क्या {block} में {type} व्यवसाय चलेगा?",
      description: "हमने देखा कि आपके आसपास कितने लोग रहते हैं, आपके जैसी कितनी दुकानें पहले से हैं, और आपके इलाके में दाम कैसे हैं।",
    },
    financial: {
      eyebrow: "चरण 3 / 5",
      title: "आपको कितना पैसा मिल सकता है",
      description: "व्यवसाय को जितने भी ₹10 चाहिए, उसमें से ₹1 आप लगाते हैं और बाकी ₹9 सरकारी योजना कर्ज के रूप में देती है। आपका व्यवसाय कितना बड़ा है, इससे तय होता है कि आपको कौन सी योजना मिलेगी।",
    },
    repayment: {
      eyebrow: "चरण 4 / 5",
      title: "आपको कितना और कब चुकाना होगा",
      description: "शुरू के कुछ महीनों में आपको कुछ नहीं देना है। उसके बाद, कर्ज खत्म होने तक हर महीने एक जैसी रकम देनी होगी।",
    },
    summary: {
      eyebrow: "चरण 5 / 5",
      title: "आपकी पूरी योजना",
      description: "सब कुछ एक ही पन्ने पर। इसे प्रिंट करें और बैंक, सीएससी केंद्र या अपने एसएचजी समूह के पास ले जाएं।",
    },
  },
  mr: {
    nav: {
      tagline: "तुमच्या व्यवसायाची योजना करा",
      footerFormula: "इथे दाखवलेला प्रत्येक रुपया एका ठराविक सूत्राने काढला आहे, जेणेकरून बँक ते तपासू शकेल.",
      mobileFooterNote: "आवाजाद्वारे तुमची माहिती घेतली जाते. प्रत्येक आर्थिक आकडा नेहमी ठराविक गणनेने काढला जातो, अंदाजाने नाही.",
      mobileStepOf: "टप्पा {current} / {total}",
    },
    steps: {
      1: { label: "आपल्याबद्दल सांगा" },
      2: { label: "हे इथे चालेल का?" },
      3: { label: "तुम्हाला किती मिळू शकते" },
      4: { label: "तुम्हाला किती परत करावे लागेल" },
      5: { label: "तुमची योजना" },
    },
    common: { back: "मागे", next: "पुढे" },
    intake: {
      eyebrow: "टप्पा 1 / 5",
      title: "तुम्ही सुरू करू इच्छित असलेल्या व्यवसायाबद्दल सांगा",
      description: "सारथीशी एखाद्या व्यक्तीशी बोलावे तसे बोला. ते एका वेळी एक प्रश्न विचारेल आणि इथे उत्तरे भरेल. तुम्ही स्वतः टाइप करू शकता किंवा काहीही बदलू शकता.",
    },
    feasibility: {
      eyebrow: "टप्पा 2 / 5",
      title: "{block} मध्ये {type} व्यवसाय चालेल का?",
      description: "आम्ही पाहिले की तुमच्या जवळ किती लोक राहतात, तुमच्यासारखी किती दुकाने आधीच आहेत, आणि तुमच्या भागात किंमती कशा आहेत.",
    },
    financial: {
      eyebrow: "टप्पा 3 / 5",
      title: "तुम्हाला किती पैसे मिळू शकतात",
      description: "व्यवसायाला लागणाऱ्या प्रत्येक ₹10 पैकी ₹1 तुम्ही घालता आणि उरलेले ₹9 सरकारी योजना कर्ज म्हणून देते. तुमचा व्यवसाय किती मोठा आहे यावर कोणती योजना मिळेल हे ठरते.",
    },
    repayment: {
      eyebrow: "टप्पा 4 / 5",
      title: "तुम्हाला किती आणि केव्हा परत करावे लागेल",
      description: "सुरुवातीच्या काही महिन्यांत तुम्हाला काहीही द्यायचे नाही. त्यानंतर, कर्ज संपेपर्यंत दर महिन्याला तेवढीच रक्कम द्यावी लागेल.",
    },
    summary: {
      eyebrow: "टप्पा 5 / 5",
      title: "तुमची संपूर्ण योजना",
      description: "सर्व काही एका पानावर. हे प्रिंट करा आणि बँक, सीएससी केंद्र किंवा तुमच्या एसएचजी गटाकडे घेऊन जा.",
    },
  },
};

function getPath(obj, path) {
  return path.split(".").reduce((acc, key) => (acc == null ? acc : acc[key]), obj);
}

export function translate(lang, key, vars) {
  const value = getPath(DICT[lang], key) ?? getPath(DICT.en, key) ?? key;
  if (typeof value !== "string" || !vars) return value;
  return Object.entries(vars).reduce((str, [k, v]) => str.replaceAll(`{${k}}`, v ?? ""), value);
}
